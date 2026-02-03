# Data Model: 文档向量化功能优化

**Branch**: `003-vector-embedding-opt` | **Date**: 2026-02-02

## Entity Relationship Diagram

```
┌─────────────────────┐       ┌─────────────────────┐
│   EmbeddingTask     │       │   EmbeddingResult   │
├─────────────────────┤       ├─────────────────────┤
│ task_id (PK)        │──1:1──│ result_id (PK)      │
│ document_id         │       │ task_id (FK)        │
│ chunking_result_id  │       │ document_id         │
│ model               │       │ model               │
│ status              │       │ status              │
│ config [NEW]        │       │ statistics [EXT]    │
│ progress [NEW]      │       │ json_file_path      │
│ created_at          │       │ is_active           │
│ updated_at          │       │ created_at          │
│ completed_at        │       └─────────┬───────────┘
└─────────────────────┘                 │
                                       1:N
                                        │
                              ┌─────────▼───────────┐
                              │   ChunkVector       │
                              ├─────────────────────┤
                              │ id (PK)             │
                              │ result_id (FK)      │
                              │ chunk_id            │
                              │ chunk_type [NEW]    │
                              │ vector              │
                              │ dimension           │
                              │ source [NEW]        │
                              │ content_hash [NEW]  │
                              │ processing_time_ms  │
                              │ error_message       │
                              └─────────────────────┘

┌─────────────────────┐
│    VectorCache      │
├─────────────────────┤
│ cache_key (PK)      │
│ content_hash        │
│ model               │
│ vector              │
│ dimension           │
│ created_at          │
│ last_accessed_at    │
│ access_count        │
└─────────────────────┘
```

## Entity Definitions

### 1. EmbeddingTask (扩展)

**表名**: `embedding_tasks`

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| task_id | String(36) | PK | UUID |
| document_id | String(36) | FK, NOT NULL | 关联文档 |
| chunking_result_id | String(36) | FK, NOT NULL | 关联分块结果 |
| model | String(50) | NOT NULL | 模型名称 |
| status | Enum | NOT NULL | pending/running/completed/partial/failed/cancelled |
| **config** | JSON | NOT NULL | **新增**: 任务配置 |
| **progress** | JSON | | **新增**: 进度信息 |
| created_at | Timestamp | NOT NULL | 创建时间 |
| updated_at | Timestamp | | 更新时间 |
| completed_at | Timestamp | | 完成时间 |

**config 字段结构**:
```json
{
  "batch_size": 50,
  "concurrency": 5,
  "enable_cache": true,
  "incremental": true,
  "force_recompute": false,
  "multimodal_model": "qwen3-vl-embedding-8b"
}
```

**progress 字段结构**:
```json
{
  "total_chunks": 500,
  "completed": 300,
  "failed": 2,
  "cached": 150,
  "current_batch": 6,
  "speed": 25.5,
  "eta_seconds": 8.0
}
```

**新增状态**:
```python
class EmbeddingTaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIAL = "partial"       # 部分成功
    FAILED = "failed"
    CANCELLED = "cancelled"   # 新增：用户取消
```

**新增索引**:
```sql
CREATE INDEX idx_task_document ON embedding_tasks(document_id);
CREATE INDEX idx_task_status ON embedding_tasks(status);
CREATE INDEX idx_task_created ON embedding_tasks(created_at DESC);
```

---

### 2. EmbeddingResult (扩展)

**表名**: `embedding_results`

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| result_id | String(36) | PK | UUID |
| task_id | String(36) | FK | 关联任务 |
| document_id | String(36) | FK, NOT NULL | 关联文档 |
| chunking_result_id | String(36) | FK, NOT NULL | 关联分块结果 |
| model | String(50) | NOT NULL | 模型名称 |
| status | Enum | NOT NULL | SUCCESS/PARTIAL_SUCCESS/FAILED |
| **statistics** | JSON | NOT NULL | **扩展**: 统计信息 |
| json_file_path | String(500) | NOT NULL | 向量文件路径 |
| is_active | Boolean | DEFAULT FALSE | 是否活跃（用于检索） |
| created_at | Timestamp | NOT NULL | 创建时间 |
| error_message | Text | | 错误信息 |

**statistics 字段结构（扩展）**:
```json
{
  "total_chunks": 500,
  "successful_count": 498,
  "failed_count": 2,
  "cached_count": 150,
  "computed_count": 348,
  "text_chunks": 400,
  "table_chunks": 50,
  "image_chunks": 40,
  "code_chunks": 10,
  "processing_time_ms": 12500.5,
  "avg_chunk_time_ms": 25.0,
  "cache_hit_rate": 0.30,
  "multimodal_stats": {
    "image_success": 38,
    "image_fallback": 2,
    "image_failed": 0
  }
}
```

**新增索引**:
```sql
CREATE INDEX idx_result_document_model ON embedding_results(document_id, model);
CREATE INDEX idx_result_is_active ON embedding_results(is_active);
```

---

### 3. ChunkVector (新增 - JSON 存储)

向量化结果的详细数据，存储在 JSON 文件中。

```json
{
  "result_id": "uuid",
  "vectors": [
    {
      "id": "uuid",
      "chunk_id": "chunk-uuid",
      "chunk_type": "text",
      "vector": [0.1, 0.2, ...],
      "dimension": 1024,
      "source": "computed",
      "content_hash": "sha256-hash",
      "processing_time_ms": 25.5,
      "error_message": null
    },
    {
      "id": "uuid",
      "chunk_id": "chunk-uuid-2",
      "chunk_type": "image",
      "vector": [0.3, 0.4, ...],
      "dimension": 1024,
      "source": "computed",
      "content_hash": "sha256-hash-2",
      "processing_time_ms": 150.0,
      "error_message": null,
      "embedding_method": "base64"
    }
  ]
}
```

**source 枚举**:
```python
class VectorSource(str, Enum):
    COMPUTED = "computed"    # 新计算
    CACHED = "cached"        # 来自缓存
```

---

### 4. VectorCache (新增)

**表名**: `vector_cache` (或使用 Redis)

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| cache_key | String(100) | PK | hash(content)[:16] + ":" + model |
| content_hash | String(64) | NOT NULL | SHA-256 全量哈希 |
| model | String(50) | NOT NULL | 模型名称 |
| vector | BLOB | NOT NULL | 向量数据（二进制） |
| dimension | Integer | NOT NULL | 向量维度 |
| created_at | Timestamp | NOT NULL | 创建时间 |
| last_accessed_at | Timestamp | NOT NULL | 最后访问时间 |
| access_count | Integer | DEFAULT 1 | 访问次数 |

**索引**:
```sql
CREATE INDEX idx_cache_model ON vector_cache(model);
CREATE INDEX idx_cache_last_accessed ON vector_cache(last_accessed_at);
```

**缓存键生成规则**:
```python
def make_cache_key(content: str, model: str) -> str:
    content_hash = hashlib.sha256(content.encode()).hexdigest()
    return f"{content_hash[:16]}:{model}"
```

---

### 5. EmbeddingConfig (配置实体)

用于 API 请求和响应的配置结构。

```python
@dataclass
class EmbeddingConfig:
    batch_size: int = 50           # 批量大小 (10-200)
    concurrency: int = 5           # 并发数 (1-20)
    enable_cache: bool = True      # 启用缓存
    incremental: bool = True       # 增量模式
    force_recompute: bool = False  # 强制重新计算
    multimodal_model: str = "qwen3-vl-embedding-8b"  # 多模态模型
    
@dataclass
class EmbeddingProgress:
    total_chunks: int
    completed: int
    failed: int
    cached: int
    current_batch: int
    speed: float                   # 块/秒
    eta_seconds: float             # 预估剩余秒数
    
    @property
    def percentage(self) -> float:
        return (self.completed / self.total_chunks) * 100 if self.total_chunks > 0 else 0
```

---

### 6. EmbeddingComparison (对比实体 - 非持久化)

用于 API 响应的对比结果结构。

```python
@dataclass
class ModelComparisonResult:
    result_id: str
    model: str
    dimension: int
    processing_time_ms: float
    success_rate: float
    cache_hit_rate: float
    image_success_rate: float
    avg_chunk_time_ms: float
    created_at: str

@dataclass
class EmbeddingComparison:
    document_id: str
    results: List[ModelComparisonResult]
```

---

## State Transitions

### EmbeddingTask Status

```
PENDING ──► RUNNING ──► COMPLETED
    │          │            │
    │          ├────────────┼──► PARTIAL (部分失败)
    │          │            │
    │          ▼            │
    │       CANCELLED ◄─────┤ (用户取消)
    │                       │
    ▼                       ▼
FAILED ◄───────────────────┘
```

### EmbeddingResult Active Lifecycle

```
┌─────────────────┐
│  Result A       │ (is_active=true, 当前活跃)
│   (active)      │
└───────┬─────────┘
        │ 用户选择新结果
        ▼
┌─────────────────┐     ┌─────────────────┐
│  Result A       │     │  Result B       │ (is_active=true)
│  (inactive)     │◄────│   (active)      │
└─────────────────┘     └─────────────────┘
```

### VectorCache LRU Lifecycle

```
┌─────────────┐
│  Cache A    │ last_accessed: T1
│  Cache B    │ last_accessed: T2
│  Cache C    │ last_accessed: T3
└─────────────┘
       │
       │ 访问 Cache A
       ▼
┌─────────────┐
│  Cache B    │ last_accessed: T2
│  Cache C    │ last_accessed: T3
│  Cache A    │ last_accessed: T4 (更新)
└─────────────┘
       │
       │ 容量已满，新增 Cache D
       ▼
┌─────────────┐
│  Cache C    │ last_accessed: T3
│  Cache A    │ last_accessed: T4
│  Cache D    │ last_accessed: T5
└─────────────┘
  (Cache B 被淘汰)
```

---

## Validation Rules

| 实体 | 规则 | 错误消息 |
|------|------|----------|
| EmbeddingConfig | batch_size 必须在 10-200 范围内 | "Batch size must be between 10 and 200" |
| EmbeddingConfig | concurrency 必须在 1-20 范围内 | "Concurrency must be between 1 and 20" |
| EmbeddingTask | status 为 RUNNING 时不能重复启动 | "Task is already running" |
| EmbeddingResult | 同一 document_id 只能有一个 is_active=true | "Multiple active results for same document" |
| VectorCache | 缓存向量维度必须与模型匹配 | "Cached vector dimension mismatch" |
| ChunkVector | content_hash 必须为 64 位十六进制字符串 | "Invalid content hash format" |

---

## Migration SQL

```sql
-- 1. 扩展 embedding_tasks 表
ALTER TABLE embedding_tasks 
ADD COLUMN config JSON DEFAULT '{}' NOT NULL,
ADD COLUMN progress JSON DEFAULT NULL,
ADD COLUMN updated_at TIMESTAMP,
ADD COLUMN completed_at TIMESTAMP;

-- 更新状态枚举（如果需要）
-- CANCELLED 状态需要在应用层处理

CREATE INDEX idx_task_document ON embedding_tasks(document_id);
CREATE INDEX idx_task_status ON embedding_tasks(status);
CREATE INDEX idx_task_created ON embedding_tasks(created_at DESC);

-- 2. 扩展 embedding_results 表
ALTER TABLE embedding_results
ADD COLUMN is_active BOOLEAN DEFAULT FALSE;

CREATE INDEX idx_result_document_model ON embedding_results(document_id, model);
CREATE INDEX idx_result_is_active ON embedding_results(is_active);

-- 3. 创建 vector_cache 表
CREATE TABLE vector_cache (
    cache_key VARCHAR(100) PRIMARY KEY,
    content_hash VARCHAR(64) NOT NULL,
    model VARCHAR(50) NOT NULL,
    vector BLOB NOT NULL,
    dimension INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    last_accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    access_count INTEGER DEFAULT 1
);

CREATE INDEX idx_cache_model ON vector_cache(model);
CREATE INDEX idx_cache_last_accessed ON vector_cache(last_accessed_at);

-- 4. 确保只有一个活跃结果的触发器（可选）
CREATE TRIGGER ensure_single_active_result
BEFORE UPDATE ON embedding_results
FOR EACH ROW
WHEN NEW.is_active = TRUE
BEGIN
    UPDATE embedding_results 
    SET is_active = FALSE 
    WHERE document_id = NEW.document_id 
      AND result_id != NEW.result_id 
      AND is_active = TRUE;
END;
```
