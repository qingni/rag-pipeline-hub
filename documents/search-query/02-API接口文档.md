# API接口文档 - 检索查询模块

**生成日期**: 2026-02-26  
**最后更新**: 2026-03-06  
**项目**: RAG Framework - 检索查询模块  
**API版本**: v2  

---

## 📋 目录

1. [接口概述](#1-接口概述)
2. [语义搜索](#2-语义搜索)
3. [混合检索](#3-混合检索)
4. [Collection 管理](#4-collection-管理)
5. [Reranker 服务](#5-reranker-服务)
6. [索引与历史](#6-索引与历史)
7. [错误码说明](#7-错误码说明)

---

## 1. 接口概述

### 1.1 基础信息

| 项目 | 说明 |
|------|------|
| 基础URL | `http://localhost:8000/api/v1` |
| 路由前缀 | `/search` |
| 协议 | HTTP/HTTPS |
| 数据格式 | JSON |

### 1.2 接口列表

| 方法 | 路径 | 描述 | 分类 |
|------|------|------|------|
| POST | /api/v1/search | 语义搜索 | Search |
| POST | /api/v1/search/hybrid | 混合检索（含查询增强 + 三层防御）| Search |
| GET | /api/v1/search/collections | 可用 Collection 列表 | Collection |
| GET | /api/v1/search/reranker/health | Reranker 健康检查 | Reranker |
| GET | /api/v1/search/indexes | 可用索引列表 | Index |
| GET | /api/v1/search/history | 搜索历史列表 | History |
| DELETE | /api/v1/search/history/{id} | 删除单条历史 | History |
| DELETE | /api/v1/search/history | 清空搜索历史 | History |

---

## 2. 语义搜索

### 2.1 执行语义搜索

| 项目 | 说明 |
|------|------|
| 路径 | `POST /api/v1/search` |
| 描述 | 将查询文本转换为向量并在指定索引中检索相似文档 |

#### 请求参数

```json
{
  "query_text": "RAG 系统的核心架构",
  "index_ids": ["1", "2"],
  "top_k": 10,
  "threshold": 0.5,
  "metric_type": "cosine"
}
```

| 参数 | 类型 | 必填 | 默认值 | 约束 | 说明 |
|------|------|------|--------|------|------|
| query_text | string | 是 | - | 1-2000字符 | 查询文本 |
| index_ids | string[] | 否 | null | - | 目标索引ID列表（空则搜索所有） |
| top_k | int | 否 | 10 | 1-100 | 返回结果数量 |
| threshold | float | 否 | 0.5 | 0-1 | 相似度阈值过滤 |
| metric_type | string | 否 | cosine | cosine/euclidean/dot_product | 相似度计算方法 |

#### 响应示例

```json
{
  "success": true,
  "data": {
    "query_id": "a1b2c3d4-...",
    "query_text": "RAG 系统的核心架构",
    "results": [
      {
        "id": "res_001",
        "chunk_id": "chunk_001",
        "text_content": "RAG系统的核心架构包括...",
        "text_summary": "RAG系统核心架构概述",
        "similarity_score": 0.95,
        "similarity_percent": "95.0%",
        "source_index": "技术文档",
        "source_document": "架构设计.pdf",
        "chunk_position": 3,
        "metadata": {},
        "rank": 1
      }
    ],
    "total_count": 10,
    "execution_time_ms": 52
  }
}
```

---

## 3. 混合检索

### 3.1 执行混合检索

| 项目 | 说明 |
|------|------|
| 路径 | `POST /api/v1/search/hybrid` |
| 描述 | 🆕 查询增强 → 稠密+稀疏双路召回 → RRF 粗排 → 三层防御 → Reranker 精排 |

#### 请求参数

```json
{
  "query_text": "RAG 系统的核心架构",
  "collection_ids": ["技术文档知识库"],
  "top_k": 10,
  "threshold": 0.5,
  "metric_type": "cosine",
  "search_mode": "auto",
  "reranker_top_n": 20,
  "reranker_top_k": null,
  "enable_query_enhancement": true,
  "page": 1,
  "page_size": 10
}
```

| 参数 | 类型 | 必填 | 默认值 | 约束 | 说明 |
|------|------|------|--------|------|------|
| query_text | string | 是 | - | 1-2000字符 | 查询文本 |
| collection_ids | string[] | 否 | null | 最多5个 | 目标 Collection ID 列表（空则搜索所有） |
| top_k | int | 否 | 10 | 1-100 | 最多返回结果数量 |
| threshold | float | 否 | 0.5 | 0-1 | 相似度阈值 |
| metric_type | string | 否 | cosine | cosine/euclidean/dot_product | 相似度计算方法 |
| search_mode | string | 否 | auto | auto/hybrid/dense_only | 检索模式 |
| reranker_top_n | int | 否 | 20 | 10-100 | Reranker 候选集大小 |
| reranker_top_k | int | 否 | null（使用top_k） | ≥1 | Reranker 最大返回数 |
| enable_query_enhancement | bool | 否 | true | - | 🆕 是否启用查询增强 |
| page | int | 否 | 1 | ≥1 | 🆕 分页页码 |
| page_size | int | 否 | 10 | 1-100 | 🆕 每页数量 |

#### 响应示例

```json
{
  "success": true,
  "data": {
    "query_id": "a1b2c3d4-...",
    "query_text": "RAG 系统的核心架构",
    "search_mode": "hybrid",
    "reranker_available": true,
    "rrf_k": 60,
    "results": [
      {
        "id": "res_001",
        "chunk_id": "chunk_001",
        "text_content": "RAG系统的核心架构包括检索模块、生成模块...",
        "text_summary": "RAG系统核心架构概述",
        "similarity_score": 0.85,
        "similarity_percent": "85.0%",
        "rrf_score": 0.032,
        "reranker_score": 0.92,
        "search_mode": "hybrid",
        "source_collection": "技术文档知识库",
        "source_document": "架构设计.pdf",
        "chunk_position": 3,
        "metadata": {},
        "rank": 1
      }
    ],
    "total_count": 5,
    "execution_time_ms": 2250,
    "timing": {
      "query_enhancement_ms": 2100,
      "embedding_ms": 50,
      "bm25_ms": 5,
      "search_ms": 80,
      "reranker_ms": 45,
      "total_ms": 2280
    },
    "query_enhancement": null
  }
}
```

> 说明：后端服务内部确实会执行 Query Enhancement，但当前 `api/search.py` 对外响应并未显式组装 `query_enhancement` 字段，因此前端应以 `results`、`search_mode`、`timing`、`reranker_available` 等实际返回字段为准。

### 3.2 检索模式说明

| 模式 | 条件 | 说明 |
|------|------|------|
| auto | 默认 | 乐观尝试混合检索，不可用时自动降级为 dense_only |
| hybrid | 强制 | 稠密+稀疏双路召回 + RRF 融合 |
| dense_only | 强制 | 仅稠密向量检索 |

### 3.3 降级行为

| 阶段 | 降级条件 | 降级行为 |
|------|---------|---------|
| 查询增强 | 🆕 LLM 调用失败/超时 | 降级使用原始查询，不影响后续检索 |
| 查询增强 | 🆕 JSON 解析失败 | 降级使用原始查询 |
| 稀疏向量 | BM25 统计数据不存在 / 稀疏向量为空 | 自动切换到 dense_only 模式 |
| 稀疏向量 | Collection 无 sparse_embedding 字段 | 自动切换到 dense_only 模式 |
| Reranker | Reranker 服务不可用 | 跳过精排，直接返回 RRF 粗排结果 |

### 3.4 文本生成页接入方式

当前文本生成页将混合检索接口作为“生成前自动召回”能力使用，典型流程如下：

1. 先调用 `GET /api/v1/search/collections` 获取可选知识库列表。
2. 用户选择一个或多个 Collection 后，调用 `POST /api/v1/search/hybrid`。
3. 前端将返回结果映射为生成接口所需的 `context` 数组。
4. 再调用 `/api/v1/generation/generate` 或 `/api/v1/generation/stream` 发起回答生成。

文本生成页的典型请求示例：

```json
{
  "query_text": "请总结这份知识库里关于 RAG 架构的设计要点",
  "collection_ids": ["技术文档知识库"],
  "top_k": 5,
  "threshold": 0.3
}
```

文本生成页的典型字段映射如下：

| 检索结果字段 | 生成上下文字段 | 说明 |
|------|------|------|
| `text_content` | `content` | 作为 LLM 参考片段正文 |
| `source_document` | `source_file` | 作为来源文件名展示 |
| `similarity_score` | `similarity` | 用于引用来源排序和展示 |
| `chunk_id` | `chunk_id` | 保留片段标识 |
| `metadata` | `metadata` | 透传额外元数据 |

---

## 4. Collection 管理

### 4.1 获取可用 Collection 列表

| 项目 | 说明 |
|------|------|
| 路径 | `GET /api/v1/search/collections` |
| 描述 | 获取所有可用 Collection 的信息（含稀疏向量标识、文档数、绑定模型）|

#### 响应示例

```json
{
  "success": true,
  "data": [
    {
      "id": "技术文档知识库",
      "name": "技术文档知识库",
      "provider": "milvus",
      "vector_count": 1500,
      "dimension": 1024,
      "metric_type": "cosine",
      "has_sparse": true,
      "document_count": 12,
      "created_at": "2026-02-26T10:00:00"
    }
  ]
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | Collection ID（逻辑知识库名） |
| name | string | Collection 名称 |
| provider | string | 向量数据库类型 |
| vector_count | int | 总向量数量 |
| dimension | int | 向量维度 |
| metric_type | string | 度量类型 |
| has_sparse | bool | 是否含稀疏向量字段 |
| document_count | int | 🆕 文档数量 |
| created_at | datetime | 创建时间 |

> 说明：Collection 与 Embedding 模型的绑定关系存在于服务内部，但当前 `/search/collections` 对外响应模型未暴露 `embedding_model` 字段。

> 文本生成页在进入页面时会优先调用该接口，用于填充“知识库 Collection”下拉选项。

---

## 5. Reranker 服务

### 5.1 Reranker 健康检查

| 项目 | 说明 |
|------|------|
| 路径 | `GET /api/v1/search/reranker/health` |
| 描述 | 检查 Reranker 精排服务是否可用 |

#### 响应示例

```json
{
  "success": true,
  "data": {
    "available": true,
    "model_name": "qwen3-reranker-4b",
    "api_base_url": "http://reranker-server.example.com/api/llmproxy",
    "api_connected": true,
    "supported_models": ["qwen3-reranker-4b"]
  }
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| available | bool | Reranker 是否可用 |
| model_name | string | 模型名称 |
| api_base_url | string | 🆕 API 基础 URL |
| api_connected | bool | 🆕 API 是否已连接 |
| supported_models | string[] | 🆕 支持的模型列表 |

---

## 6. 索引与历史

### 6.1 获取可用索引列表

| 项目 | 说明 |
|------|------|
| 路径 | `GET /api/v1/search/indexes` |
| 描述 | 获取所有可用于搜索的向量索引 |

#### 响应示例

```json
{
  "success": true,
  "data": [
    {
      "id": "1",
      "name": "技术文档索引",
      "provider": "milvus",
      "vector_count": 500,
      "dimension": 1024,
      "metric_type": "cosine",
      "created_at": "2026-02-26T10:00:00"
    }
  ]
}
```

### 6.2 获取搜索历史

| 项目 | 说明 |
|------|------|
| 路径 | `GET /api/v1/search/history` |
| 描述 | 返回用户的搜索历史记录 |

#### 请求参数（Query）

| 参数 | 类型 | 必填 | 默认值 | 约束 | 说明 |
|------|------|------|--------|------|------|
| limit | int | 否 | 20 | 1-50 | 每页数量 |
| offset | int | 否 | 0 | ≥0 | 偏移量 |

#### 响应示例

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "hist_001",
        "query_text": "RAG 核心架构",
        "index_ids": ["技术文档知识库"],
        "config": {
          "top_k": 10,
          "threshold": 0.5,
          "metric_type": "cosine",
          "search_mode": "hybrid",
          "reranker_available": true,
          "reranker_top_n": 20,
          "rrf_k": 60
        },
        "result_count": 5,
        "execution_time_ms": 2250,
        "created_at": "2026-03-04T14:30:00"
      }
    ],
    "total": 42,
    "limit": 20,
    "offset": 0
  }
}
```

### 6.3 删除单条历史记录

| 项目 | 说明 |
|------|------|
| 路径 | `DELETE /api/v1/search/history/{history_id}` |
| 描述 | 根据 ID 删除指定的搜索历史记录 |

#### 响应示例

```json
{
  "success": true,
  "message": "删除成功"
}
```

### 6.4 清空搜索历史

| 项目 | 说明 |
|------|------|
| 路径 | `DELETE /api/v1/search/history` |
| 描述 | 删除所有搜索历史记录 |

#### 响应示例

```json
{
  "success": true,
  "message": "已清空 42 条历史记录"
}
```

---

## 7. 错误码说明

### 7.1 检索相关错误码

| 错误码 | HTTP 状态码 | 说明 | 处理建议 |
|--------|------------|------|----------|
| EMPTY_QUERY | 400 | 查询文本为空 | 输入有效查询文本 |
| QUERY_TOO_LONG | 400 | 查询文本超过2000字符 | 缩短查询文本 |
| MAX_COLLECTIONS_EXCEEDED | 400 | 联合搜索超过5个 Collection | 减少 Collection 数量 |
| INDEX_NOT_FOUND | 404 | 索引不存在 | 检查索引 ID |
| HISTORY_NOT_FOUND | 404 | 历史记录不存在 | 检查历史记录 ID |
| EMBEDDING_SERVICE_ERROR | 503 | Embedding 服务不可用 | 检查 Embedding 服务状态 |
| SEARCH_TIMEOUT | 504 | 搜索超时 | 重试或缩小搜索范围 |
| SEARCH_ERROR | 500 | 搜索内部错误 | 查看服务端日志 |
| INTERNAL_ERROR | 500 | 未知内部错误 | 查看服务端日志 |

### 7.2 错误响应示例

```json
{
  "detail": {
    "success": false,
    "error": {
      "code": "EMPTY_QUERY",
      "message": "查询文本不能为空"
    }
  }
}
```
