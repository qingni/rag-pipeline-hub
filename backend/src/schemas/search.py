"""
搜索查询 Pydantic Schemas

定义 API 请求和响应的数据结构
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class MetricType(str, Enum):
    """相似度计算方法"""
    COSINE = "cosine"
    EUCLIDEAN = "euclidean"
    DOT_PRODUCT = "dot_product"


class SearchMode(str, Enum):
    """检索模式"""
    AUTO = "auto"           # 自动检测（默认）：乐观尝试混合检索 + 自动降级
    HYBRID = "hybrid"       # 强制混合检索
    DENSE_ONLY = "dense_only"  # 强制纯稠密检索


# ==================== 请求模型 ====================

class SearchRequest(BaseModel):
    """搜索请求"""
    query_text: str = Field(..., min_length=1, max_length=2000, description="查询文本")
    index_ids: Optional[List[str]] = Field(default=None, description="目标索引ID列表")
    top_k: int = Field(default=10, ge=1, le=100, description="返回结果数量")
    threshold: float = Field(default=0.5, ge=0, le=1, description="相似度阈值")
    metric_type: MetricType = Field(default=MetricType.COSINE, description="相似度计算方法")


class HybridSearchRequest(BaseModel):
    """混合检索请求"""
    query_text: str = Field(..., min_length=1, max_length=2000, description="查询文本")
    collection_ids: Optional[List[str]] = Field(default=None, max_length=5, description="目标 Collection ID 列表（最多5个）")
    top_k: int = Field(default=10, ge=1, le=100, description="最多返回结果数量")
    threshold: float = Field(default=0.5, ge=0, le=1, description="相似度阈值")
    metric_type: MetricType = Field(default=MetricType.COSINE, description="相似度计算方法")
    search_mode: SearchMode = Field(default=SearchMode.AUTO, description="检索模式")
    reranker_top_n: int = Field(default=20, ge=10, le=100, description="Reranker 候选集大小")
    reranker_top_k: Optional[int] = Field(default=None, ge=1, description="Reranker 最大返回数（默认使用 top_k）")
    enable_query_enhancement: bool = Field(default=True, description="是否启用查询增强（Query Rewrite + Multi-query）")
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=10, ge=1, le=100, description="每页数量")


# ==================== 响应模型 ====================

class SearchResultItem(BaseModel):
    """单条搜索结果"""
    id: str = Field(..., description="结果ID")
    chunk_id: str = Field(..., description="文档片段ID")
    text_content: str = Field(..., description="文档片段内容")
    text_summary: str = Field(..., max_length=200, description="文本摘要")
    similarity_score: float = Field(..., ge=0, le=1, description="相似度分数")
    similarity_percent: str = Field(..., description="相似度百分比")
    source_index: str = Field(..., description="来源索引名称")
    source_document: str = Field(..., description="来源文档名称")
    chunk_position: Optional[int] = Field(default=None, description="片段位置")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="元数据")
    rank: int = Field(..., description="结果排名")


class HybridSearchResultItem(BaseModel):
    """混合检索单条结果"""
    id: str = Field(..., description="结果ID")
    chunk_id: str = Field(..., description="文档片段ID")
    text_content: str = Field(..., description="文档片段完整内容")
    text_summary: str = Field(default="", max_length=200, description="文本摘要（≤200字符）")
    similarity_score: float = Field(default=0.0, description="原始相似度分数")
    similarity_percent: str = Field(default="0.0%", description="相似度百分比")
    rrf_score: Optional[float] = Field(default=None, description="RRF 融合分数（混合检索模式）")
    reranker_score: Optional[float] = Field(default=None, description="Reranker 精排分数")
    search_mode: str = Field(..., description="检索模式标签 (hybrid/dense_only)")
    source_collection: str = Field(default="", description="来源 Collection 名称")
    source_document: str = Field(default="未知文档", description="来源文档名称")
    chunk_position: Optional[int] = Field(default=None, description="片段位置")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="元数据")
    rank: int = Field(..., description="结果排名")


class SearchTiming(BaseModel):
    """检索各阶段耗时明细"""
    query_enhancement_ms: int = Field(default=0, description="查询增强耗时（Query Rewrite + Multi-query）")
    embedding_ms: int = Field(default=0, description="查询向量化耗时")
    bm25_ms: int = Field(default=0, description="BM25 稀疏向量生成耗时")
    search_ms: int = Field(default=0, description="向量检索耗时（含 RRF）")
    reranker_ms: int = Field(default=0, description="Reranker 精排耗时")
    total_ms: int = Field(default=0, description="总耗时")


class QueryEnhancementInfo(BaseModel):
    """查询增强信息（用于调试和前端展示）"""
    enabled: bool = Field(default=False, description="是否启用了查询增强")
    original_query: str = Field(default="", description="原始查询")
    rewritten_query: str = Field(default="", description="改写后的主查询")
    is_complex: bool = Field(default=False, description="是否为复杂查询（触发 Multi-query）")
    sub_queries: List[str] = Field(default_factory=list, description="多查询变体列表")
    all_queries: List[str] = Field(default_factory=list, description="所有实际执行的查询")
    enhancement_time_ms: int = Field(default=0, description="查询增强耗时（毫秒）")
    error: Optional[str] = Field(default=None, description="查询增强错误信息")


class HybridSearchResponseData(BaseModel):
    """混合检索响应数据"""
    query_id: str = Field(..., description="查询ID")
    query_text: str = Field(..., description="原始查询文本")
    search_mode: str = Field(..., description="实际使用的检索模式 (hybrid/dense_only)")
    reranker_available: bool = Field(default=False, description="Reranker 是否可用")
    rrf_k: Optional[int] = Field(default=None, description="使用的 RRF k 值")
    results: List[HybridSearchResultItem] = Field(default=[], description="搜索结果列表")
    total_count: int = Field(..., description="结果总数")
    execution_time_ms: int = Field(..., description="总执行耗时(毫秒)")
    timing: Optional[SearchTiming] = Field(default=None, description="各阶段耗时明细")
    query_enhancement: Optional[QueryEnhancementInfo] = Field(default=None, description="查询增强信息")


class HybridSearchResponse(BaseModel):
    """混合检索响应"""
    success: bool = Field(default=True)
    data: Optional[HybridSearchResponseData] = None
    error: Optional[Dict[str, Any]] = None


class SearchResponseData(BaseModel):
    """搜索响应数据"""
    query_id: str = Field(..., description="查询ID")
    query_text: str = Field(..., description="原始查询文本")
    results: List[SearchResultItem] = Field(default=[], description="搜索结果列表")
    total_count: int = Field(..., description="结果总数")
    execution_time_ms: int = Field(..., description="执行耗时(毫秒)")


class SearchResponse(BaseModel):
    """搜索响应"""
    success: bool = Field(default=True)
    data: Optional[SearchResponseData] = None
    error: Optional[Dict[str, Any]] = None


# ==================== 索引列表响应 ====================

class IndexInfo(BaseModel):
    """索引信息"""
    id: str = Field(..., description="索引ID")
    name: str = Field(..., description="索引名称")
    provider: str = Field(..., description="向量数据库类型")
    vector_count: int = Field(..., description="向量数量")
    dimension: int = Field(..., description="向量维度")
    metric_type: str = Field(default="cosine", description="度量类型 (cosine/euclidean/dot_product)")
    created_at: datetime = Field(..., description="创建时间")


class CollectionInfo(BaseModel):
    """Collection 信息（含稀疏向量标识）"""
    id: str = Field(..., description="Collection ID（逻辑知识库名）")
    name: str = Field(..., description="Collection 名称（逻辑知识库名）")
    provider: str = Field(default="milvus", description="向量数据库类型")
    vector_count: int = Field(default=0, description="总向量数量")
    dimension: int = Field(default=0, description="向量维度")
    metric_type: str = Field(default="cosine", description="度量类型")
    has_sparse: bool = Field(default=False, description="是否含稀疏向量字段")
    document_count: int = Field(default=0, description="文档数量")
    created_at: Optional[datetime] = Field(default=None, description="创建时间")


class CollectionListResponse(BaseModel):
    """Collection 列表响应"""
    success: bool = Field(default=True)
    data: List[CollectionInfo] = Field(default=[])


class IndexListResponse(BaseModel):
    """索引列表响应"""
    success: bool = Field(default=True)
    data: List[IndexInfo] = Field(default=[])


class RerankerHealthData(BaseModel):
    """Reranker 健康检查数据"""
    available: bool = Field(..., description="是否可用")
    model_name: str = Field(default="", description="模型名称")
    api_base_url: str = Field(default="", description="API 基础 URL")
    api_connected: bool = Field(default=False, description="API 是否已连接")
    supported_models: List[str] = Field(default=[], description="支持的模型列表")


class RerankerHealthResponse(BaseModel):
    """Reranker 健康检查响应"""
    success: bool = Field(default=True)
    data: Optional[RerankerHealthData] = None


# ==================== 历史记录响应 ====================

class HistoryConfig(BaseModel):
    """历史记录配置"""
    top_k: int
    threshold: float
    metric_type: str
    search_mode: Optional[str] = Field(default=None, description="检索模式")
    reranker_available: Optional[bool] = Field(default=None, description="Reranker 是否可用")
    reranker_top_n: Optional[int] = Field(default=None, description="Reranker 候选集大小")
    rrf_k: Optional[int] = Field(default=None, description="RRF k 值")


class HistoryItem(BaseModel):
    """历史记录项"""
    id: str = Field(..., description="历史记录ID")
    query_text: str = Field(..., description="查询文本")
    index_ids: List[str] = Field(default=[], description="索引列表")
    config: HistoryConfig = Field(..., description="搜索配置")
    result_count: int = Field(..., description="结果数量")
    execution_time_ms: int = Field(..., description="执行耗时")
    created_at: datetime = Field(..., description="搜索时间")


class HistoryListData(BaseModel):
    """历史列表数据"""
    items: List[HistoryItem] = Field(default=[])
    total: int = Field(..., description="总记录数")
    limit: int = Field(..., description="每页数量")
    offset: int = Field(..., description="偏移量")


class HistoryListResponse(BaseModel):
    """历史列表响应"""
    success: bool = Field(default=True)
    data: Optional[HistoryListData] = None


# ==================== 通用响应 ====================

class SuccessResponse(BaseModel):
    """成功响应"""
    success: bool = Field(default=True)
    message: str = Field(default="操作成功")


class ErrorDetail(BaseModel):
    """错误详情"""
    code: str = Field(..., description="错误代码")
    message: str = Field(..., description="错误信息")
    details: Optional[Dict[str, Any]] = Field(default=None, description="错误详情")


class ErrorResponse(BaseModel):
    """错误响应"""
    success: bool = Field(default=False)
    error: ErrorDetail
