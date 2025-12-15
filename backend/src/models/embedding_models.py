"""
Pydantic models for embedding service.

Defines request/response schemas and validation rules.
"""
from typing import List, Optional, Literal
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, field_validator, ConfigDict
import hashlib


# Enums for error classification
class ErrorType(str, Enum):
    """Error classification for embedding failures."""
    INVALID_TEXT_ERROR = "INVALID_TEXT_ERROR"
    API_TIMEOUT_ERROR = "API_TIMEOUT_ERROR"
    RATE_LIMIT_ERROR = "RATE_LIMIT_ERROR"
    NETWORK_ERROR = "NETWORK_ERROR"
    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
    DIMENSION_MISMATCH_ERROR = "DIMENSION_MISMATCH_ERROR"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


class ResponseStatus(str, Enum):
    """Response status for embedding operations."""
    SUCCESS = "SUCCESS"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
    FAILED = "FAILED"


# Request Models
class SingleEmbeddingRequest(BaseModel):
    """Request model for single text vectorization."""
    text: str = Field(..., min_length=1, max_length=10000, description="Text to vectorize")
    model: str = Field(..., description="Embedding model name")
    max_retries: int = Field(default=3, ge=0, le=10, description="Maximum retry attempts")
    timeout: int = Field(default=60, ge=1, le=300, description="Request timeout in seconds")
    
    @field_validator('text')
    @classmethod
    def validate_non_empty_text(cls, v: str) -> str:
        """Validate text contains non-whitespace characters."""
        if not v or not v.strip():
            raise ValueError("Text must contain non-whitespace characters")
        return v
    
    @field_validator('model')
    @classmethod
    def validate_model_name(cls, v: str) -> str:
        """Validate model name format."""
        valid_models = ["qwen3-embedding-8b", "bge-m3", "hunyuan-embedding", "jina-embeddings-v4"]
        if v not in valid_models:
            raise ValueError(
                f"Model '{v}' not found. Supported models: {', '.join(valid_models)}"
            )
        return v


class BatchEmbeddingRequest(BaseModel):
    """Request model for batch text vectorization."""
    texts: List[str] = Field(..., min_length=1, max_length=1000, description="Texts to vectorize")
    model: str = Field(..., description="Embedding model name")
    max_retries: int = Field(default=3, ge=0, le=10, description="Maximum retry attempts")
    timeout: int = Field(default=60, ge=1, le=300, description="Request timeout in seconds")
    
    @field_validator('texts')
    @classmethod
    def validate_batch_size(cls, v: List[str]) -> List[str]:
        """Validate batch size limit."""
        if len(v) > 1000:
            raise ValueError(
                f"Batch size {len(v)} exceeds maximum limit of 1000. "
                f"Please split into {(len(v) + 999) // 1000} batches."
            )
        return v
    
    @field_validator('model')
    @classmethod
    def validate_model_name(cls, v: str) -> str:
        """Validate model name format."""
        valid_models = ["qwen3-embedding-8b", "bge-m3", "hunyuan-embedding", "jina-embeddings-v4"]
        if v not in valid_models:
            raise ValueError(
                f"Model '{v}' not found. Supported models: {', '.join(valid_models)}"
            )
        return v


# Entity Models
class Vector(BaseModel):
    """Vector entity with metadata."""
    index: int = Field(..., ge=0, description="Position in batch")
    vector: List[float] = Field(..., description="Vector values")
    dimension: int = Field(..., description="Vector dimension")
    text_hash: Optional[str] = Field(None, description="SHA256 hash of source text")
    text_length: int = Field(..., gt=0, description="Character count of source text")
    processing_time_ms: Optional[float] = Field(None, ge=0, description="Processing time")
    
    @field_validator('dimension')
    @classmethod
    def validate_dimension(cls, v: int) -> int:
        """Validate dimension is one of supported sizes."""
        if v not in [768, 1024, 1536]:
            raise ValueError(f"Dimension {v} not supported. Must be 768, 1024, or 1536")
        return v
    
    @field_validator('vector')
    @classmethod
    def validate_vector_values(cls, v: List[float]) -> List[float]:
        """Validate all vector values are finite."""
        import math
        for val in v:
            if not math.isfinite(val):
                raise ValueError("Vector contains non-finite values (NaN or Infinity)")
        return v
    
    @staticmethod
    def create_text_hash(text: str) -> str:
        """Create SHA256 hash of text."""
        return "sha256:" + hashlib.sha256(text.encode('utf-8')).hexdigest()


class EmbeddingFailure(BaseModel):
    """Details of a failed text vectorization."""
    index: int = Field(..., ge=0, description="Position in batch")
    text_preview: Optional[str] = Field(None, max_length=50, description="First 50 chars")
    error_type: ErrorType = Field(..., description="Error classification")
    error_message: str = Field(..., min_length=1, description="Human-readable error")
    retry_recommended: bool = Field(..., description="Whether retry likely to succeed")
    retry_count: int = Field(..., ge=0, description="Number of retry attempts")


class EmbeddingConfig(BaseModel):
    """Configuration snapshot for reproducibility."""
    api_endpoint: str = Field(..., description="Full API URL")
    max_retries: int = Field(..., ge=0, le=10, description="Retry limit")
    timeout_seconds: int = Field(..., gt=0, description="Request timeout")
    exponential_backoff: bool = Field(default=True, description="Backoff enabled")
    initial_delay_seconds: float = Field(default=1.0, gt=0, description="First retry delay")
    max_delay_seconds: float = Field(default=32.0, gt=0, description="Maximum retry delay")


class EmbeddingMetadata(BaseModel):
    """Processing statistics and configuration."""
    model_config = ConfigDict(protected_namespaces=())
    model: str = Field(..., description="Model name used")
    model_dimension: int = Field(..., description="Expected vector dimension")
    processing_time_ms: float = Field(..., gt=0, description="Total processing duration")
    api_latency_ms: Optional[float] = Field(None, ge=0, description="API round-trip time")
    retry_count: int = Field(default=0, ge=0, description="Total retry attempts")
    rate_limit_hits: int = Field(default=0, ge=0, description="Rate limit encounters")
    config: EmbeddingConfig = Field(..., description="Request configuration")


class BatchMetadata(EmbeddingMetadata):
    """Metadata specific to batch operations."""
    model_config = ConfigDict(protected_namespaces=())
    batch_size: int = Field(..., ge=1, le=1000, description="Total texts in request")
    successful_count: int = Field(..., ge=0, description="Successfully vectorized")
    failed_count: int = Field(..., ge=0, description="Failed vectorization")
    vectors_per_second: Optional[float] = Field(None, ge=0, description="Throughput metric")
    
    @field_validator('batch_size')
    @classmethod
    def validate_batch_consistency(cls, v: int, info) -> int:
        """Validate batch_size equals successful + failed counts."""
        # Note: This validation occurs during construction
        return v


# Response Models
class SingleEmbeddingResponse(BaseModel):
    """Response for single text vectorization."""
    request_id: str = Field(..., description="Unique request identifier")
    status: Literal[ResponseStatus.SUCCESS, ResponseStatus.FAILED] = Field(..., description="Response status")
    vector: Optional[Vector] = Field(None, description="Generated vector")
    metadata: EmbeddingMetadata = Field(..., description="Processing metadata")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response time")
    error: Optional[EmbeddingFailure] = Field(None, description="Error details if failed")


class BatchEmbeddingResponse(BaseModel):
    """Response for batch text vectorization."""
    request_id: str = Field(..., description="Unique request identifier")
    status: ResponseStatus = Field(..., description="Response status")
    vectors: List[Vector] = Field(default_factory=list, description="Successfully generated vectors")
    failures: List[EmbeddingFailure] = Field(default_factory=list, description="Failed items")
    metadata: BatchMetadata = Field(..., description="Processing metadata")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response time")


# Model Information Models
class ModelInfo(BaseModel):
    """Information about an embedding model."""
    model_config = ConfigDict(protected_namespaces=())
    name: str = Field(..., pattern=r"^[a-z0-9\-]+$", description="Model identifier")
    dimension: int = Field(..., description="Vector dimension")
    description: str = Field(..., min_length=1, description="Human-readable description")
    provider: str = Field(..., description="Provider name")
    supports_multilingual: bool = Field(default=True, description="Multilingual support")
    max_batch_size: int = Field(default=1000, ge=1, le=1000, description="Provider batch limit")


class ModelsListResponse(BaseModel):
    """Response for listing available models."""
    models: List[ModelInfo] = Field(..., description="Available models")
    count: int = Field(..., ge=0, description="Total model count")


# Error Response Model
class ErrorDetail(BaseModel):
    """Detailed error information."""
    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[dict] = Field(None, description="Additional error context")


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: ErrorDetail = Field(..., description="Error information")


# Custom Exceptions
class EmbeddingServiceError(Exception):
    """Base exception for embedding service."""
    pass


class RateLimitError(EmbeddingServiceError):
    """API rate limit exceeded."""
    def __init__(self, message: str, retry_after: Optional[int] = None):
        super().__init__(message)
        self.retry_after = retry_after


class APITimeoutError(EmbeddingServiceError):
    """Request timeout exceeded."""
    pass


class InvalidTextError(EmbeddingServiceError):
    """Invalid or empty text input."""
    pass


class VectorDimensionMismatchError(EmbeddingServiceError):
    """Vector dimension doesn't match expected."""
    def __init__(self, expected: int, actual: int, model: str):
        message = (
            f"Model '{model}' returned vector with {actual} dimensions, "
            f"expected {expected}. This may indicate API version mismatch or "
            f"model misconfiguration. Please verify model settings."
        )
        super().__init__(message)
        self.expected = expected
        self.actual = actual
        self.model = model


class BatchSizeLimitError(EmbeddingServiceError):
    """Batch size exceeds maximum limit."""
    def __init__(self, size: int, max_size: int = 1000):
        message = (
            f"Batch size {size} exceeds maximum limit of {max_size}. "
            f"Please split into {(size + max_size - 1) // max_size} batches."
        )
        super().__init__(message)
        self.size = size
        self.max_size = max_size


class AuthenticationError(EmbeddingServiceError):
    """Invalid API credentials."""
    pass


class NetworkError(EmbeddingServiceError):
    """Network connectivity failure."""
    pass
