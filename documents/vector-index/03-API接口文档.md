# API接口文档 - 向量索引模块

**生成日期**: 2025-12-26  
**最后更新**: 2026-03-06  
**项目**: RAG Framework - 向量索引模块  
**API版本**: custom (`/api/vector-index`)  

---

## 📋 目录

1. [接口概述](#1-接口概述)
2. [索引创建](#2-索引创建)
3. [索引管理](#3-索引管理)
4. [向量操作](#4-向量操作)
5. [向量搜索](#5-向量搜索)
6. [统计信息](#6-统计信息)
7. [错误码说明](#7-错误码说明)

---

## 1. 接口概述

### 1.1 基础信息

| 项目 | 说明 |
|------|------|
| 基础URL | `http://localhost:8000/api/vector-index` |
| 协议 | HTTP/HTTPS |
| 数据格式 | JSON |

### 1.2 接口列表

| 方法 | 路径 | 描述 | 分类 |
|------|------|------|------|
| **索引管理** | | | |
| POST | /api/vector-index/indexes | 创建索引 | Index Management |
| POST | /api/vector-index/indexes/from-embedding | 从向量化结果创建索引 | Index Management |
| GET | /api/vector-index/indexes | 列出所有索引 | Index Management |
| GET | /api/vector-index/indexes/{id} | 获取索引详情 | Index Management |
| DELETE | /api/vector-index/indexes/{id} | 删除索引 | Index Management |
| GET | /api/vector-index/indexes/find-matching | 查找匹配索引 | Index Management |
| POST | /api/vector-index/indexes/{id}/persist | 持久化索引 | Index Management |
| POST | /api/vector-index/indexes/{id}/recover | 恢复索引 | Index Management |
| GET | /api/vector-index/indexes/{id}/statistics | 获取统计信息 | Index Management |
| GET | /api/vector-index/indexes/{id}/query-history | 获取查询历史 | Index Management |
| **Collection 管理** | | | |
| GET | /api/vector-index/collections | 获取 Collection 列表 | Collection |
| **向量操作** | | | |
| POST | /api/vector-index/indexes/{id}/vectors | 添加向量 | Vector Operations |
| PUT | /api/vector-index/indexes/{id}/vectors | 更新向量 | Vector Operations |
| DELETE | /api/vector-index/indexes/{id}/vectors | 删除向量 | Vector Operations |
| **检索** | | | |
| - | - | 检索相关接口已移至 [检索查询模块 API 文档](../search-query/02-API接口文档.md) | Search |
| **历史管理** | | | |
| GET | /api/vector-index/indexes/history | 获取索引历史 | History |
| DELETE | /api/vector-index/history/{id} | 删除历史记录 | History |
| DELETE | /api/vector-index/history/clear-all | 清空所有历史 | History |
| **向量化任务** | | | |
| GET | /api/vector-index/embedding-tasks | 获取向量化任务列表 | Embedding |
| **智能推荐** | | | |
| POST | /api/vector-index/recommend | 智能推荐索引配置 | Recommendation |
| POST | /api/vector-index/recommend/log | 记录推荐采纳行为 | Recommendation |
| GET | /api/vector-index/recommend/stats | 获取推荐统计 | Recommendation |
| **健康检查** | | | |
| GET | /api/vector-index/health | 系统健康检查 | System |

---

## 2. 索引创建

### 2.1 从向量化结果创建索引

| 项目 | 说明 |
|------|------|
| 路径 | `POST /api/vector-index/indexes/from-embedding` |
| 描述 | 从已完成的向量化结果创建向量索引，支持追加到已有 Collection |

#### 请求参数

```json
{
  "embedding_result_id": "emb_123456",
  "name": "idx_技术文档_20260226",
  "collection_name": "knowledge_base_a",
  "provider": "MILVUS",
  "index_type": "HNSW",
  "metric_type": "cosine",
  "index_params": {
    "M": 16,
    "efConstruction": 200
  },
  "namespace": "default",
  "enable_sparse": true
}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| embedding_result_id | string | 是 | 向量化结果ID |
| name | string | 否 | 索引名称，默认自动生成 |
| collection_name | string | 否 | 目标 Collection 名称；可选，不传时由后端按当前逻辑处理 |
| provider | string | 否 | 向量数据库（默认 MILVUS） |
| index_type | string | 否 | 索引算法（FLAT/IVF_FLAT/IVF_SQ8/IVF_PQ/HNSW），默认 FLAT |
| metric_type | string | 否 | 度量类型（cosine/euclidean/dot_product），默认 cosine |
| index_params | object | 否 | 算法参数 |
| namespace | string | 否 | 命名空间（默认 default） |
| enable_sparse | boolean | 否 | 是否启用 BM25 稀疏向量（默认 true） |

#### 响应示例

```json
{
  "id": 1,
  "uuid": "a1b2c3d4-...",
  "index_name": "idx_技术文档_20260226",
  "index_type": "MILVUS",
  "algorithm_type": "HNSW",
  "dimension": 1024,
  "metric_type": "cosine",
  "status": "READY",
  "collection_name": "knowledge_base_a",
  "embedding_result_id": "emb_123456",
  "source_document_name": "技术文档.pdf",
  "source_model": "bge-m3",
  "vector_count": 50,
  "has_sparse": true,
  "namespace": "default",
  "created_at": "2026-02-26T10:30:00Z",
  "updated_at": "2026-02-26T10:30:15Z"
}
```

### 2.2 直接创建空索引

| 项目 | 说明 |
|------|------|
| 路径 | `POST /api/vector-index/indexes` |
| 描述 | 创建一个空的向量索引 |

#### 请求参数

```json
{
  "index_name": "自定义索引",
  "index_type": "MILVUS",
  "algorithm_type": "FLAT",
  "metric_type": "cosine",
  "dimension": 1024,
  "namespace": "default"
}
```

#### 响应示例

```json
{
  "id": 12,
  "uuid": "a1b2c3d4-...",
  "index_name": "自定义索引",
  "index_type": "MILVUS",
  "algorithm_type": "FLAT",
  "dimension": 1024,
  "metric_type": "cosine",
  "status": "READY",
  "vector_count": 0,
  "namespace": "default",
  "created_at": "2026-03-06T10:30:00Z",
  "updated_at": "2026-03-06T10:30:00Z"
}
```

---

## 3. 索引管理

### 3.1 获取索引列表

| 项目 | 说明 |
|------|------|
| 路径 | `GET /api/vector-index/indexes` |
| 描述 | 获取所有向量索引列表 |

#### 请求参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| skip | int | 否 | 0 | 跳过记录数 |
| limit | int | 否 | 100 | 返回记录数 |
| namespace | string | 否 | - | 按命名空间筛选 |
| status | string | 否 | - | 按状态筛选（BUILDING/READY/UPDATING/ERROR） |

#### 响应示例

```json
[
  {
    "id": 1,
    "uuid": "a1b2c3d4-...",
    "index_name": "技术文档索引",
    "index_type": "MILVUS",
    "algorithm_type": "HNSW",
    "metric_type": "cosine",
    "dimension": 1024,
    "vector_count": 50,
    "status": "READY",
    "created_at": "2026-03-06T10:30:00Z",
    "updated_at": "2026-03-06T10:30:15Z"
  }
]
```

### 3.2 获取索引详情

| 项目 | 说明 |
|------|------|
| 路径 | `GET /api/vector-index/indexes/{id}` |
| 描述 | 获取单个索引的详细信息 |

#### 响应示例

```json
{
  "id": 1,
  "uuid": "a1b2c3d4-...",
  "index_name": "技术文档索引",
  "index_type": "MILVUS",
  "algorithm_type": "HNSW",
  "metric_type": "cosine",
  "dimension": 1024,
  "embedding_result_id": "emb_123456",
  "source_document_name": "技术文档.pdf",
  "source_model": "bge-m3",
  "vector_count": 50,
  "status": "READY",
  "created_at": "2026-03-06T10:30:00Z",
  "updated_at": "2026-03-06T10:30:15Z"
}
```

### 3.3 删除索引

| 项目 | 说明 |
|------|------|
| 路径 | `DELETE /api/vector-index/indexes/{id}` |
| 描述 | 删除指定的向量索引，成功时返回 `204 No Content` |

#### 响应示例

无响应体。

### 3.4 获取 Collection 列表（新增）

| 项目 | 说明 |
|------|------|
| 路径 | `GET /api/vector-index/collections` |
| 描述 | 获取所有 Collection 信息（Dify 方案按逻辑知识库聚合） |

#### 响应示例

```json
{
  "collections": [
    {
      "collection_name": "knowledge_base_a",
      "is_default": true,
      "document_count": 5,
      "total_vectors": 250,
      "physical_collections": [
        {"physical_name": "knowledge_base_a_dim1024", "dimension": 1024},
        {"physical_name": "knowledge_base_a_dim2048", "dimension": 2048}
      ],
      "dimensions": [1024, 2048],
      "physical_count": 2
    }
  ],
  "total": 1
}
```

---

## 4. 混合检索（已移至检索查询模块）

> 混合检索、向量搜索、多 Collection 联合搜索、Reranker 健康检查等检索相关接口已移至 [检索查询模块 API 文档](../search-query/02-API接口文档.md)。

---

## 5. 智能推荐引擎（新增）

### 5.1 获取推荐配置

| 项目 | 说明 |
|------|------|
| 路径 | `POST /vector-index/recommend` |
| 描述 | 根据向量特征自动推荐索引算法和度量类型 |

#### 请求参数

```json
{
  "embedding_task_id": "emb_123456",
  "vector_count": 50000,
  "dimension": 1024,
  "embedding_model": "bge-m3"
}
```

#### 响应示例

```json
{
  "success": true,
  "data": {
    "recommended_index_type": "HNSW",
    "recommended_metric_type": "COSINE",
    "reason": "基于 bge-m3 1024维 + 50000条向量推荐 — 数据量 50000 条（1万~50万），HNSW 图索引兼顾高召回率与低延迟",
    "is_fallback": false,
    "vector_count": 50000,
    "dimension": 1024,
    "embedding_model": "bge-m3"
  }
}
```

### 5.2 记录推荐采纳行为

| 项目 | 说明 |
|------|------|
| 路径 | `POST /vector-index/recommend/log` |
| 描述 | 记录用户对推荐值的采纳/修改行为 |

### 5.3 获取推荐统计

| 项目 | 说明 |
|------|------|
| 路径 | `GET /api/vector-index/recommend/stats?days=30` |
| 描述 | 获取推荐采纳率统计（目标 ≥ 80%） |

---

## 6. 统计信息

### 6.1 获取索引统计

| 项目 | 说明 |
|------|------|
| 路径 | `GET /api/vector-index/indexes/{id}/statistics` |
| 描述 | 获取索引的详细统计信息 |

#### 响应示例

```json
{
  "index_id": 1,
  "index_name": "技术文档索引",
  "vector_count": 50,
  "dimension": 1024,
  "index_type": "MILVUS",
  "algorithm_type": "HNSW",
  "metric_type": "cosine",
  "total_queries": 100,
  "avg_search_time_ms": 12.5,
  "memory_usage_bytes": 204800,
  "created_at": "2026-03-06T10:30:00Z",
  "last_updated": "2026-03-06T11:00:00Z"
}
```

> 说明：当前向量索引模块没有独立的 `/providers` 或 `/algorithms` 查询接口，前端可选数据库和算法由页面内置配置与推荐逻辑共同决定。

---

## 7. 错误码说明

### 7.1 HTTP 状态码

| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 201 | 创建成功 |
| 204 | 删除成功（无响应体） |
| 400 | 请求参数错误 |
| 404 | 索引/Collection 不存在 |
| 500 | 服务器内部错误 |
| 503 | 服务不可用（健康检查失败） |

### 7.2 业务错误码

| 错误码 | 说明 | 处理建议 |
|--------|------|----------|
| VI001 | 索引不存在 | 检查索引ID |
| VI002 | 向量化结果不存在 | 先完成向量化 |
| VI003 | Provider不可用 | 检查数据库连接 |
| VI004 | 维度不匹配 | 确保向量维度一致 |
| VI005 | 索引已存在 | 使用overwrite参数 |
| VI006 | 算法不支持 | 选择支持的算法 |
| VI007 | 索引构建失败 | 检查日志详情 |
| VI008 | 搜索失败 | 检查索引状态 |

### 7.3 错误响应示例

```json
{
  "code": 404,
  "message": "Index not found",
  "detail": {
    "error_code": "VI001",
    "index_id": "idx_notexist"
  }
}
```
