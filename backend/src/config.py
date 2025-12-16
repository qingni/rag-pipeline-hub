"""Application configuration."""
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
    
    # OpenAI
    OPENAI_API_KEY: Optional[str] = None
    
    # AWS Bedrock
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: str = "us-east-1"
    
    # HuggingFace
    HUGGINGFACE_API_KEY: Optional[str] = None
    
    # Milvus
    MILVUS_HOST: str = "localhost"
    MILVUS_PORT: int = 19530
    
    # Pinecone
    PINECONE_API_KEY: Optional[str] = None
    PINECONE_ENVIRONMENT: str = "us-west1-gcp"
    
    # Ollama
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    
    # Embedding API Configuration
    EMBEDDING_API_KEY: Optional[str] = None
    EMBEDDING_API_BASE_URL: str = "http://dev.fit-ai.woa.com/api/llmproxy"
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
