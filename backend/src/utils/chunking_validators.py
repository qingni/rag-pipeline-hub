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
        
        # 短 chunk 合并阈值验证（借鉴 Unstructured.io combine_text_under_n_chars）
        min_chunk_content_size = params.get('min_chunk_content_size', 100)
        if not isinstance(min_chunk_content_size, int):
            raise ValueError("min_chunk_content_size must be an integer")
        if min_chunk_content_size < 0:
            raise ValueError("min_chunk_content_size must be non-negative (0 to disable merging)")
        if min_chunk_content_size > 500:
            raise ValueError("min_chunk_content_size cannot exceed 500")
        
        return {
            'heading_formats': heading_formats,
            'min_chunk_content_size': min_chunk_content_size
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
    def validate_parent_child_params(params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate parameters for parent-child chunking strategy.
        
        Args:
            params: Parameters dictionary
        
        Returns:
            Validated parameters dictionary
        
        Raises:
            ValueError: If parameters are invalid
        """
        parent_chunk_size = params.get('parent_chunk_size', 2000)
        child_chunk_size = params.get('child_chunk_size', 500)
        child_overlap = params.get('child_overlap', 50)
        parent_overlap = params.get('parent_overlap', 200)
        
        # Validate parent chunk size
        if not isinstance(parent_chunk_size, int):
            raise ValueError("parent_chunk_size must be an integer")
        
        if parent_chunk_size < 500:
            raise ValueError("parent_chunk_size must be at least 500")
        
        if parent_chunk_size > 10000:
            raise ValueError("parent_chunk_size cannot exceed 10000")
        
        # Validate child chunk size
        if not isinstance(child_chunk_size, int):
            raise ValueError("child_chunk_size must be an integer")
        
        if child_chunk_size < ChunkingParameterValidator.MIN_CHUNK_SIZE:
            raise ValueError(f"child_chunk_size must be at least {ChunkingParameterValidator.MIN_CHUNK_SIZE}")
        
        if child_chunk_size > 2000:
            raise ValueError("child_chunk_size cannot exceed 2000")
        
        # Validate relationship
        if child_chunk_size >= parent_chunk_size:
            raise ValueError("child_chunk_size must be less than parent_chunk_size")
        
        # Validate overlaps
        if not isinstance(child_overlap, int) or child_overlap < 0:
            raise ValueError("child_overlap must be a non-negative integer")
        
        if child_overlap >= child_chunk_size:
            raise ValueError("child_overlap must be less than child_chunk_size")
        
        if not isinstance(parent_overlap, int) or parent_overlap < 0:
            raise ValueError("parent_overlap must be a non-negative integer")
        
        if parent_overlap >= parent_chunk_size:
            raise ValueError("parent_overlap must be less than parent_chunk_size")
        
        return {
            'parent_chunk_size': parent_chunk_size,
            'child_chunk_size': child_chunk_size,
            'child_overlap': child_overlap,
            'parent_overlap': parent_overlap
        }
    
    @staticmethod
    def validate_hybrid_params(params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate parameters for hybrid chunking strategy.
        
        Note: This now includes multimodal parameters as multimodal 
        has been merged into hybrid.
        
        Args:
            params: Parameters dictionary
        
        Returns:
            Validated parameters dictionary
        
        Raises:
            ValueError: If parameters are invalid
        """
        # Text strategy (extended to support 'none' from multimodal)
        text_strategy = params.get('text_strategy', 'semantic')
        valid_text_strategies = ['semantic', 'paragraph', 'character', 'heading', 'none']
        if text_strategy not in valid_text_strategies:
            raise ValueError(f"text_strategy must be one of {valid_text_strategies}")
        
        # Code strategy
        code_strategy = params.get('code_strategy', 'lines')
        valid_code_strategies = ['lines', 'character', 'none']
        if code_strategy not in valid_code_strategies:
            raise ValueError(f"code_strategy must be one of {valid_code_strategies}")
        
        # Table strategy
        table_strategy = params.get('table_strategy', 'independent')
        valid_table_strategies = ['independent', 'merge_with_text']
        if table_strategy not in valid_table_strategies:
            raise ValueError(f"table_strategy must be one of {valid_table_strategies}")
        
        # Content extraction flags (merged from multimodal)
        include_tables = params.get('include_tables', True)
        if not isinstance(include_tables, bool):
            raise ValueError("include_tables must be a boolean")
        
        include_images = params.get('include_images', True)
        if not isinstance(include_images, bool):
            raise ValueError("include_images must be a boolean")
        
        include_code = params.get('include_code', True)
        if not isinstance(include_code, bool):
            raise ValueError("include_code must be a boolean")
        
        # Text chunk parameters
        text_chunk_size = params.get('text_chunk_size', 500)
        if not isinstance(text_chunk_size, int):
            raise ValueError("text_chunk_size must be an integer")
        
        if text_chunk_size < 100:
            raise ValueError("text_chunk_size must be at least 100")
        
        if text_chunk_size > 5000:
            raise ValueError("text_chunk_size cannot exceed 5000")
        
        text_overlap = params.get('text_overlap', 50)
        if not isinstance(text_overlap, int):
            raise ValueError("text_overlap must be an integer")
        
        if text_overlap < 0:
            raise ValueError("text_overlap must be non-negative")
        
        if text_overlap >= text_chunk_size:
            raise ValueError("text_overlap must be less than text_chunk_size")
        
        # Code chunk parameters
        code_chunk_lines = params.get('code_chunk_lines', 50)
        if not isinstance(code_chunk_lines, int) or code_chunk_lines < 10:
            raise ValueError("code_chunk_lines must be at least 10")
        
        code_overlap_lines = params.get('code_overlap_lines', 5)
        if not isinstance(code_overlap_lines, int) or code_overlap_lines < 0:
            raise ValueError("code_overlap_lines must be non-negative")
        
        # Extraction thresholds (merged from multimodal)
        min_table_rows = params.get('min_table_rows', 2)
        if not isinstance(min_table_rows, int) or min_table_rows < 1:
            raise ValueError("min_table_rows must be a positive integer")
        
        min_code_lines = params.get('min_code_lines', 3)
        if not isinstance(min_code_lines, int) or min_code_lines < 1:
            raise ValueError("min_code_lines must be a positive integer")
        
        # Semantic-specific parameters
        similarity_threshold = params.get('similarity_threshold', 0.5)
        if text_strategy == 'semantic':
            if not isinstance(similarity_threshold, (int, float)):
                raise ValueError("similarity_threshold must be a number")
            if not 0.1 <= similarity_threshold <= 0.9:
                raise ValueError("similarity_threshold must be between 0.1 and 0.9")
        
        use_embedding = params.get('use_embedding', True)
        if not isinstance(use_embedding, bool):
            raise ValueError("use_embedding must be a boolean")
        
        # Embedding model validation (支持的模型列表)
        embedding_model = params.get('embedding_model', 'bge-m3')
        valid_embedding_models = ['bge-m3', 'qwen3-embedding-8b']
        if embedding_model not in valid_embedding_models:
            raise ValueError(f"embedding_model must be one of {valid_embedding_models}")
        
        # Image base path (optional)
        image_base_path = params.get('image_base_path')
        
        return {
            'text_strategy': text_strategy,
            'code_strategy': code_strategy,
            'table_strategy': table_strategy,
            'include_tables': include_tables,
            'include_images': include_images,
            'include_code': include_code,
            'image_base_path': image_base_path,
            'text_chunk_size': text_chunk_size,
            'text_overlap': text_overlap,
            'code_chunk_lines': code_chunk_lines,
            'code_overlap_lines': code_overlap_lines,
            'min_table_rows': min_table_rows,
            'min_code_lines': min_code_lines,
            'similarity_threshold': similarity_threshold,
            'use_embedding': use_embedding,
            'embedding_model': embedding_model
        }
    
    @staticmethod
    def validate(strategy: str, params: Dict[str, Any]) -> None:
        """
        Validate parameters for given strategy.
        
        Args:
            strategy: Strategy name (character, paragraph, heading, semantic, parent_child, hybrid)
            params: Parameters dictionary
        
        Raises:
            ValueError: If parameters are invalid
        """
        validators = {
            'character': ChunkingParameterValidator.validate_character_params,
            'paragraph': ChunkingParameterValidator.validate_paragraph_params,
            'heading': ChunkingParameterValidator.validate_heading_params,
            'semantic': ChunkingParameterValidator.validate_semantic_params,
            'parent_child': ChunkingParameterValidator.validate_parent_child_params,
            'hybrid': ChunkingParameterValidator.validate_hybrid_params,
        }
        
        validator = validators.get(strategy)
        if not validator:
            raise ValueError(f"Unknown chunking strategy: {strategy}")
        
        validator(params)
