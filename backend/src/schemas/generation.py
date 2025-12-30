"""Pydantic schemas for text generation feature."""
from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class GenerationStatus(str, Enum):
    """Generation request status."""
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ============== Request Schemas ==============

class ContextItem(BaseModel):
    """Context item from search results."""
    content: str = Field(..., description="文档内容")
    source_file: str = Field(default="未知来源", description="来源文件")
    similarity: float = Field(default=0.0, description="相似度分数")
    chunk_id: Optional[str] = Field(None, description="Chunk ID")
    metadata: Optional[dict] = Field(None, description="额外元数据")


class GenerationRequest(BaseModel):
    """Generation request schema."""
    question: str = Field(..., min_length=1, max_length=10000, description="用户问题")
    model: str = Field(default="deepseek-v3", description="模型名称")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="温度参数")
    max_tokens: int = Field(default=4096, ge=1, le=8192, description="最大输出长度")
    context: List[ContextItem] = Field(default=[], description="检索上下文")
    stream: bool = Field(default=True, description="是否流式输出")


# ============== Response Schemas ==============

class TokenUsage(BaseModel):
    """Token usage statistics."""
    prompt_tokens: int = Field(..., description="Prompt tokens")
    completion_tokens: int = Field(..., description="Completion tokens")
    total_tokens: int = Field(..., description="总 tokens")


class SourceReference(BaseModel):
    """Source reference in generation result."""
    index: int = Field(..., description="引用编号")
    source_file: str = Field(..., description="来源文件")
    similarity: float = Field(..., description="相似度")


class GenerationResponse(BaseModel):
    """Non-streaming generation response."""
    request_id: str = Field(..., description="请求ID")
    answer: str = Field(..., description="生成的回答")
    model: str = Field(..., description="使用的模型")
    token_usage: TokenUsage = Field(..., description="Token使用统计")
    processing_time_ms: float = Field(..., description="处理耗时（毫秒）")
    sources: List[SourceReference] = Field(default=[], description="引用来源")


class StreamChunk(BaseModel):
    """Streaming output chunk."""
    content: str = Field(..., description="内容片段")
    done: bool = Field(default=False, description="是否完成")
    token_usage: Optional[TokenUsage] = Field(None, description="Token统计（仅最后一块）")


# ============== Model Info Schemas ==============

class ModelInfo(BaseModel):
    """Model information schema."""
    name: str = Field(..., description="模型名称")
    context_length: int = Field(..., description="上下文长度")
    description: str = Field(..., description="模型描述")
    default_temperature: float = Field(..., description="默认温度")
    default_max_tokens: int = Field(..., description="默认最大输出长度")


class ModelsResponse(BaseModel):
    """Models list response."""
    models: List[ModelInfo] = Field(..., description="可用模型列表")


# ============== History Schemas ==============

class GenerationHistoryItem(BaseModel):
    """History list item schema."""
    id: int = Field(..., description="记录ID")
    request_id: str = Field(..., description="请求ID")
    question: str = Field(..., description="问题")
    answer_preview: str = Field(..., description="回答预览（前200字）")
    model: str = Field(..., description="模型")
    status: GenerationStatus = Field(..., description="状态")
    created_at: datetime = Field(..., description="创建时间")


class GenerationHistoryDetail(BaseModel):
    """History detail schema."""
    id: int = Field(..., description="记录ID")
    request_id: str = Field(..., description="请求ID")
    question: str = Field(..., description="问题")
    answer: Optional[str] = Field(None, description="回答")
    model: str = Field(..., description="模型")
    temperature: float = Field(..., description="温度参数")
    max_tokens: int = Field(..., description="最大输出长度")
    context_sources: List[ContextItem] = Field(default=[], description="上下文来源")
    token_usage: Optional[TokenUsage] = Field(None, description="Token使用统计")
    processing_time_ms: Optional[float] = Field(None, description="处理耗时")
    status: GenerationStatus = Field(..., description="状态")
    error_message: Optional[str] = Field(None, description="错误信息")
    created_at: datetime = Field(..., description="创建时间")


class HistoryListResponse(BaseModel):
    """History list response with pagination."""
    items: List[GenerationHistoryItem] = Field(..., description="历史记录列表")
    total: int = Field(..., description="总记录数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页大小")
    total_pages: int = Field(..., description="总页数")


# ============== Common Response Schemas ==============

class SuccessResponse(BaseModel):
    """Generic success response."""
    success: bool = Field(default=True, description="是否成功")
    message: str = Field(..., description="消息")


class ErrorResponse(BaseModel):
    """Generic error response."""
    success: bool = Field(default=False, description="是否成功")
    error: str = Field(..., description="错误类型")
    message: str = Field(..., description="错误信息")
    detail: Optional[str] = Field(None, description="详细信息")
