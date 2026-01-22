"""Parent-Child chunker implementation for hierarchical document chunking.

This chunker generates two-level chunks:
- Parent chunks: Large chunks containing complete context
- Child chunks: Smaller chunks for retrieval, linked to parent via parent_id

Use case: Small chunks for precise retrieval + large chunks for context during generation.
"""
from typing import List, Dict, Any, Tuple, Optional
from .base_chunker import BaseChunker
import uuid


class ParentChildChunker(BaseChunker):
    """Chunker that creates parent-child hierarchical chunks.
    
    Parameters:
        parent_chunk_size (int): Size of parent chunks (default: 2000)
        child_chunk_size (int): Size of child chunks (default: 500)
        child_overlap (int): Overlap between child chunks (default: 50)
        parent_overlap (int): Overlap between parent chunks (default: 200)
    
    The relationship:
    - Each parent chunk contains multiple child chunks
    - Child chunks are used for retrieval (embeddings)
    - Parent chunks provide context during generation
    """
    
    def validate_params(self) -> None:
        """
        Validate parent-child chunking parameters.
        
        Raises:
            ValueError: If parameters are invalid
        """
        parent_size = self.params.get('parent_chunk_size', 2000)
        child_size = self.params.get('child_chunk_size', 500)
        child_overlap = self.params.get('child_overlap', 50)
        parent_overlap = self.params.get('parent_overlap', 200)
        
        if not isinstance(parent_size, int) or parent_size <= 0:
            raise ValueError("parent_chunk_size must be a positive integer")
        
        if not isinstance(child_size, int) or child_size <= 0:
            raise ValueError("child_chunk_size must be a positive integer")
        
        if not isinstance(child_overlap, int) or child_overlap < 0:
            raise ValueError("child_overlap must be a non-negative integer")
        
        if not isinstance(parent_overlap, int) or parent_overlap < 0:
            raise ValueError("parent_overlap must be a non-negative integer")
        
        if child_size >= parent_size:
            raise ValueError("child_chunk_size must be less than parent_chunk_size")
        
        if child_overlap >= child_size:
            raise ValueError("child_overlap must be less than child_chunk_size")
        
        if parent_overlap >= parent_size:
            raise ValueError("parent_overlap must be less than parent_chunk_size")
    
    def chunk(self, text: str, metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Chunk text into parent-child hierarchical structure.
        
        Args:
            text: Input text to chunk
            metadata: Optional metadata about the source document
        
        Returns:
            List of chunk dictionaries containing both parent and child chunks.
            Child chunks have 'parent_id' linking to their parent chunk.
        """
        if not text or len(text) == 0:
            return []
        
        parent_size = self.params.get('parent_chunk_size', 2000)
        child_size = self.params.get('child_chunk_size', 500)
        child_overlap = self.params.get('child_overlap', 50)
        parent_overlap = self.params.get('parent_overlap', 200)
        
        # Step 1: Create parent chunks
        parent_chunks = self._create_parent_chunks(text, parent_size, parent_overlap)
        
        # Step 2: Create child chunks within each parent
        all_chunks = []
        child_index = 0
        
        for parent_idx, parent in enumerate(parent_chunks):
            parent_id = parent['metadata']['chunk_id']
            parent_content = parent['content']
            parent_start = parent['metadata']['start_position']
            
            # Create child chunks from parent content
            children = self._create_child_chunks(
                parent_content,
                parent_id,
                parent_start,
                child_size,
                child_overlap,
                child_index,
                parent_idx
            )
            
            # Update parent with child count
            parent['metadata']['child_count'] = len(children)
            parent['metadata']['child_ids'] = [c['metadata']['chunk_id'] for c in children]
            
            # Add children to result
            all_chunks.extend(children)
            child_index += len(children)
        
        # Store parent chunks in special metadata key for later extraction
        # The service layer will separate parent and child chunks
        return {
            'parent_chunks': parent_chunks,
            'child_chunks': all_chunks
        }
    
    def chunk_with_parents(self, text: str, metadata: Dict[str, Any] = None) -> Tuple[List[Dict], List[Dict]]:
        """
        Chunk text and return separate parent and child chunk lists.
        
        This method provides explicit separation of parent and child chunks
        for cleaner processing by the service layer.
        
        Args:
            text: Input text to chunk
            metadata: Optional metadata about the source document
        
        Returns:
            Tuple of (parent_chunks, child_chunks)
        """
        result = self.chunk(text, metadata)
        if isinstance(result, dict):
            return result['parent_chunks'], result['child_chunks']
        return [], result
    
    def _create_parent_chunks(
        self, 
        text: str, 
        chunk_size: int, 
        overlap: int
    ) -> List[Dict[str, Any]]:
        """Create parent-level chunks from text."""
        chunks = []
        start = 0
        chunk_index = 0
        text_length = len(text)
        step = chunk_size - overlap
        
        while start < text_length:
            end = min(start + chunk_size, text_length)
            content = text[start:end]
            
            # Try to break at sentence boundary for cleaner chunks
            if end < text_length:
                # Look for sentence endings within the last 20% of chunk
                search_start = int(len(content) * 0.8)
                last_period = content.rfind('。', search_start)
                last_dot = content.rfind('. ', search_start)
                last_newline = content.rfind('\n\n', search_start)
                
                # Find the latest sentence boundary
                boundary = max(last_period, last_dot, last_newline)
                if boundary > search_start:
                    end = start + boundary + 1
                    content = text[start:end]
            
            content = content.strip()
            if content:
                chunk = {
                    'content': content,
                    'chunk_type': 'parent',
                    'parent_id': None,
                    'metadata': {
                        'chunk_id': str(uuid.uuid4()),
                        'chunk_index': chunk_index,
                        'chunk_type': 'parent',
                        'char_count': len(content),
                        'word_count': len(content.split()),
                        'start_position': start,
                        'end_position': end,
                        'parent_sequence': chunk_index,
                        'is_parent': True,
                        'child_count': 0,
                        'child_ids': []
                    }
                }
                chunks.append(chunk)
                chunk_index += 1
            
            if end >= text_length:
                break
            
            start = start + step
        
        return chunks
    
    def _create_child_chunks(
        self,
        parent_content: str,
        parent_id: str,
        parent_start: int,
        chunk_size: int,
        overlap: int,
        global_index: int,
        parent_sequence: int
    ) -> List[Dict[str, Any]]:
        """Create child chunks from parent content."""
        chunks = []
        start = 0
        local_index = 0
        content_length = len(parent_content)
        step = chunk_size - overlap
        
        while start < content_length:
            end = min(start + chunk_size, content_length)
            content = parent_content[start:end]
            
            # Try to break at word boundary
            if end < content_length and len(content) > 0:
                # Look for space or punctuation near the end
                last_space = content.rfind(' ', int(len(content) * 0.8))
                last_newline = content.rfind('\n', int(len(content) * 0.8))
                boundary = max(last_space, last_newline)
                
                if boundary > int(len(content) * 0.8):
                    end = start + boundary + 1
                    content = parent_content[start:end]
            
            content = content.strip()
            if content:
                # Calculate absolute positions
                abs_start = parent_start + start
                abs_end = parent_start + end
                
                chunk = self._create_chunk(
                    content=content,
                    index=global_index + local_index,
                    start_pos=abs_start,
                    end_pos=abs_end,
                    chunk_type='text',
                    parent_id=parent_id,
                    local_index=local_index,
                    parent_sequence=parent_sequence,
                    relative_start=start,
                    relative_end=end
                )
                chunks.append(chunk)
                local_index += 1
            
            if end >= content_length:
                break
            
            start = start + step
        
        return chunks
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """Get information about the chunking strategy."""
        return {
            'type': 'parent_child',
            'name': 'Parent-Child Chunking',
            'description': 'Hierarchical chunking with large parent chunks for context and small child chunks for retrieval',
            'parameters': {
                'parent_chunk_size': {
                    'type': 'int',
                    'default': 2000,
                    'min': 500,
                    'max': 10000,
                    'description': 'Size of parent chunks in characters'
                },
                'child_chunk_size': {
                    'type': 'int', 
                    'default': 500,
                    'min': 100,
                    'max': 2000,
                    'description': 'Size of child chunks in characters'
                },
                'child_overlap': {
                    'type': 'int',
                    'default': 50,
                    'min': 0,
                    'max': 500,
                    'description': 'Overlap between child chunks'
                },
                'parent_overlap': {
                    'type': 'int',
                    'default': 200,
                    'min': 0,
                    'max': 1000,
                    'description': 'Overlap between parent chunks'
                }
            }
        }
