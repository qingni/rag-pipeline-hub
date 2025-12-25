# Data Model: 搜索查询功能

**Feature**: 005-search-query  
**Date**: 2025-12-25

## Entity Relationship Diagram

```text
┌─────────────────────┐       ┌─────────────────────┐
│    SearchQuery      │       │    SearchResult     │
├─────────────────────┤       ├─────────────────────┤
│ id: UUID (PK)       │       │ id: UUID (PK)       │
│ query_text: str     │──1:N──│ query_id: UUID (FK) │
│ query_vector: bytes │       │ chunk_id: str       │
│ index_ids: JSON     │       │ text_content: str   │
│ top_k: int          │       │ similarity_score: f │
│ threshold: float    │       │ source_index: str   │
│ metric_type: str    │       │ source_document: str│
│ created_at: datetime│       │ metadata: JSON      │
└─────────────────────┘       │ rank: int           │
                              └─────────────────────┘

┌─────────────────────┐       ┌─────────────────────┐
│   SearchHistory     │       │   SearchConfig      │
├─────────────────────┤       ├─────────────────────┤
│ id: UUID (PK)       │       │ id: UUID (PK)       │
│ query_text: str     │       │ name: str           │
│ index_ids: JSON     │       │ default_index_id: s │
│ config: JSON        │       │ default_top_k: int  │
│ result_count: int   │       │ default_threshold: f│
│ execution_time_ms:i │       │ default_metric: str │
│ created_at: datetime│       │ is_default: bool    │
└─────────────────────┘       │ created_at: datetime│
                              └─────────────────────┘
```

## Entities

### 1. SearchQuery (搜索查询)

代表一次搜索请求的完整信息。

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK, auto-generated | 查询唯一标识 |
| query_text | string | NOT NULL, max 2000 chars | 用户输入的查询文本 |
| query_vector | bytes | NULL | 查询文本的向量表示（可选缓存） |
| index_ids | JSON array | NOT NULL, min 1 item | 目标索引ID列表 |
| top_k | integer | NOT NULL, range 1-100, default 10 | 返回结果数量 |
| threshold | float | NOT NULL, range 0-1, default 0.5 | 相似度阈值 |
| metric_type | string | ENUM: cosine, euclidean, dot_product | 相似度计算方法 |
| created_at | datetime | NOT NULL, auto | 创建时间 |

**Validation Rules**:
- `query_text` 不能为空或仅包含空格
- `index_ids` 至少包含一个有效的索引ID
- `top_k` 必须在 1-100 范围内
- `threshold` 必须在 0-1 范围内

---

### 2. SearchResult (搜索结果)

代表单条搜索结果。

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK, auto-generated | 结果唯一标识 |
| query_id | UUID | FK → SearchQuery.id | 关联的查询ID |
| chunk_id | string | NOT NULL | 文档片段ID |
| text_content | string | NOT NULL | 文档片段文本内容 |
| similarity_score | float | NOT NULL, range 0-1 | 相似度分数 |
| source_index | string | NOT NULL | 来源索引名称 |
| source_document | string | NOT NULL | 来源文档名称 |
| metadata | JSON | NULL | 额外元数据 |
| rank | integer | NOT NULL | 结果排名（1-based） |

**Validation Rules**:
- `similarity_score` 必须在 0-1 范围内
- `rank` 必须为正整数

---

### 3. SearchHistory (搜索历史)

记录用户的搜索历史，用于快速重复查询。

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK, auto-generated | 历史记录唯一标识 |
| query_text | string | NOT NULL | 查询文本 |
| index_ids | JSON array | NOT NULL | 搜索的索引列表 |
| config | JSON | NOT NULL | 搜索配置快照 |
| result_count | integer | NOT NULL, >= 0 | 返回结果数量 |
| execution_time_ms | integer | NOT NULL, >= 0 | 执行耗时（毫秒） |
| created_at | datetime | NOT NULL, auto | 创建时间 |

**Config JSON Structure**:
```json
{
  "top_k": 10,
  "threshold": 0.5,
  "metric_type": "cosine"
}
```

---

### 4. SearchConfig (搜索配置)

存储用户的搜索配置预设。

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK, auto-generated | 配置唯一标识 |
| name | string | NOT NULL, unique | 配置名称 |
| default_index_id | string | NULL | 默认索引ID |
| default_top_k | integer | NOT NULL, default 10 | 默认返回数量 |
| default_threshold | float | NOT NULL, default 0.5 | 默认相似度阈值 |
| default_metric | string | NOT NULL, default 'cosine' | 默认相似度方法 |
| is_default | boolean | NOT NULL, default false | 是否为默认配置 |
| created_at | datetime | NOT NULL, auto | 创建时间 |

---

## Enumerations

### MetricType (相似度计算方法)

| Value | Description |
|-------|-------------|
| `cosine` | 余弦相似度（默认） |
| `euclidean` | 欧氏距离 |
| `dot_product` | 点积 |

---

## Relationships

| From | To | Type | Description |
|------|-----|------|-------------|
| SearchQuery | SearchResult | 1:N | 一次查询产生多条结果 |
| SearchQuery | VectorIndex | N:M | 一次查询可搜索多个索引 |
| SearchHistory | SearchQuery | Reference | 历史记录引用查询参数 |

---

## Indexes (Database)

| Table | Index | Columns | Purpose |
|-------|-------|---------|---------|
| search_history | idx_history_created | created_at DESC | 按时间倒序查询 |
| search_history | idx_history_query | query_text | 按查询文本搜索 |
| search_result | idx_result_query | query_id | 按查询ID关联 |
| search_result | idx_result_score | similarity_score DESC | 按相似度排序 |

---

## State Transitions

SearchQuery 无状态转换（一次性操作）。

SearchHistory 生命周期：
```text
Created → Active → Deleted
```

---

## Data Retention

| Entity | Retention Policy |
|--------|------------------|
| SearchQuery | 不持久化，仅运行时存在 |
| SearchResult | 不持久化，仅运行时存在 |
| SearchHistory | 保留最近 50 条，超出自动删除最旧记录 |
| SearchConfig | 永久保留 |
