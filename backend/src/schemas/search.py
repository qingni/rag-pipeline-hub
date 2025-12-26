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


# ==================== 请求模型 ====================

class SearchRequest(BaseModel):
    """搜索请求"""
    query_text: str = Field(..., min_length=1, max_length=2000, description="查询文本")
    index_ids: Optional[List[str]] = Field(default=None, description="目标索引ID列表")
    top_k: int = Field(default=10, ge=1, le=100, description="返回结果数量")
    threshold: float = Field(default=0.5, ge=0, le=1, description="相似度阈值")
    metric_type: MetricType = Field(default=MetricType.COSINE, description="相似度计算方法")


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


class IndexListResponse(BaseModel):
    """索引列表响应"""
    success: bool = Field(default=True)
    data: List[IndexInfo] = Field(default=[])


# ==================== 历史记录响应 ====================

class HistoryConfig(BaseModel):
    """历史记录配置"""
    top_k: int
    threshold: float
    metric_type: str


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
