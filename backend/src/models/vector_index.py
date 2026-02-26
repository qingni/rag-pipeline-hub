"""
Vector Index Data Models

This module defines the SQLAlchemy model and Pydantic schemas for vector indexes.

2024-12-24 更新: 添加与向量化任务(EmbeddingResult)的关联支持
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum
import uuid

from sqlalchemy import Column, String, Integer, DateTime, Text, Enum as SQLEnum, BigInteger, Float, JSON, ForeignKey, Boolean
from sqlalchemy.sql import func
from pydantic import BaseModel, Field, validator

from ..storage.database import Base


class IndexProvider(str, Enum):
    """Vector index provider types (大写枚举值)"""
    MILVUS = "MILVUS"


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
    IVF_SQ8 = "IVF_SQ8"
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
    
    # 外部展示用 UUID 标识符
    uuid = Column(String(36), nullable=False, default=lambda: str(uuid.uuid4()), unique=True, index=True)
    
    # Index information
    index_name = Column(String(255), nullable=False, unique=True)
    index_type = Column(SQLEnum(IndexProvider), nullable=False, default=IndexProvider.MILVUS)
    algorithm_type = Column(String(50), nullable=True, default="FLAT")  # FLAT, IVF_FLAT, IVF_PQ, HNSW
    dimension = Column(Integer, nullable=False)
    metric_type = Column(String(50), nullable=False, default="cosine")
    description = Column(Text, nullable=True)
    
    # 数据源关联 (2024-12-24 新增)
    embedding_result_id = Column(String(36), nullable=True)  # 关联的向量化任务ID
    source_document_name = Column(String(255), nullable=True)  # 源文档名称（冗余存储）
    source_model = Column(String(50), nullable=True)  # 源向量化模型（冗余存储）
    
    # Collection 关联（知识库级别）
    collection_name = Column(String(255), nullable=True, default="default_collection")  # 逻辑知识库名称（对外暴露）
    physical_collection_name = Column(String(255), nullable=True)  # 物理 Collection 名称（实际 Milvus Collection，如 default_collection_dim1024）
    
    # Provider-specific
    provider_index_id = Column(String(255), nullable=True)  # ID in the vector provider
    namespace = Column(String(255), nullable=True, default="default")  # 命名空间
    index_params = Column(JSON, nullable=True, default={})  # 索引算法参数
    file_path = Column(String(512), nullable=True)  # 索引文件路径
    milvus_collection = Column(String(255), nullable=True)  # Milvus Collection名称（兼容历史字段）
    
    # Statistics
    vector_count = Column(Integer, nullable=False, default=0)
    
    # 混合检索标志 (2026-02-06 新增)
    has_sparse = Column(Boolean, nullable=False, default=False)  # 是否包含稀疏向量字段
    
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
            "uuid": self.uuid,
            "index_name": self.index_name,
            "index_type": self.index_type.value if self.index_type else None,
            "algorithm_type": self.algorithm_type,
            "dimension": self.dimension,
            "metric_type": self.metric_type,
            "description": self.description,
            "collection_name": self.collection_name,
            "physical_collection_name": self.physical_collection_name,
            "embedding_result_id": self.embedding_result_id,
            "source_document_name": self.source_document_name,
            "source_model": self.source_model,
            "provider_index_id": self.provider_index_id,
            "namespace": self.namespace,
            "index_params": self.index_params,
            "vector_count": self.vector_count,
            "has_sparse": self.has_sparse,
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
    index_type: IndexProvider = Field(default=IndexProvider.MILVUS, description="Vector database provider")
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
    index_type: IndexProvider = Field(default=IndexProvider.MILVUS)
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
    collection_name: Optional[str] = Field(
        default=None, 
        description="Target Collection name. If None, uses default_collection. If specified, appends vectors to that collection."
    )
    provider: IndexProvider = Field(default=IndexProvider.MILVUS, description="Vector database provider")
    index_type: str = Field(default="FLAT", description="Index algorithm type")
    metric_type: str = Field(default="cosine", description="Similarity metric")
    index_params: Optional[Dict[str, Any]] = Field(default={}, description="Index parameters")
    namespace: Optional[str] = Field(default="default", description="Namespace")
    enable_sparse: bool = Field(default=True, description="Enable BM25 sparse vectors for hybrid search")
    
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


# ==================== 混合检索 Pydantic Schemas ====================

class HybridSearchRequest(BaseModel):
    """混合检索请求"""
    
    collection_name: str = Field(..., description="目标 Collection 名称")
    query_text: str = Field(..., description="原始查询文本（用于 Reranker 精排）")
    query_dense_vector: List[float] = Field(..., description="稠密查询向量")
    query_sparse_vector: Optional[Dict[str, float]] = Field(
        None, description="稀疏查询向量（格式：{index: weight}）"
    )
    top_n: int = Field(default=20, ge=5, le=100, description="粗排候选集大小")
    top_k: int = Field(default=5, ge=1, le=50, description="最终返回结果数量")
    enable_reranker: bool = Field(default=True, description="是否启用 Reranker 精排")
    rrf_k: int = Field(default=60, description="RRF 排名平滑因子")
    search_params: Optional[Dict[str, Any]] = Field(None, description="搜索参数")
    output_fields: Optional[List[str]] = Field(
        default=["doc_id", "chunk_index", "metadata"],
        description="返回字段列表"
    )


class HybridSearchResult(BaseModel):
    """混合检索单条结果"""
    
    vector_id: int = Field(..., description="向量ID")
    rrf_score: float = Field(..., description="RRF 粗排融合分数")
    reranker_score: Optional[float] = Field(None, description="Reranker 精排分数")
    final_score: float = Field(..., description="最终排序分数")
    doc_id: str = Field(..., description="文档ID")
    chunk_index: int = Field(..., description="分块索引")
    text: Optional[str] = Field(None, description="文本内容")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")
    search_mode: str = Field(..., description="检索模式（hybrid/dense_only）")


class HybridSearchResponse(BaseModel):
    """混合检索响应"""
    
    success: bool = Field(default=True)
    data: List[HybridSearchResult] = Field(default_factory=list)
    search_mode: str = Field(..., description="实际检索模式（hybrid/dense_only）")
    query_time_ms: float = Field(..., description="总查询耗时（毫秒）")
    rrf_time_ms: Optional[float] = Field(None, description="RRF 粗排耗时")
    reranker_time_ms: Optional[float] = Field(None, description="Reranker 精排耗时")
    total_candidates: int = Field(..., description="粗排候选集大小")
    reranker_available: bool = Field(default=True, description="Reranker 是否可用")


# ==================== 推荐引擎 SQLAlchemy Models ====================

class RecommendationRule(Base):
    """推荐规则 SQLAlchemy 模型
    
    智能推荐引擎的决策规则实体，按优先级排序匹配。
    """
    
    __tablename__ = "recommendation_rules"
    
    rule_id = Column(String(36), primary_key=True)
    priority = Column(Integer, nullable=False)
    min_vector_count = Column(Integer, nullable=True)
    max_vector_count = Column(Integer, nullable=True)
    min_dimension = Column(Integer, nullable=True)
    max_dimension = Column(Integer, nullable=True)
    embedding_models = Column(Text, nullable=True)  # JSON array string
    recommended_index_type = Column(String(16), nullable=False)
    recommended_metric_type = Column(String(16), nullable=True)
    reason_template = Column(Text, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    def __repr__(self):
        return f"<RecommendationRule(id={self.rule_id}, priority={self.priority}, index_type={self.recommended_index_type})>"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "priority": self.priority,
            "min_vector_count": self.min_vector_count,
            "max_vector_count": self.max_vector_count,
            "min_dimension": self.min_dimension,
            "max_dimension": self.max_dimension,
            "embedding_models": self.embedding_models,
            "recommended_index_type": self.recommended_index_type,
            "recommended_metric_type": self.recommended_metric_type,
            "reason_template": self.reason_template,
            "is_active": self.is_active,
        }


class RecommendationLog(Base):
    """推荐行为日志 SQLAlchemy 模型
    
    记录用户对推荐值的采纳/修改行为，用于推荐采纳率统计。
    """
    
    __tablename__ = "recommendation_logs"
    
    log_id = Column(Integer, primary_key=True, autoincrement=True)
    embedding_task_id = Column(String(36), nullable=False)
    recommended_index_type = Column(String(16), nullable=False)
    recommended_metric_type = Column(String(16), nullable=False)
    final_index_type = Column(String(16), nullable=False)
    final_metric_type = Column(String(16), nullable=False)
    is_modified = Column(Boolean, nullable=False, default=False)
    is_fallback = Column(Boolean, nullable=False, default=False)
    reason = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    def __repr__(self):
        return f"<RecommendationLog(id={self.log_id}, task={self.embedding_task_id}, modified={self.is_modified})>"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "log_id": self.log_id,
            "embedding_task_id": self.embedding_task_id,
            "recommended_index_type": self.recommended_index_type,
            "recommended_metric_type": self.recommended_metric_type,
            "final_index_type": self.final_index_type,
            "final_metric_type": self.final_metric_type,
            "is_modified": self.is_modified,
            "is_fallback": self.is_fallback,
            "reason": self.reason,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ==================== 推荐引擎 Pydantic Schemas ====================

class RecommendRequest(BaseModel):
    """智能推荐请求"""
    
    embedding_task_id: str = Field(..., description="向量化任务ID")
    vector_count: Optional[int] = Field(None, ge=0, description="向量数量（可选覆盖）")
    dimension: Optional[int] = Field(None, description="向量维度（可选覆盖）")
    embedding_model: Optional[str] = Field(None, description="Embedding 模型名称（可选覆盖）")


class RecommendResult(BaseModel):
    """推荐结果"""
    
    recommended_index_type: str = Field(..., description="推荐的索引算法")
    recommended_metric_type: str = Field(..., description="推荐的度量类型")
    reason: str = Field(..., description="推荐理由文案")
    is_fallback: bool = Field(default=False, description="是否使用了兜底默认值")
    vector_count: Optional[int] = Field(None, description="用于推荐的数据量")
    dimension: Optional[int] = Field(None, description="用于推荐的向量维度")
    embedding_model: Optional[str] = Field(None, description="用于推荐的模型名称")


class RecommendResponse(BaseModel):
    """推荐响应"""
    
    success: bool = Field(default=True)
    data: RecommendResult


class RecommendLogRequest(BaseModel):
    """记录推荐采纳行为请求"""
    
    embedding_task_id: str = Field(..., description="向量化任务ID")
    recommended_index_type: str = Field(..., description="推荐的索引算法")
    recommended_metric_type: str = Field(..., description="推荐的度量类型")
    final_index_type: str = Field(..., description="用户最终选择的索引算法")
    final_metric_type: str = Field(..., description="用户最终选择的度量类型")
    is_fallback: bool = Field(default=False, description="是否使用了兜底默认值")
    reason: Optional[str] = Field(None, description="推荐理由文案")


class RecommendLogResponse(BaseModel):
    """记录推荐采纳行为响应"""
    
    success: bool = Field(default=True)
    log_id: int
    is_modified: bool = Field(..., description="用户是否修改了推荐值")
    message: str


class RecommendStatsResponse(BaseModel):
    """推荐统计响应"""
    
    success: bool = Field(default=True)
    data: Dict[str, Any]
