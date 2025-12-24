"""
Vector Index Data Models

This module defines the SQLAlchemy model and Pydantic schemas for vector indexes.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum
import uuid

from sqlalchemy import Column, String, Integer, DateTime, Text, Enum as SQLEnum
from sqlalchemy.sql import func
from pydantic import BaseModel, Field, validator

from ..storage.database import Base


class IndexProvider(str, Enum):
    """Vector index provider types"""
    MILVUS = "milvus"
    FAISS = "faiss"


class IndexStatus(str, Enum):
    """Vector index status"""
    CREATED = "created"
    BUILDING = "building"
    READY = "ready"
    UPDATING = "updating"
    ERROR = "error"
    DELETED = "deleted"


class MetricType(str, Enum):
    """Similarity metric types"""
    COSINE = "cosine"
    EUCLIDEAN = "euclidean"
    DOT_PRODUCT = "dot_product"


# ==================== SQLAlchemy Model ====================

class VectorIndex(Base):
    """SQLAlchemy model for vector indexes"""
    
    __tablename__ = "vector_indexes"
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Index information
    index_name = Column(String(255), nullable=False, unique=True)
    index_type = Column(SQLEnum(IndexProvider), nullable=False, default=IndexProvider.FAISS)
    dimension = Column(Integer, nullable=False)
    metric_type = Column(String(50), nullable=False, default="cosine")
    description = Column(Text, nullable=True)
    
    # Provider-specific
    provider_index_id = Column(String(255), nullable=True)  # ID in the vector provider
    
    # Status
    status = Column(SQLEnum(IndexStatus), nullable=False, default=IndexStatus.CREATED)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    def __repr__(self):
        return f"<VectorIndex(id={self.id}, name={self.index_name}, type={self.index_type})>"


# ==================== Pydantic Schemas ====================

class VectorIndexSchema(BaseModel):
    """Pydantic schema for vector index"""
    
    id: Optional[int] = None
    index_name: str = Field(..., min_length=1, max_length=255, description="Index name")
    index_type: IndexProvider = Field(default=IndexProvider.FAISS, description="Vector database provider")
    dimension: int = Field(..., description="Vector dimension")
    metric_type: str = Field(default="cosine", description="Similarity metric")
    description: Optional[str] = Field(None, description="Index description")
    provider_index_id: Optional[str] = Field(None, description="Provider-specific index ID")
    status: IndexStatus = Field(default=IndexStatus.CREATED, description="Index status")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }
    
    @validator("index_name")
    def validate_name(cls, v):
        """Validate index name format"""
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError("Index name must contain only letters, numbers, underscores, and hyphens")
        return v


class CreateIndexRequest(BaseModel):
    """Request model for creating a new index"""
    
    index_name: str = Field(..., min_length=1, max_length=255)
    dimension: int = Field(..., gt=0)
    index_type: IndexProvider = Field(default=IndexProvider.FAISS)
    metric_type: str = Field(default="cosine")
    description: Optional[str] = None
    
    @validator("index_name")
    def validate_name(cls, v):
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError("Index name must contain only letters, numbers, underscores, and hyphens")
        return v


class IndexListResponse(BaseModel):
    """Response model for listing indexes"""
    
    indexes: list
    total: int
    limit: int
    offset: int


class IndexResponse(BaseModel):
    """Response model for single index operations"""
    
    index: VectorIndexSchema
    message: Optional[str] = None
