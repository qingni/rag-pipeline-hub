"""
Vector Index Data Models

This module defines the SQLAlchemy model and Pydantic schemas for vector indexes.

2024-12-24 更新: 添加与向量化任务(EmbeddingResult)的关联支持
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum
import uuid

from sqlalchemy import Column, String, Integer, DateTime, Text, Enum as SQLEnum, BigInteger, Float, JSON, ForeignKey
from sqlalchemy.sql import func
from pydantic import BaseModel, Field, validator

from ..storage.database import Base


class IndexProvider(str, Enum):
    """Vector index provider types (大写枚举值)"""
    MILVUS = "MILVUS"
    FAISS = "FAISS"


class IndexStatus(str, Enum):
    """Vector index status (大写枚举值)"""
    BUILDING = "BUILDING"
    READY = "READY"
    UPDATING = "UPDATING"
    ERROR = "ERROR"


class MetricType(str, Enum):
    """Similarity metric types"""
    COSINE = "cosine"
    EUCLIDEAN = "euclidean"
    DOT_PRODUCT = "dot_product"


class IndexType(str, Enum):
    """Index algorithm types"""
    FLAT = "FLAT"
    IVF_FLAT = "IVF_FLAT"
    IVF_PQ = "IVF_PQ"
    HNSW = "HNSW"


# 有效的向量维度列表
VALID_DIMENSIONS = [128, 256, 512, 768, 1024, 1536, 2048, 3072, 4096]


# ==================== SQLAlchemy Model ====================

class VectorIndex(Base):
    """SQLAlchemy model for vector indexes
    
    2024-12-24 更新: 添加 embedding_result_id 等新字段，支持从向量化任务创建索引
    """
    
    __tablename__ = "vector_indexes"
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Index information
    index_name = Column(String(255), nullable=False, unique=True)
    index_type = Column(SQLEnum(IndexProvider), nullable=False, default=IndexProvider.FAISS)
    algorithm_type = Column(String(50), nullable=True, default="FLAT")  # FLAT, IVF_FLAT, IVF_PQ, HNSW
    dimension = Column(Integer, nullable=False)
    metric_type = Column(String(50), nullable=False, default="cosine")
    description = Column(Text, nullable=True)
    
    # 数据源关联 (2024-12-24 新增)
    embedding_result_id = Column(String(36), nullable=True)  # 关联的向量化任务ID
    source_document_name = Column(String(255), nullable=True)  # 源文档名称（冗余存储）
    source_model = Column(String(50), nullable=True)  # 源向量化模型（冗余存储）
    
    # Provider-specific
    provider_index_id = Column(String(255), nullable=True)  # ID in the vector provider
    namespace = Column(String(255), nullable=True, default="default")  # 命名空间
    index_params = Column(JSON, nullable=True, default={})  # 索引算法参数
    file_path = Column(String(512), nullable=True)  # FAISS索引文件路径
    milvus_collection = Column(String(255), nullable=True)  # Milvus Collection名称
    
    # Statistics
    vector_count = Column(Integer, nullable=False, default=0)
    
    # Status
    status = Column(SQLEnum(IndexStatus), nullable=False, default=IndexStatus.BUILDING)
    error_message = Column(Text, nullable=True)  # 错误信息
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    def __repr__(self):
        return f"<VectorIndex(id={self.id}, name={self.index_name}, type={self.index_type})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "index_name": self.index_name,
            "index_type": self.index_type.value if self.index_type else None,
            "algorithm_type": self.algorithm_type,
            "dimension": self.dimension,
            "metric_type": self.metric_type,
            "description": self.description,
            "embedding_result_id": self.embedding_result_id,
            "source_document_name": self.source_document_name,
            "source_model": self.source_model,
            "provider_index_id": self.provider_index_id,
            "namespace": self.namespace,
            "index_params": self.index_params,
            "vector_count": self.vector_count,
            "status": self.status.value if self.status else None,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class IndexOperationLog(Base):
    """索引操作日志模型"""
    
    __tablename__ = "index_operation_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    index_id = Column(Integer, ForeignKey("vector_indexes.id", ondelete="CASCADE"), nullable=True)
    operation_type = Column(String(50), nullable=False)  # CREATE, UPDATE, DELETE, SEARCH, PERSIST, RECOVER
    user_id = Column(String(255), nullable=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_ms = Column(Float, nullable=True)
    status = Column(String(20), nullable=False, default="STARTED")  # STARTED, SUCCESS, FAILED
    details = Column(JSON, nullable=True, default={})
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    def __repr__(self):
        return f"<IndexOperationLog(id={self.id}, index_id={self.index_id}, type={self.operation_type})>"


# ==================== Pydantic Schemas ====================

class VectorIndexSchema(BaseModel):
    """Pydantic schema for vector index"""
    
    id: Optional[int] = None
    index_name: str = Field(..., min_length=1, max_length=255, description="Index name")
    index_type: IndexProvider = Field(default=IndexProvider.FAISS, description="Vector database provider")
    algorithm_type: Optional[str] = Field(default="FLAT", description="Index algorithm type")
    dimension: int = Field(..., description="Vector dimension")
    metric_type: str = Field(default="cosine", description="Similarity metric")
    description: Optional[str] = Field(None, description="Index description")
    embedding_result_id: Optional[str] = Field(None, description="Associated embedding result ID")
    source_document_name: Optional[str] = Field(None, description="Source document name")
    source_model: Optional[str] = Field(None, description="Source embedding model")
    provider_index_id: Optional[str] = Field(None, description="Provider-specific index ID")
    namespace: Optional[str] = Field(default="default", description="Namespace")
    index_params: Optional[Dict[str, Any]] = Field(default={}, description="Index parameters")
    vector_count: int = Field(default=0, description="Vector count")
    status: IndexStatus = Field(default=IndexStatus.BUILDING, description="Index status")
    error_message: Optional[str] = Field(None, description="Error message")
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
    
    @validator("dimension")
    def validate_dimension(cls, v):
        """Validate dimension is in valid range"""
        if v not in VALID_DIMENSIONS:
            raise ValueError(f"Dimension must be one of {VALID_DIMENSIONS}")
        return v


class CreateIndexRequest(BaseModel):
    """Request model for creating a new index"""
    
    index_name: str = Field(..., min_length=1, max_length=255)
    dimension: int = Field(..., gt=0)
    index_type: IndexProvider = Field(default=IndexProvider.FAISS)
    algorithm_type: str = Field(default="FLAT")
    metric_type: str = Field(default="cosine")
    description: Optional[str] = None
    namespace: Optional[str] = Field(default="default")
    index_params: Optional[Dict[str, Any]] = Field(default={})
    
    @validator("index_name")
    def validate_name(cls, v):
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError("Index name must contain only letters, numbers, underscores, and hyphens")
        return v
    
    @validator("dimension")
    def validate_dimension(cls, v):
        if v not in VALID_DIMENSIONS:
            raise ValueError(f"Dimension must be one of {VALID_DIMENSIONS}")
        return v


class CreateIndexFromEmbeddingRequest(BaseModel):
    """Request model for creating index from embedding result"""
    
    embedding_result_id: str = Field(..., description="Embedding result ID")
    name: Optional[str] = Field(None, description="Index name (auto-generated if not provided)")
    provider: IndexProvider = Field(default=IndexProvider.FAISS, description="Vector database provider")
    index_type: str = Field(default="FLAT", description="Index algorithm type")
    metric_type: str = Field(default="cosine", description="Similarity metric")
    index_params: Optional[Dict[str, Any]] = Field(default={}, description="Index parameters")
    namespace: Optional[str] = Field(default="default", description="Namespace")
    
    @validator("name")
    def validate_name(cls, v):
        if v is not None:
            import re
            if not re.match(r'^[a-zA-Z0-9_-]+$', v):
                raise ValueError("Index name must contain only letters, numbers, underscores, and hyphens")
        return v


class IndexListResponse(BaseModel):
    """Response model for listing indexes"""
    
    indexes: List[Dict[str, Any]]
    total: int
    limit: int
    offset: int


class IndexResponse(BaseModel):
    """Response model for single index operations"""
    
    index: Dict[str, Any]
    message: Optional[str] = None


class IndexHistoryResponse(BaseModel):
    """Response model for index history"""
    
    items: List[Dict[str, Any]]
    total: int
    page: int
    page_size: int
    total_pages: int
