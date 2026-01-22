"""Base chunker abstract class."""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Generator, Optional


class BaseChunker(ABC):
    """Abstract base class for all chunking strategies."""
    
    def __init__(self, **params):
        """
        Initialize chunker with parameters.
        
        Args:
            **params: Strategy-specific parameters
        """
        self.params = params
        self.validate_params()
    
    @abstractmethod
    def validate_params(self) -> None:
        """
        Validate chunking parameters.
        
        Raises:
            ValueError: If parameters are invalid
        """
        pass
    
    @abstractmethod
    def chunk(self, text: str, metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Chunk the input text into segments.
        
        Args:
            text: Input text to chunk
            metadata: Optional metadata about the source document
        
        Returns:
            List of chunk dictionaries with 'content' and 'metadata' keys
        """
        pass
    
    def chunk_stream(
        self, 
        text: str, 
        segment_size: int = 100000,
        metadata: Dict[str, Any] = None
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Stream chunk the input text for large documents.
        
        This is the default implementation that processes text in segments.
        Subclasses can override this for more efficient streaming.
        
        Args:
            text: Input text to chunk
            segment_size: Size of each segment to process
            metadata: Optional metadata about the source document
        
        Yields:
            Chunk dictionaries with 'content' and 'metadata' keys
        """
        text_length = len(text)
        chunk_index = 0
        
        for start in range(0, text_length, segment_size):
            end = min(start + segment_size, text_length)
            segment = text[start:end]
            
            # Chunk this segment
            segment_chunks = self.chunk(segment, metadata)
            
            # Adjust positions and yield
            for chunk in segment_chunks:
                chunk["metadata"]["chunk_index"] = chunk_index
                chunk["metadata"]["start_position"] += start
                chunk["metadata"]["end_position"] += start
                chunk_index += 1
                yield chunk
    
    def _create_chunk(
        self,
        content: str,
        index: int,
        start_pos: int,
        end_pos: int,
        chunk_type: str = "text",
        parent_id: Optional[str] = None,
        **additional_metadata
    ) -> Dict[str, Any]:
        """
        Create a standardized chunk dictionary.
        
        Args:
            content: Chunk text content
            index: Chunk index in sequence
            start_pos: Start character position in source text
            end_pos: End character position in source text
            chunk_type: Type of chunk (text, table, image, code)
            parent_id: Optional parent chunk ID for parent-child chunking
            **additional_metadata: Additional metadata fields
        
        Returns:
            Standardized chunk dictionary
        """
        import uuid
        
        chunk_metadata = {
            "chunk_id": str(uuid.uuid4()),
            "chunk_index": index,
            "char_count": len(content),
            "word_count": len(content.split()),
            "start_position": start_pos,
            "end_position": end_pos,
            "chunk_type": chunk_type,
        }
        
        # Add parent_id if provided
        if parent_id:
            chunk_metadata["parent_id"] = parent_id
        
        # Add any additional metadata
        chunk_metadata.update(additional_metadata)
        
        return {
            "content": content,
            "chunk_type": chunk_type,
            "parent_id": parent_id,
            "metadata": chunk_metadata
        }
