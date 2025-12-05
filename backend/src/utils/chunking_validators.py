"""Parameter validators for chunking operations."""
from typing import Dict, Any


class ChunkingParameterValidator:
    """Validator for chunking parameters."""
    
    # Parameter constraints
    MIN_CHUNK_SIZE = 50
    MAX_CHUNK_SIZE = 5000
    MIN_OVERLAP = 0
    MAX_OVERLAP = 500
    
    @staticmethod
    def validate_character_params(params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate parameters for character chunking strategy.
        
        Args:
            params: Parameters dictionary
        
        Returns:
            Validated parameters dictionary
        
        Raises:
            ValueError: If parameters are invalid
        """
        chunk_size = params.get('chunk_size')
        chunk_overlap = params.get('chunk_overlap', 0)
        
        if chunk_size is None:
            raise ValueError("chunk_size is required for character chunking")
        
        if not isinstance(chunk_size, int):
            raise ValueError("chunk_size must be an integer")
        
        if chunk_size < ChunkingParameterValidator.MIN_CHUNK_SIZE:
            raise ValueError(f"chunk_size must be at least {ChunkingParameterValidator.MIN_CHUNK_SIZE}")
        
        if chunk_size > ChunkingParameterValidator.MAX_CHUNK_SIZE:
            raise ValueError(f"chunk_size cannot exceed {ChunkingParameterValidator.MAX_CHUNK_SIZE}")
        
        if not isinstance(chunk_overlap, int):
            raise ValueError("chunk_overlap must be an integer")
        
        if chunk_overlap < ChunkingParameterValidator.MIN_OVERLAP:
            raise ValueError(f"chunk_overlap must be at least {ChunkingParameterValidator.MIN_OVERLAP}")
        
        if chunk_overlap > ChunkingParameterValidator.MAX_OVERLAP:
            raise ValueError(f"chunk_overlap cannot exceed {ChunkingParameterValidator.MAX_OVERLAP}")
        
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be less than chunk_size")
        
        return {
            'chunk_size': chunk_size,
            'chunk_overlap': chunk_overlap
        }
    
    @staticmethod
    def validate_paragraph_params(params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate parameters for paragraph chunking strategy.
        
        Args:
            params: Parameters dictionary
        
        Returns:
            Validated parameters dictionary
        
        Raises:
            ValueError: If parameters are invalid
        """
        chunk_size = params.get('chunk_size', 800)
        
        if not isinstance(chunk_size, int):
            raise ValueError("chunk_size must be an integer")
        
        if chunk_size < ChunkingParameterValidator.MIN_CHUNK_SIZE:
            raise ValueError(f"chunk_size must be at least {ChunkingParameterValidator.MIN_CHUNK_SIZE}")
        
        if chunk_size > ChunkingParameterValidator.MAX_CHUNK_SIZE:
            raise ValueError(f"chunk_size cannot exceed {ChunkingParameterValidator.MAX_CHUNK_SIZE}")
        
        return {
            'chunk_size': chunk_size
        }
    
    @staticmethod
    def validate_heading_params(params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate parameters for heading chunking strategy.
        
        Args:
            params: Parameters dictionary
        
        Returns:
            Validated parameters dictionary
        
        Raises:
            ValueError: If parameters are invalid
        """
        # Heading strategy has no size constraints, but validate format
        heading_formats = params.get('heading_formats', ['markdown', 'html'])
        
        if not isinstance(heading_formats, list):
            raise ValueError("heading_formats must be a list")
        
        valid_formats = ['markdown', 'html']
        for fmt in heading_formats:
            if fmt not in valid_formats:
                raise ValueError(f"Invalid heading format: {fmt}. Must be one of {valid_formats}")
        
        return {
            'heading_formats': heading_formats
        }
    
    @staticmethod
    def validate_semantic_params(params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate parameters for semantic chunking strategy.
        
        Args:
            params: Parameters dictionary
        
        Returns:
            Validated parameters dictionary
        
        Raises:
            ValueError: If parameters are invalid
        """
        min_chunk_size = params.get('min_chunk_size', 300)
        max_chunk_size = params.get('max_chunk_size', 1200)
        similarity_threshold = params.get('similarity_threshold', 0.3)
        
        if not isinstance(min_chunk_size, int):
            raise ValueError("min_chunk_size must be an integer")
        
        if not isinstance(max_chunk_size, int):
            raise ValueError("max_chunk_size must be an integer")
        
        if min_chunk_size < ChunkingParameterValidator.MIN_CHUNK_SIZE:
            raise ValueError(f"min_chunk_size must be at least {ChunkingParameterValidator.MIN_CHUNK_SIZE}")
        
        if max_chunk_size > ChunkingParameterValidator.MAX_CHUNK_SIZE:
            raise ValueError(f"max_chunk_size cannot exceed {ChunkingParameterValidator.MAX_CHUNK_SIZE}")
        
        if min_chunk_size >= max_chunk_size:
            raise ValueError("min_chunk_size must be less than max_chunk_size")
        
        if not isinstance(similarity_threshold, (int, float)):
            raise ValueError("similarity_threshold must be a number")
        
        if not 0 <= similarity_threshold <= 1:
            raise ValueError("similarity_threshold must be between 0 and 1")
        
        return {
            'min_chunk_size': min_chunk_size,
            'max_chunk_size': max_chunk_size,
            'similarity_threshold': similarity_threshold
        }
    
    @staticmethod
    def validate(strategy: str, params: Dict[str, Any]) -> None:
        """
        Validate parameters for given strategy.
        
        Args:
            strategy: Strategy name (character, paragraph, heading, semantic)
            params: Parameters dictionary
        
        Raises:
            ValueError: If parameters are invalid
        """
        validators = {
            'character': ChunkingParameterValidator.validate_character_params,
            'paragraph': ChunkingParameterValidator.validate_paragraph_params,
            'heading': ChunkingParameterValidator.validate_heading_params,
            'semantic': ChunkingParameterValidator.validate_semantic_params,
        }
        
        validator = validators.get(strategy)
        if not validator:
            raise ValueError(f"Unknown chunking strategy: {strategy}")
        
        validator(params)
