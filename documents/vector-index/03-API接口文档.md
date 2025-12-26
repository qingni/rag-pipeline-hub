# API接口文档 - 向量索引模块

**生成日期**: 2025-12-26  
**项目**: RAG Framework - 向量索引模块  
**API版本**: v1  

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
| 基础URL | `http://localhost:8000/api/v1` |
| 协议 | HTTP/HTTPS |
| 数据格式 | JSON |

### 1.2 接口列表

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | /vector-index/create | 创建索引 |
| POST | /vector-index/create-from-embedding | 从向量化结果创建索引 |
| GET | /vector-index/list | 获取索引列表 |
| GET | /vector-index/{id} | 获取索引详情 |
| DELETE | /vector-index/{id} | 删除索引 |
| POST | /vector-index/{id}/vectors | 添加向量 |
| POST | /vector-index/{id}/search | 搜索向量 |
| GET | /vector-index/{id}/statistics | 获取统计信息 |
| GET | /vector-index/providers | 获取可用Provider |
| GET | /vector-index/algorithms | 获取可用算法 |
| GET | /vector-index/check-match | 检查匹配索引 |

---

## 2. 索引创建

### 2.1 从向量化结果创建索引

| 项目 | 说明 |
|------|------|
| 路径 | `POST /vector-index/create-from-embedding` |
| 描述 | 从已完成的向量化结果创建向量索引 |

#### 请求参数

```json
{
  "embedding_result_id": "emb_123456",
  "index_name": "技术文档索引",
  "provider": "milvus",
  "algorithm": "HNSW",
  "metric_type": "cosine",
  "algorithm_params": {
    "M": 16,
    "efConstruction": 256
  },
  "overwrite": false
}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| embedding_result_id | string | 是 | 向量化结果ID |
| index_name | string | 否 | 索引名称，默认使用文档名 |
| provider | string | 是 | 向量数据库类型 |
| algorithm | string | 是 | 索引算法 |
| metric_type | string | 是 | 度量类型 |
| algorithm_params | object | 否 | 算法参数 |
| overwrite | boolean | 否 | 是否覆盖已存在的匹配索引 |

#### 响应示例

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": "idx_789012",
    "index_name": "技术文档索引",
    "embedding_result_id": "emb_123456",
    "document_name": "技术文档.pdf",
    "provider": "milvus",
    "algorithm": "HNSW",
    "metric_type": "cosine",
    "dimension": 1024,
    "vector_count": 50,
    "status": "ready",
    "created_at": "2025-12-26T10:30:00Z"
  }
}
```

### 2.2 直接创建空索引

| 项目 | 说明 |
|------|------|
| 路径 | `POST /vector-index/create` |
| 描述 | 创建一个空的向量索引 |

#### 请求参数

```json
{
  "index_name": "自定义索引",
  "provider": "faiss",
  "algorithm": "FLAT",
  "metric_type": "cosine",
  "dimension": 1024
}
```

#### 响应示例

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": "idx_abc123",
    "index_name": "自定义索引",
    "provider": "faiss",
    "algorithm": "FLAT",
    "metric_type": "cosine",
    "dimension": 1024,
    "vector_count": 0,
    "status": "ready",
    "created_at": "2025-12-26T10:30:00Z"
  }
}
```

---

## 3. 索引管理

### 3.1 获取索引列表

| 项目 | 说明 |
|------|------|
| 路径 | `GET /vector-index/list` |
| 描述 | 获取所有向量索引列表 |

#### 请求参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| page | int | 否 | 1 | 页码 |
| page_size | int | 否 | 20 | 每页数量 |
| provider | string | 否 | - | 按Provider筛选 |
| status | string | 否 | - | 按状态筛选 |

#### 响应示例

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "items": [
      {
        "id": "idx_789012",
        "index_name": "技术文档索引",
        "document_name": "技术文档.pdf",
        "provider": "milvus",
        "algorithm": "HNSW",
        "metric_type": "cosine",
        "dimension": 1024,
        "vector_count": 50,
        "status": "ready",
        "created_at": "2025-12-26T10:30:00Z"
      }
    ],
    "total": 5,
    "page": 1,
    "page_size": 20
  }
}
```

### 3.2 获取索引详情

| 项目 | 说明 |
|------|------|
| 路径 | `GET /vector-index/{id}` |
| 描述 | 获取单个索引的详细信息 |

#### 响应示例

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": "idx_789012",
    "index_name": "技术文档索引",
    "embedding_result_id": "emb_123456",
    "document_id": "doc_abc123",
    "document_name": "技术文档.pdf",
    "provider": "milvus",
    "algorithm": "HNSW",
    "algorithm_params": {
      "M": 16,
      "efConstruction": 256
    },
    "metric_type": "cosine",
    "dimension": 1024,
    "vector_count": 50,
    "status": "ready",
    "index_file": "results/vector_index/idx_789012.faiss",
    "created_at": "2025-12-26T10:30:00Z",
    "updated_at": "2025-12-26T10:30:15Z"
  }
}
```

### 3.3 删除索引

| 项目 | 说明 |
|------|------|
| 路径 | `DELETE /vector-index/{id}` |
| 描述 | 删除指定的向量索引 |

#### 响应示例

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": "idx_789012",
    "deleted": true
  }
}
```

### 3.4 检查匹配索引

| 项目 | 说明 |
|------|------|
| 路径 | `GET /vector-index/check-match` |
| 描述 | 检查是否存在匹配的索引 |

#### 请求参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| embedding_result_id | string | 是 | 向量化结果ID |
| provider | string | 是 | 向量数据库类型 |
| algorithm | string | 是 | 索引算法 |
| metric_type | string | 是 | 度量类型 |

#### 响应示例（存在匹配）

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "matched": true,
    "index": {
      "id": "idx_789012",
      "index_name": "技术文档索引",
      "vector_count": 50,
      "status": "ready",
      "created_at": "2025-12-26T10:30:00Z"
    }
  }
}
```

#### 响应示例（无匹配）

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "matched": false,
    "index": null
  }
}
```

---

## 4. 向量操作

### 4.1 添加向量

| 项目 | 说明 |
|------|------|
| 路径 | `POST /vector-index/{id}/vectors` |
| 描述 | 向索引中添加向量 |

#### 请求参数

```json
{
  "vectors": [
    {
      "id": "vec_001",
      "embedding": [0.123, -0.456, 0.789, ...],
      "text": "文本内容",
      "metadata": {
        "source": "文档.pdf",
        "page": 1
      }
    }
  ]
}
```

#### 响应示例

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "added_count": 10,
    "total_count": 60
  }
}
```

### 4.2 删除向量

| 项目 | 说明 |
|------|------|
| 路径 | `DELETE /vector-index/{id}/vectors` |
| 描述 | 从索引中删除向量 |

#### 请求参数

```json
{
  "vector_ids": ["vec_001", "vec_002"]
}
```

#### 响应示例

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "deleted_count": 2,
    "total_count": 48
  }
}
```

---

## 5. 向量搜索

### 5.1 单向量搜索

| 项目 | 说明 |
|------|------|
| 路径 | `POST /vector-index/{id}/search` |
| 描述 | 在指定索引中搜索相似向量 |

#### 请求参数

```json
{
  "query_vector": [0.123, -0.456, 0.789, ...],
  "top_k": 10,
  "threshold": 0.5,
  "filter": {
    "page": {"$gte": 1, "$lte": 10}
  }
}
```

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| query_vector | float[] | 是 | - | 查询向量 |
| top_k | int | 否 | 10 | 返回数量 |
| threshold | float | 否 | 0 | 相似度阈值 |
| filter | object | 否 | - | 元数据过滤条件 |

#### 响应示例

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "results": [
      {
        "id": "vec_005",
        "score": 0.95,
        "text": "最相似的文本内容...",
        "metadata": {
          "source": "文档.pdf",
          "page": 3
        }
      },
      {
        "id": "vec_012",
        "score": 0.88,
        "text": "第二相似的文本内容...",
        "metadata": {
          "source": "文档.pdf",
          "page": 5
        }
      }
    ],
    "total": 2,
    "search_time_ms": 15
  }
}
```

### 5.2 批量搜索

| 项目 | 说明 |
|------|------|
| 路径 | `POST /vector-index/{id}/batch-search` |
| 描述 | 批量搜索多个查询向量 |

#### 请求参数

```json
{
  "query_vectors": [
    [0.123, -0.456, ...],
    [0.234, -0.567, ...]
  ],
  "top_k": 5,
  "threshold": 0.5
}
```

#### 响应示例

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "results": [
      {
        "query_index": 0,
        "matches": [
          {"id": "vec_005", "score": 0.95, "text": "..."},
          {"id": "vec_012", "score": 0.88, "text": "..."}
        ]
      },
      {
        "query_index": 1,
        "matches": [
          {"id": "vec_008", "score": 0.92, "text": "..."}
        ]
      }
    ],
    "total_queries": 2,
    "search_time_ms": 25
  }
}
```

---

## 6. 统计信息

### 6.1 获取索引统计

| 项目 | 说明 |
|------|------|
| 路径 | `GET /vector-index/{id}/statistics` |
| 描述 | 获取索引的详细统计信息 |

#### 响应示例

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "index_id": "idx_789012",
    "vector_count": 50,
    "dimension": 1024,
    "index_size_bytes": 204800,
    "index_size_human": "200 KB",
    "avg_search_time_ms": 12.5,
    "total_searches": 100,
    "last_search_at": "2025-12-26T11:00:00Z",
    "created_at": "2025-12-26T10:30:00Z"
  }
}
```

### 6.2 获取可用Provider

| 项目 | 说明 |
|------|------|
| 路径 | `GET /vector-index/providers` |
| 描述 | 获取系统支持的向量数据库列表 |

#### 响应示例

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "providers": [
      {
        "name": "milvus",
        "display_name": "Milvus",
        "description": "分布式向量数据库，适合生产环境",
        "available": true,
        "supported_algorithms": ["FLAT", "HNSW", "IVF_FLAT", "IVF_PQ"]
      },
      {
        "name": "faiss",
        "display_name": "FAISS",
        "description": "本地向量索引库，适合开发测试",
        "available": true,
        "supported_algorithms": ["FLAT", "HNSW", "IVF_FLAT", "IVF_PQ"]
      }
    ]
  }
}
```

### 6.3 获取可用算法

| 项目 | 说明 |
|------|------|
| 路径 | `GET /vector-index/algorithms` |
| 描述 | 获取系统支持的索引算法列表 |

#### 响应示例

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "algorithms": [
      {
        "name": "FLAT",
        "display_name": "FLAT (精确搜索)",
        "description": "暴力搜索，精度100%",
        "params": []
      },
      {
        "name": "HNSW",
        "display_name": "HNSW (图索引)",
        "description": "层次可导航小世界图，高性能",
        "params": [
          {"name": "M", "type": "int", "default": 16, "description": "连接数"},
          {"name": "efConstruction", "type": "int", "default": 256, "description": "构建搜索范围"}
        ]
      },
      {
        "name": "IVF_FLAT",
        "display_name": "IVF_FLAT (倒排索引)",
        "description": "倒排索引，平衡精度与速度",
        "params": [
          {"name": "nlist", "type": "int", "default": 100, "description": "聚类数量"}
        ]
      },
      {
        "name": "IVF_PQ",
        "display_name": "IVF_PQ (乘积量化)",
        "description": "向量压缩，节省内存",
        "params": [
          {"name": "nlist", "type": "int", "default": 100, "description": "聚类数量"},
          {"name": "m", "type": "int", "default": 8, "description": "子向量数量"}
        ]
      }
    ]
  }
}
```

---

## 7. 错误码说明

### 7.1 HTTP 状态码

| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 404 | 索引不存在 |
| 409 | 索引已存在（冲突） |
| 500 | 服务器内部错误 |

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
