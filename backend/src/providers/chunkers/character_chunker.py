"""Character-based chunker implementation with sliding window support."""
from typing import List, Dict, Any
from .base_chunker import BaseChunker


class CharacterChunker(BaseChunker):
    """Chunker that splits text by character count with overlap/sliding window support.
    
    Supports two modes:
    1. Standard mode: chunk_size and overlap parameters
    2. Sliding window mode: window_size and step_size parameters (FR-005)
    """
    
    def validate_params(self) -> None:
        """
        Validate character chunking parameters.
        
        Raises:
            ValueError: If parameters are invalid
        """
        # Support both chunk_size/overlap and window_size/step_size
        chunk_size = self.params.get('chunk_size') or self.params.get('window_size', 500)
        overlap = self.params.get('overlap', 50)
        step_size = self.params.get('step_size')
        
        if step_size is not None:
            # Sliding window mode
            if not isinstance(chunk_size, int) or chunk_size <= 0:
                raise ValueError("window_size must be a positive integer")
            if not isinstance(step_size, int) or step_size <= 0:
                raise ValueError("step_size must be a positive integer")
            if step_size > chunk_size:
                raise ValueError("step_size must be less than or equal to window_size")
        else:
            # Standard mode
            if not isinstance(chunk_size, int) or chunk_size <= 0:
                raise ValueError("chunk_size must be a positive integer")
            if not isinstance(overlap, int) or overlap < 0:
                raise ValueError("overlap must be a non-negative integer")
            if overlap >= chunk_size:
                raise ValueError("overlap must be less than chunk_size")
    
    def chunk(self, text: str, metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Chunk text by character count with sliding window support.
        
        Args:
            text: Input text to chunk
            metadata: Optional metadata about the source document
        
        Returns:
            List of chunk dictionaries
        """
        # Support both parameter naming conventions
        chunk_size = self.params.get('chunk_size') or self.params.get('window_size', 500)
        step_size = self.params.get('step_size')
        overlap = self.params.get('overlap', 50)
        
        # Calculate step (sliding window mode vs standard mode)
        if step_size is not None:
            step = step_size
        else:
            step = chunk_size - overlap
        
        if not text or len(text) == 0:
            return []
        
        chunks = []
        start = 0
        chunk_index = 0
        text_length = len(text)
        
        while start < text_length:
            # Calculate end position
            end = min(start + chunk_size, text_length)
            
            # Extract chunk content
            content = text[start:end].strip()
            
            # Skip empty chunks
            if content:
                chunk = self._create_chunk(
                    content=content,
                    index=chunk_index,
                    start_pos=start,
                    end_pos=end,
                    strategy="character",
                    chunk_size=chunk_size,
                    overlap=overlap if step_size is None else chunk_size - step_size,
                    window_size=chunk_size if step_size is not None else None,
                    step_size=step_size
                )
                chunks.append(chunk)
                chunk_index += 1
            
            # Move to next position
            if end >= text_length:
                break
            
            start = start + step
        
        return chunks
