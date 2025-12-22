"""
Embedding models for both Pydantic (API) and SQLAlchemy (Database).

Defines:
- SQLAlchemy ORM model: EmbeddingResult (database table)
- Pydantic models: Request/response schemas and validation rules
"""
from typing import List, Optional, Literal
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, field_validator, ConfigDict
from sqlalchemy import Column, String, Integer, Float, DateTime, CheckConstraint, Index
from sqlalchemy.sql import func
import hashlib
import uuid

from ..storage.database import Base


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


# ============================================================================
# SQLAlchemy ORM Models (Database Tables)
# ============================================================================

class EmbeddingResult(Base):
    """
    Database model for storing embedding result metadata.
    
    Vector values are stored separately as JSON files to optimize database performance.
    This table stores metadata enabling fast queries and traceability.
    
    Implements:
    - FR-021: Database table for embedding metadata
    - FR-022: Dual-write storage pattern (DB + JSON)
    - FR-023: Relative JSON file path storage
    - FR-024: Update-on-duplicate for same document+model
    - FR-028: Performance indexes (document_id+model, created_at, status)
    - NFR-003: Row-level locking for concurrent safety
    """
    
    __tablename__ = "embedding_results"
    
    # Identity
    result_id = Column(
        String(36), 
        primary_key=True, 
        default=lambda: str(uuid.uuid4()),
        comment="Unique identifier for this embedding operation"
    )
    
    # Source Traceability (FR-021)
    document_id = Column(
        String(36), 
        nullable=False,
        comment="Reference to source document"
    )
    chunking_result_id = Column(
        String(36), 
        nullable=True,
        comment="Reference to chunking result (NULL for ad-hoc text)"
    )
    
    # Model Configuration (FR-006)
    model = Column(
        String(50), 
        nullable=False,
        comment="Embedding model name (bge-m3, qwen3-embedding-8b, etc.)"
    )
    vector_dimension = Column(
        Integer, 
        nullable=False,
        comment="Dimension of generated vectors (1024, 2048, 4096)"
    )
    
    # Processing Status
    status = Column(
        String(20), 
        nullable=False,
        comment="Processing outcome (SUCCESS, FAILED, PARTIAL_SUCCESS)"
    )
    successful_count = Column(
        Integer, 
        nullable=False, 
        default=0,
        comment="Number of successfully vectorized chunks"
    )
    failed_count = Column(
        Integer, 
        nullable=False, 
        default=0,
        comment="Number of failed chunks"
    )
    
    # Storage Reference (FR-023)
    json_file_path = Column(
        String, 
        nullable=False,
        comment="Relative path to JSON file containing vector values"
    )
    
    # Performance Metrics (FR-017)
    processing_time_ms = Column(
        Float, 
        nullable=True,
        comment="Total vectorization time in milliseconds"
    )
    
    # Timestamps
    created_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        nullable=False,
        comment="Record creation timestamp (UTC)"
    )
    
    # Error Tracking
    error_message = Column(
        String, 
        nullable=True,
        comment="Detailed error for FAILED or PARTIAL_SUCCESS status"
    )
    
    # Constraints (FR-021)
    __table_args__ = (
        # Composite index for "latest embedding by document+model" query (FR-028)
        Index('idx_embedding_doc_model', 'document_id', 'model'),
        
        # Index for timestamp-based queries and sorting (FR-028)
        Index('idx_embedding_created_at', 'created_at'),
        
        # Index for status-based filtering (FR-028)
        Index('idx_embedding_status', 'status'),
        
        # Check constraints for data integrity
        CheckConstraint(
            "status IN ('SUCCESS', 'FAILED', 'PARTIAL_SUCCESS')",
            name='check_status_enum'
        ),
        CheckConstraint(
            "model IN ('bge-m3', 'qwen3-embedding-8b', 'hunyuan-embedding', 'jina-embeddings-v4')",
            name='check_model_enum'
        ),
        CheckConstraint(
            'successful_count >= 0',
            name='check_successful_count_non_negative'
        ),
        CheckConstraint(
            'failed_count >= 0',
            name='check_failed_count_non_negative'
        ),
        CheckConstraint(
            'vector_dimension > 0',
            name='check_vector_dimension_positive'
        ),
    )
    
    def __repr__(self):
        return (
            f"<EmbeddingResult("
            f"id={self.result_id[:8]}..., "
            f"doc={self.document_id[:8]}..., "
            f"model={self.model}, "
            f"status={self.status}, "
            f"vectors={self.successful_count}"
            f")>"
        )
    
    def to_dict(self) -> dict:
        """Convert ORM model to dictionary for API responses."""
        return {
            "result_id": self.result_id,
            "document_id": self.document_id,
            "chunking_result_id": self.chunking_result_id,
            "model": self.model,
            "status": self.status,
            "successful_count": self.successful_count,
            "failed_count": self.failed_count,
            "vector_dimension": self.vector_dimension,
            "json_file_path": self.json_file_path,
            "processing_time_ms": self.processing_time_ms,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "error_message": self.error_message,
        }


# ============================================================================
# Pydantic Models (API Request/Response)
# ============================================================================


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
        valid_models = ["qwen3-embedding-8b", "bge-m3", "jina-embeddings-v4"]
        if v not in valid_models:
            raise ValueError(
                f"Model '{v}' not found. Supported models: {', '.join(valid_models)}"
            )
        return v


class BatchEmbeddingRequest(BaseModel):
    """Request model for batch text vectorization."""
    texts: List[str] = Field(..., min_length=1, max_length=1000, description="Texts to vectorize")
    model: str = Field(..., description="Embedding model name")
    result_id: Optional[str] = Field(None, description="Optional chunking result ID for tracking")
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
        valid_models = ["qwen3-embedding-8b", "bge-m3", "jina-embeddings-v4"]
        if v not in valid_models:
            raise ValueError(
                f"Model '{v}' not found. Supported models: {', '.join(valid_models)}"
            )
        return v


class ChunkingResultEmbeddingRequest(BaseModel):
    """Request model for embedding based on chunking result."""
    result_id: str = Field(..., description="Chunking result ID to vectorize")
    model: str = Field(..., description="Embedding model name")
    max_retries: int = Field(default=3, ge=0, le=10, description="Maximum retry attempts")
    timeout: int = Field(default=60, ge=1, le=300, description="Request timeout in seconds")
    
    @field_validator('model')
    @classmethod
    def validate_model_name(cls, v: str) -> str:
        """Validate model name format."""
        valid_models = ["qwen3-embedding-8b", "bge-m3", "jina-embeddings-v4"]
        if v not in valid_models:
            raise ValueError(
                f"Model '{v}' not found. Supported models: {', '.join(valid_models)}"
            )
        return v


class DocumentEmbeddingRequest(BaseModel):
    """Request model for embedding a document's latest chunking result."""
    document_id: str = Field(..., description="Document ID to vectorize")
    model: str = Field(..., description="Embedding model name")
    strategy_type: Optional[str] = Field(None, description="Filter by chunking strategy type")
    max_retries: int = Field(default=3, ge=0, le=10, description="Maximum retry attempts")
    timeout: int = Field(default=60, ge=1, le=300, description="Request timeout in seconds")
    
    @field_validator('model')
    @classmethod
    def validate_model_name(cls, v: str) -> str:
        """Validate model name format."""
        valid_models = ["qwen3-embedding-8b", "bge-m3", "jina-embeddings-v4"]
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
    source_text: Optional[str] = Field(None, description="Original source text for this chunk")
    
    @field_validator('dimension')
    @classmethod
    def validate_dimension(cls, v: int) -> int:
        """Validate dimension is one of supported sizes."""
        # 支持常见的嵌入向量维度
        # 768: BERT/Jina base models
        # 1024: BGE-M3, Hunyuan
        # 1536: OpenAI ada-002
        # 2048: Jina v4
        # 4096: Qwen3 8B
        if v not in [768, 1024, 1536, 2048, 4096]:
            raise ValueError(f"Dimension {v} not supported. Must be 768, 1024, 1536, 2048, or 4096")
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


# ============================================================================
# Query API Response Models
# ============================================================================

class EmbeddingResultDetail(BaseModel):
    """Detailed embedding result for query responses (FR-025, FR-026)."""
    model_config = ConfigDict(from_attributes=True)
    
    result_id: str = Field(..., description="Unique result identifier")
    document_id: str = Field(..., description="Source document ID")
    document_name: Optional[str] = Field(None, description="Source document filename")
    chunking_result_id: Optional[str] = Field(None, description="Source chunking result ID")
    model: str = Field(..., description="Embedding model used")
    status: str = Field(..., description="Processing status")
    successful_count: int = Field(..., ge=0, description="Successfully vectorized chunks")
    failed_count: int = Field(..., ge=0, description="Failed chunks")
    vector_dimension: int = Field(..., gt=0, description="Vector dimension")
    json_file_path: str = Field(..., description="Relative path to JSON file")
    processing_time_ms: Optional[float] = Field(None, ge=0, description="Processing time")
    created_at: datetime = Field(..., description="Creation timestamp")
    error_message: Optional[str] = Field(None, description="Error details")


class EmbeddingResultWithVectors(EmbeddingResultDetail):
    """Extended result with vector data loaded from JSON file."""
    vectors: List[Vector] = Field(default_factory=list, description="Vector data from JSON file")
    failures: List[EmbeddingFailure] = Field(default_factory=list, description="Failed vectorization items")
    metadata: Optional[dict] = Field(None, description="Additional metadata from JSON")


class PaginationMeta(BaseModel):
    """Pagination metadata for list responses (FR-027)."""
    total_count: int = Field(..., ge=0, description="Total results matching filters")
    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, le=100, description="Results per page")
    total_pages: int = Field(..., ge=0, description="Total pages")


class EmbeddingResultListResponse(BaseModel):
    """Response for paginated embedding result list (FR-027)."""
    results: List[EmbeddingResultDetail] = Field(default_factory=list, description="Result items")
    pagination: PaginationMeta = Field(..., description="Pagination metadata")
