"""Character-based chunker implementation."""
from typing import List, Dict, Any
from .base_chunker import BaseChunker


class CharacterChunker(BaseChunker):
    """Chunker that splits text by character count with overlap."""
    
    def validate_params(self) -> None:
        """
        Validate character chunking parameters.
        
        Raises:
            ValueError: If parameters are invalid
        """
        chunk_size = self.params.get('chunk_size', 500)
        overlap = self.params.get('overlap', 50)
        
        if not isinstance(chunk_size, int) or chunk_size <= 0:
            raise ValueError("chunk_size must be a positive integer")
        
        if not isinstance(overlap, int) or overlap < 0:
            raise ValueError("overlap must be a non-negative integer")
        
        if overlap >= chunk_size:
            raise ValueError("overlap must be less than chunk_size")
    
    def chunk(self, text: str, metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Chunk text by character count.
        
        Args:
            text: Input text to chunk
            metadata: Optional metadata about the source document
        
        Returns:
            List of chunk dictionaries
        """
        chunk_size = self.params.get('chunk_size', 500)
        overlap = self.params.get('overlap', 50)
        
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
                    overlap=overlap
                )
                chunks.append(chunk)
                chunk_index += 1
            
            # Move to next position with overlap
            if end >= text_length:
                break
            
            start = start + chunk_size - overlap
        
        return chunks
