"""Configuration module for embedding optimization."""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings."""
    
    # Database
    DATABASE_URL: str = "sqlite:///./app.db"
    
    # File Storage
    UPLOAD_DIR: str = "../uploads"
    RESULTS_DIR: str = "./results"
    MAX_UPLOAD_SIZE: int = 52428800  # 50MB in bytes
    
    # Milvus
    MILVUS_HOST: str = "localhost"
    MILVUS_PORT: int = 19530
    MILVUS_USER: str = ""
    MILVUS_PASSWORD: str = ""
    MILVUS_TIMEOUT: int = 30
    
    # Vector Index
    VECTOR_INDEX_RESULTS_DIR: str = "results/vector_index"
    VECTOR_INDEX_DEFAULT_PROVIDER: str = "milvus"
    
    # Embedding API Configuration
    EMBEDDING_API_KEY: Optional[str] = None
    EMBEDDING_API_BASE_URL: str = ""  # 必须通过 .env 配置
    EMBEDDING_DEFAULT_MODEL: str = "qwen3-embedding-8b"
    
    # Embedding Retry Configuration
    EMBEDDING_MAX_RETRIES: int = 3
    EMBEDDING_TIMEOUT: int = 60
    EMBEDDING_INITIAL_DELAY: int = 1
    EMBEDDING_MAX_DELAY: int = 32
    
    # Embedding Storage Configuration
    EMBEDDING_RESULTS_DIR: str = "results/embedding"
    
    # Embedding Client Authentication
    EMBEDDING_CLIENT_API_KEY: Optional[str] = None
    FRONTEND_ALLOWED_ORIGINS: str = "http://localhost:5173,http://localhost:4173"
    
    # Docling Serve Configuration
    DOCLING_SERVE_URL: str = "http://localhost:5001"
    DOCLING_SERVE_API_KEY: Optional[str] = None
    DOCLING_SERVE_TIMEOUT: int = 600  # 10 分钟，适应大文件处理
    DOCLING_SERVE_ENABLED: bool = True
    
    # Chunking Optimization Configuration
    # Semantic Chunker: bge-m3 (fast) / qwen3-embedding-8b (high-precision)
    SEMANTIC_CHUNKER_MODEL: str = "bge-m3"
    SEMANTIC_CHUNKER_USE_EMBEDDING: bool = True
    SEMANTIC_CHUNKER_SIMILARITY_THRESHOLD: float = 0.7
    
    # Large document processing
    LARGE_DOCUMENT_THRESHOLD: int = 50000000  # 5000万字符
    STREAM_SEGMENT_SIZE: int = 100000  # 流式处理段大小
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    RELOAD: bool = True
    LOG_LEVEL: str = "info"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()


# ============================================================================
# Smart chunking parameters - re-export from smart_params module
# ============================================================================

from .smart_params import (
    # Enums
    DocumentLength,
    DocumentCategory,
    
    # Configuration tables
    FORMAT_BASE_PARAMS,
    LENGTH_ADJUSTMENTS,
    EMBEDDING_MODEL_PARAMS,
    HYBRID_STRATEGY_PARAMS,
    PARENT_CHILD_STRATEGY_PARAMS,
    HEADING_STRATEGY_PARAMS,
    PARAGRAPH_STRATEGY_PARAMS,
    
    # Functions
    get_document_length_category,
    get_format_category,
    get_base_text_params,
    get_adaptive_text_params,
    get_semantic_params,
    get_hybrid_params,
    get_parent_child_params,
    get_heading_params,
    get_paragraph_params,
    get_character_params,
    get_smart_params,
    get_all_format_params,
    get_all_embedding_params,
)

__all__ = [
    # Settings
    "Settings",
    "settings",
    
    # Enums
    "DocumentLength",
    "DocumentCategory",
    
    # Configuration tables
    "FORMAT_BASE_PARAMS",
    "LENGTH_ADJUSTMENTS",
    "EMBEDDING_MODEL_PARAMS",
    "HYBRID_STRATEGY_PARAMS",
    "PARENT_CHILD_STRATEGY_PARAMS",
    "HEADING_STRATEGY_PARAMS",
    "PARAGRAPH_STRATEGY_PARAMS",
    
    # Functions
    "get_document_length_category",
    "get_format_category",
    "get_base_text_params",
    "get_adaptive_text_params",
    "get_semantic_params",
    "get_hybrid_params",
    "get_parent_child_params",
    "get_heading_params",
    "get_paragraph_params",
    "get_character_params",
    "get_smart_params",
    "get_all_format_params",
    "get_all_embedding_params",
]
