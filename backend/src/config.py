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
