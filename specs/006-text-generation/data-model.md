# Data Model: 文本生成功能

**Feature**: 006-text-generation  
**Date**: 2025-12-26  
**Status**: Complete

## Entity Relationship Diagram

```
┌─────────────────────┐
│  GenerationHistory  │
├─────────────────────┤
│  id (PK)            │
│  request_id         │
│  question           │
│  model              │
│  temperature        │
│  max_tokens         │
│  context_summary    │
│  context_sources    │ ──────┐
│  answer             │       │
│  token_usage        │       │
│  processing_time_ms │       │
│  status             │       │
│  error_message      │       │
│  created_at         │       │
│  updated_at         │       │
│  is_deleted         │       │
└─────────────────────┘       │
                              │
                              ▼
                    ┌─────────────────┐
                    │  ContextSource  │ (JSON Array)
                    ├─────────────────┤
                    │  index          │
                    │  content        │
                    │  source_file    │
                    │  similarity     │
                    │  chunk_id       │
                    └─────────────────┘
```

## Entities

### 1. GenerationHistory

生成历史记录，存储每次文本生成的完整信息。

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | Integer | PK, Auto | 主键 |
| request_id | String(36) | Unique, Not Null | 请求唯一标识 (UUID) |
| question | Text | Not Null | 用户问题 |
| model | String(50) | Not Null | 使用的模型名称 |
| temperature | Float | Default 0.7 | 温度参数 |
| max_tokens | Integer | Default 4096 | 最大输出长度 |
| context_summary | Text | Nullable | 上下文摘要（用于列表展示） |
| context_sources | JSON | Nullable | 上下文来源详情 |
| answer | Text | Nullable | 生成的回答 |
| token_usage | JSON | Nullable | Token 使用统计 |
| processing_time_ms | Float | Nullable | 处理耗时（毫秒） |
| status | Enum | Not Null | 状态：pending/generating/completed/failed/cancelled |
| error_message | Text | Nullable | 错误信息 |
| created_at | DateTime | Not Null | 创建时间 |
| updated_at | DateTime | Not Null | 更新时间 |
| is_deleted | Boolean | Default False | 软删除标记 |

**Indexes**:
- `idx_generation_history_request_id` on `request_id`
- `idx_generation_history_created_at` on `created_at`
- `idx_generation_history_status` on `status`

### 2. ContextSource (JSON Structure)

上下文来源信息，存储在 GenerationHistory.context_sources 字段中。

| Field | Type | Description |
|-------|------|-------------|
| index | Integer | 引用编号（1, 2, 3...） |
| content | String | 文档片段内容 |
| source_file | String | 来源文件名 |
| similarity | Float | 相似度分数 |
| chunk_id | String | 关联的 Chunk ID |

**Example**:
```json
[
  {
    "index": 1,
    "content": "RAG（检索增强生成）是一种结合检索和生成的技术...",
    "source_file": "rag-introduction.pdf",
    "similarity": 0.92,
    "chunk_id": "chunk_abc123"
  },
  {
    "index": 2,
    "content": "向量检索通过计算向量相似度来找到相关文档...",
    "source_file": "vector-search.md",
    "similarity": 0.87,
    "chunk_id": "chunk_def456"
  }
]
```

### 3. TokenUsage (JSON Structure)

Token 使用统计，存储在 GenerationHistory.token_usage 字段中。

| Field | Type | Description |
|-------|------|-------------|
| prompt_tokens | Integer | Prompt 消耗的 tokens |
| completion_tokens | Integer | 生成消耗的 tokens |
| total_tokens | Integer | 总 tokens |

**Example**:
```json
{
  "prompt_tokens": 1500,
  "completion_tokens": 800,
  "total_tokens": 2300
}
```

## Enums

### GenerationStatus

```python
class GenerationStatus(str, Enum):
    PENDING = "pending"         # 等待处理
    GENERATING = "generating"   # 生成中
    COMPLETED = "completed"     # 已完成
    FAILED = "failed"           # 失败
    CANCELLED = "cancelled"     # 已取消
```

## Pydantic Schemas

### Request Schemas

```python
class GenerationRequest(BaseModel):
    """生成请求"""
    question: str = Field(..., min_length=1, max_length=10000, description="用户问题")
    model: str = Field(default="deepseek-v3", description="模型名称")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="温度参数")
    max_tokens: int = Field(default=4096, ge=1, le=8192, description="最大输出长度")
    context: List[ContextItem] = Field(default=[], description="检索上下文")
    stream: bool = Field(default=True, description="是否流式输出")

class ContextItem(BaseModel):
    """上下文项"""
    content: str = Field(..., description="文档内容")
    source_file: str = Field(..., description="来源文件")
    similarity: float = Field(..., description="相似度")
    chunk_id: Optional[str] = Field(None, description="Chunk ID")
```

### Response Schemas

```python
class GenerationResponse(BaseModel):
    """生成响应"""
    request_id: str = Field(..., description="请求ID")
    answer: str = Field(..., description="生成的回答")
    model: str = Field(..., description="使用的模型")
    token_usage: TokenUsage = Field(..., description="Token使用统计")
    processing_time_ms: float = Field(..., description="处理耗时")
    sources: List[SourceReference] = Field(default=[], description="引用来源")

class SourceReference(BaseModel):
    """来源引用"""
    index: int = Field(..., description="引用编号")
    source_file: str = Field(..., description="来源文件")
    similarity: float = Field(..., description="相似度")

class StreamChunk(BaseModel):
    """流式输出块"""
    content: str = Field(..., description="内容片段")
    done: bool = Field(default=False, description="是否完成")
    token_usage: Optional[TokenUsage] = Field(None, description="Token统计（仅最后一块）")

class GenerationHistoryItem(BaseModel):
    """历史记录项"""
    id: int = Field(..., description="记录ID")
    request_id: str = Field(..., description="请求ID")
    question: str = Field(..., description="问题")
    answer_preview: str = Field(..., description="回答预览（前200字）")
    model: str = Field(..., description="模型")
    status: GenerationStatus = Field(..., description="状态")
    created_at: datetime = Field(..., description="创建时间")

class GenerationHistoryDetail(BaseModel):
    """历史记录详情"""
    id: int
    request_id: str
    question: str
    answer: str
    model: str
    temperature: float
    max_tokens: int
    context_sources: List[ContextSource]
    token_usage: Optional[TokenUsage]
    processing_time_ms: Optional[float]
    status: GenerationStatus
    error_message: Optional[str]
    created_at: datetime
```

## Model Configuration

### GenerationModel (Runtime Configuration)

```python
GENERATION_MODELS = {
    "deepseek-v3": {
        "name": "deepseek-v3",
        "context_length": 128000,
        "description": "DeepSeek V3 - 0324最新版本，稳定可靠",
        "default_temperature": 0.7,
        "default_max_tokens": 4096,
    },
    "deepseek-r1": {
        "name": "deepseek-r1",
        "context_length": 128000,
        "description": "DeepSeek R1 - 支持 Function Calling，128K超长上下文",
        "default_temperature": 0.7,
        "default_max_tokens": 4096,
    },
    "kimi-k2-instruct": {
        "name": "kimi-k2-instruct",
        "context_length": 128000,
        "description": "Kimi K2 Instruct - 1TB参数，即插即用",
        "default_temperature": 0.7,
        "default_max_tokens": 4096,
    },
}
```

## Database Migration

```sql
-- 创建生成历史表
CREATE TABLE generation_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id VARCHAR(36) NOT NULL UNIQUE,
    question TEXT NOT NULL,
    model VARCHAR(50) NOT NULL,
    temperature REAL DEFAULT 0.7,
    max_tokens INTEGER DEFAULT 4096,
    context_summary TEXT,
    context_sources JSON,
    answer TEXT,
    token_usage JSON,
    processing_time_ms REAL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    error_message TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE
);

-- 创建索引
CREATE INDEX idx_generation_history_request_id ON generation_history(request_id);
CREATE INDEX idx_generation_history_created_at ON generation_history(created_at);
CREATE INDEX idx_generation_history_status ON generation_history(status);
CREATE INDEX idx_generation_history_is_deleted ON generation_history(is_deleted);
```

## Validation Rules

1. **question**: 1-10000 字符，不能为空白
2. **model**: 必须是支持的模型之一
3. **temperature**: 0.0-2.0 范围
4. **max_tokens**: 1-8192 范围
5. **context**: 每项必须包含 content 和 source_file

## State Transitions

```
                    ┌─────────────┐
                    │   PENDING   │
                    └──────┬──────┘
                           │ start
                           ▼
                    ┌─────────────┐
         ┌─────────│ GENERATING  │─────────┐
         │ cancel  └──────┬──────┘  error  │
         │                │ complete       │
         ▼                ▼                ▼
  ┌───────────┐    ┌───────────┐    ┌─────────┐
  │ CANCELLED │    │ COMPLETED │    │ FAILED  │
  └───────────┘    └───────────┘    └─────────┘
```

## Data Retention

- 最大保留 100 条历史记录
- 超出时自动删除最旧的记录（基于 created_at）
- 软删除的记录不计入限制
- 定期清理任务：每小时检查一次
