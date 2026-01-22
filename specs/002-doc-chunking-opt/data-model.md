# Data Model: 文档分块功能优化

**Branch**: `002-doc-chunking-opt` | **Date**: 2026-01-20

## Entity Relationship Diagram

```
┌─────────────────────┐       ┌─────────────────────┐
│   ChunkingTask      │       │   ChunkingResult    │
├─────────────────────┤       ├─────────────────────┤
│ task_id (PK)        │──1:N──│ result_id (PK)      │
│ document_id         │       │ task_id (FK)        │
│ strategy_type       │       │ document_id         │
│ strategy_params     │       │ version             │
│ status              │       │ previous_version_id │
│ created_at          │       │ is_active           │
└─────────────────────┘       │ total_chunks        │
                              │ json_file_path      │
                              │ statistics          │
                              └─────────┬───────────┘
                                        │
                                       1:N
                                        │
                              ┌─────────▼───────────┐
                              │       Chunk         │
                              ├─────────────────────┤
                              │ id (PK)             │
                              │ result_id (FK)      │
                              │ sequence_number     │
                              │ content             │
                              │ chunk_type [NEW]    │
                              │ parent_id [NEW]     │
                              │ chunk_metadata      │
                              └─────────────────────┘
```

## Entity Definitions

### 1. Chunk (扩展)

**表名**: `chunks`

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | String(36) | PK | UUID |
| result_id | String(36) | FK, NOT NULL | 关联 ChunkingResult |
| sequence_number | Integer | NOT NULL | 序号（全局） |
| content | Text | NOT NULL | 块内容 |
| **chunk_type** | Enum | NOT NULL, DEFAULT 'text' | **新增**: text/table/image/code |
| **parent_id** | String(36) | FK, NULLABLE | **新增**: 父块 ID（用于父子分块） |
| chunk_metadata | JSON | NOT NULL | 元数据（位置、token 数等） |
| start_position | Integer | | 起始位置 |
| end_position | Integer | | 结束位置 |
| token_count | Integer | | Token 数量 |

**新增枚举**:
```python
class ChunkType(str, Enum):
    TEXT = "text"
    TABLE = "table"
    IMAGE = "image"
    CODE = "code"
```

**新增索引**:
```sql
CREATE INDEX idx_chunk_parent ON chunks(parent_id);
CREATE INDEX idx_chunk_type ON chunks(chunk_type);
```

---

### 2. ChunkingStrategy (扩展)

**表名**: `chunking_strategies`

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | String(36) | PK | UUID |
| name | String(50) | NOT NULL, UNIQUE | 策略名称 |
| strategy_type | Enum | NOT NULL | character/paragraph/heading/semantic/**parent_child**/**hybrid**/**multimodal** |
| description | Text | | 策略描述 |
| default_params | JSON | | 默认参数 |
| is_enabled | Boolean | DEFAULT TRUE | 是否启用 |

**新增策略类型**:
```python
class StrategyType(str, Enum):
    CHARACTER = "character"
    PARAGRAPH = "paragraph"
    HEADING = "heading"
    SEMANTIC = "semantic"
    PARENT_CHILD = "parent_child"  # 新增
    HYBRID = "hybrid"              # 新增
    MULTIMODAL = "multimodal"      # 新增
```

---

### 3. ParentChunk (新增)

**表名**: `parent_chunks`

用于父子分块场景，存储父块信息。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | String(36) | PK | UUID |
| result_id | String(36) | FK, NOT NULL | 关联 ChunkingResult |
| sequence_number | Integer | NOT NULL | 父块序号 |
| content | Text | NOT NULL | 父块完整内容 |
| start_position | Integer | | 起始位置 |
| end_position | Integer | | 结束位置 |
| child_count | Integer | | 子块数量 |
| metadata | JSON | | 元数据 |

**索引**:
```sql
CREATE INDEX idx_parent_chunk_result ON parent_chunks(result_id);
```

---

### 4. HybridChunkingConfig (新增)

**表名**: `hybrid_chunking_configs`

存储混合分块策略配置。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | String(36) | PK | UUID |
| result_id | String(36) | FK, NOT NULL | 关联 ChunkingResult |
| content_type | Enum | NOT NULL | text/table/image/code |
| strategy_type | Enum | NOT NULL | 该内容类型使用的策略 |
| strategy_params | JSON | | 策略参数 |

---

### 5. ChunkingRecommendation (新增 - 非持久化)

**用途**: API 响应实体，不持久化到数据库。

```python
@dataclass
class DocumentFeatures:
    heading_count: int           # 标题数量
    heading_levels: Dict[int, int]  # 各级标题数量 {1: 3, 2: 12, 3: 25}
    paragraph_count: int         # 段落数量
    avg_paragraph_length: float  # 平均段落长度
    table_count: int             # 表格数量
    image_count: int             # 图片数量
    code_block_count: int        # 代码块数量
    code_block_ratio: float      # 代码块占比
    total_char_count: int        # 总字符数

@dataclass
class ChunkingRecommendation:
    strategy: StrategyType       # 推荐策略
    strategy_name: str           # 策略显示名称
    reason: str                  # 推荐理由
    confidence: float            # 置信度 (0-1)
    estimated_chunks: int        # 预估块数量
    is_top: bool                 # 是否为首选推荐
    suggested_params: Dict       # 建议参数
```

---

### 6. MultimodalChunkMetadata (新增 - JSON Schema)

chunk_metadata 字段的结构定义，根据 chunk_type 有不同的 schema。

**Text Chunk Metadata**:
```json
{
  "chunk_id": "uuid",
  "chunk_index": 0,
  "char_count": 500,
  "word_count": 100,
  "start_position": 0,
  "end_position": 500,
  "page_number": 1,
  "heading_path": ["H1: 标题", "H2: 子标题"]
}
```

**Table Chunk Metadata**:
```json
{
  "chunk_id": "uuid",
  "chunk_index": 10,
  "chunk_type": "table",
  "table_index": 0,
  "page_number": 3,
  "bbox": [100, 200, 500, 400],
  "row_count": 10,
  "column_count": 5,
  "table_title": "表1: 销售数据",
  "has_header": true
}
```

**Image Chunk Metadata**:
```json
{
  "chunk_id": "uuid",
  "chunk_index": 15,
  "chunk_type": "image",
  "image_index": 0,
  "page_number": 5,
  "bbox": [50, 100, 400, 350],
  "image_path": "images/fig1.png",
  "image_base64": "...",
  "caption": "Figure 1: System Architecture",
  "width": 800,
  "height": 600,
  "format": "png"
}
```

**Code Chunk Metadata**:
```json
{
  "chunk_id": "uuid",
  "chunk_index": 20,
  "chunk_type": "code",
  "language": "python",
  "start_line": 1,
  "end_line": 50,
  "file_reference": "example.py"
}
```

---

## State Transitions

### ChunkingTask Status

```
PENDING ──► RUNNING ──► COMPLETED
    │          │            │
    │          ▼            │
    │       PARTIAL ◄───────┘
    │          │
    ▼          ▼
CANCELLED   FAILED
```

### ChunkingResult Version Lifecycle

```
                    ┌─────────────┐
                    │  Version 1  │ (is_active=true)
                    │   (active)  │
                    └──────┬──────┘
                           │ 新分块操作
                           ▼
┌─────────────┐     ┌─────────────┐
│  Version 1  │◄────│  Version 2  │ (is_active=true)
│ (inactive)  │     │   (active)  │
└─────────────┘     └──────┬──────┘
                           │ 回滚操作
                           ▼
┌─────────────┐     ┌─────────────┐
│  Version 1  │     │  Version 2  │
│  (active)   │◄────│ (inactive)  │
└─────────────┘     └─────────────┘
```

---

## Validation Rules

| 实体 | 规则 | 错误消息 |
|------|------|----------|
| Chunk | parent_id 必须引用同一 result_id 的 ParentChunk | "Parent chunk not found in same result" |
| Chunk | chunk_type 为 table/image 时，metadata 必须包含对应字段 | "Missing required metadata for {type} chunk" |
| ParentChunk | child_count 必须与实际子块数量一致 | "Child count mismatch" |
| HybridConfig | content_type 不能重复 | "Duplicate content type configuration" |
| ChunkingResult | 同一 document_id 只能有一个 is_active=true 的记录 | "Multiple active versions found" |

---

## Migration SQL

```sql
-- 1. 扩展 chunks 表
ALTER TABLE chunks 
ADD COLUMN chunk_type VARCHAR(20) DEFAULT 'text' NOT NULL,
ADD COLUMN parent_id VARCHAR(36) REFERENCES parent_chunks(id);

CREATE INDEX idx_chunk_parent ON chunks(parent_id);
CREATE INDEX idx_chunk_type ON chunks(chunk_type);

-- 2. 创建 parent_chunks 表
CREATE TABLE parent_chunks (
    id VARCHAR(36) PRIMARY KEY,
    result_id VARCHAR(36) NOT NULL REFERENCES chunking_results(result_id),
    sequence_number INTEGER NOT NULL,
    content TEXT NOT NULL,
    start_position INTEGER,
    end_position INTEGER,
    child_count INTEGER,
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_parent_chunk_result ON parent_chunks(result_id);

-- 3. 创建 hybrid_chunking_configs 表
CREATE TABLE hybrid_chunking_configs (
    id VARCHAR(36) PRIMARY KEY,
    result_id VARCHAR(36) NOT NULL REFERENCES chunking_results(result_id),
    content_type VARCHAR(20) NOT NULL,
    strategy_type VARCHAR(20) NOT NULL,
    strategy_params JSON,
    UNIQUE(result_id, content_type)
);

-- 4. 更新 chunking_strategies 表（添加新策略）
INSERT INTO chunking_strategies (id, name, strategy_type, description, default_params, is_enabled) VALUES
('ps-parent-child', '父子文档分块', 'parent_child', '生成父块和子块的两层结构，子块用于检索，父块提供上下文', '{"parent_size": 2000, "child_size": 400, "child_overlap": 50}', true),
('ps-hybrid', '混合分块策略', 'hybrid', '针对不同内容类型（正文、代码、表格）应用不同分块策略', '{}', true),
('ps-multimodal', '多模态分块', 'multimodal', '将表格、图片等非文本内容独立分块', '{"include_tables": true, "include_images": true}', true);
```
