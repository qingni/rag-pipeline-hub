"""Base chunker abstract class."""
from abc import ABC, abstractmethod
from typing import List, Dict, Any


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
    
    def _create_chunk(
        self,
        content: str,
        index: int,
        start_pos: int,
        end_pos: int,
        **additional_metadata
    ) -> Dict[str, Any]:
        """
        Create a standardized chunk dictionary.
        
        Args:
            content: Chunk text content
            index: Chunk index in sequence
            start_pos: Start character position in source text
            end_pos: End character position in source text
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
        }
        
        # Add any additional metadata
        chunk_metadata.update(additional_metadata)
        
        return {
            "content": content,
            "metadata": chunk_metadata
        }
