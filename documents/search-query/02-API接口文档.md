# API接口文档 - 检索查询模块

**生成日期**: 2026-02-26  
**最后更新**: 2026-02-26  
**项目**: RAG Framework - 检索查询模块  
**API版本**: v2  

---

## 📋 目录

1. [接口概述](#1-接口概述)
2. [向量搜索](#2-向量搜索)
3. [混合检索](#3-混合检索)
4. [多 Collection 联合搜索](#4-多-collection-联合搜索)
5. [Reranker 服务](#5-reranker-服务)
6. [错误码说明](#6-错误码说明)

---

## 1. 接口概述

### 1.1 基础信息

| 项目 | 说明 |
|------|------|
| 基础URL | `http://localhost:8000/api/v1` |
| 协议 | HTTP/HTTPS |
| 数据格式 | JSON |

### 1.2 接口列表

| 方法 | 路径 | 描述 | 分类 |
|------|------|------|------|
| POST | /vector-index/indexes/{id}/search | 向量搜索 | Search |
| POST | /vector-index/indexes/{id}/batch-search | 批量搜索 | Search |
| POST | /vector-index/hybrid-search | 混合检索 | Search |
| POST | /vector-index/multi-search | 多 Collection 联合搜索 | Search |
| GET | /vector-index/reranker/health | Reranker 健康检查 | Search |

---

## 2. 向量搜索

### 2.1 单次向量搜索

| 项目 | 说明 |
|------|------|
| 路径 | `POST /vector-index/indexes/{id}/search` |
| 描述 | 在指定索引中执行向量相似度搜索 |

#### 请求参数

```json
{
  "query_vector": [0.123, -0.456, 0.789, ...],
  "top_k": 10,
  "threshold": 0.5,
  "filters": {
    "doc_id": "doc_abc123"
  }
}
```

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| query_vector | float[] | 是 | - | 查询向量 |
| top_k | int | 否 | 10 | 返回结果数量 |
| threshold | float | 否 | null | 相似度阈值过滤 |
| filters | object | 否 | null | 元数据过滤条件 |

#### 响应示例

```json
{
  "success": true,
  "data": {
    "results": [
      {
        "vector_id": "vec_001",
        "score": 0.95,
        "metadata": {
          "doc_id": "doc_abc123",
          "chunk_index": 3,
          "text": "RAG系统的核心架构..."
        }
      }
    ],
    "total": 10,
    "search_time_ms": 5.2
  }
}
```

### 2.2 批量搜索

| 项目 | 说明 |
|------|------|
| 路径 | `POST /vector-index/indexes/{id}/batch-search` |
| 描述 | 批量向量搜索，一次提交多个查询向量 |

#### 请求参数

```json
{
  "query_vectors": [
    [0.123, -0.456, ...],
    [0.789, -0.321, ...]
  ],
  "top_k": 5,
  "threshold": 0.6
}
```

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| query_vectors | float[][] | 是 | - | 查询向量数组 |
| top_k | int | 否 | 10 | 每个查询返回结果数量 |
| threshold | float | 否 | null | 相似度阈值过滤 |

#### 响应示例

```json
{
  "success": true,
  "data": {
    "batch_results": [
      {
        "query_index": 0,
        "results": [...],
        "search_time_ms": 3.1
      },
      {
        "query_index": 1,
        "results": [...],
        "search_time_ms": 2.8
      }
    ],
    "total_time_ms": 6.5
  }
}
```

---

## 3. 混合检索

### 3.1 混合检索

| 项目 | 说明 |
|------|------|
| 路径 | `POST /vector-index/hybrid-search` |
| 描述 | 稠密+稀疏双路召回 → RRF 粗排 → Reranker 精排 |

#### 请求参数

```json
{
  "collection_name": "idx_技术文档_20260226",
  "query_text": "RAG 系统的核心架构",
  "query_dense_vector": [0.123, -0.456, ...],
  "query_sparse_vector": null,
  "top_n": 20,
  "top_k": 5,
  "enable_reranker": true,
  "rrf_k": 60,
  "output_fields": ["doc_id", "chunk_index", "metadata"]
}
```

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| collection_name | string | 是 | - | 目标 Collection 名称 |
| query_text | string | 是 | - | 原始查询文本（用于 Reranker 和 BM25） |
| query_dense_vector | float[] | 是 | - | 稠密查询向量 |
| query_sparse_vector | object | 否 | null | 稀疏查询向量（不传则 BM25 自动生成） |
| top_n | int | 否 | 20 | 粗排候选集大小 |
| top_k | int | 否 | 5 | 最终返回结果数量 |
| enable_reranker | boolean | 否 | true | 是否启用 Reranker 精排 |
| rrf_k | int | 否 | 60 | RRF 排名平滑因子 |
| output_fields | string[] | 否 | [] | 需要返回的额外字段 |

#### 响应示例

```json
{
  "success": true,
  "data": [
    {
      "vector_id": 12345,
      "rrf_score": 0.85,
      "reranker_score": 0.92,
      "final_score": 0.92,
      "doc_id": "doc_abc",
      "chunk_index": 3,
      "text": "RAG系统的核心架构包括...",
      "metadata": {"source": "技术文档.pdf", "page": 5},
      "search_mode": "hybrid"
    }
  ],
  "search_mode": "hybrid",
  "query_time_ms": 125.5,
  "rrf_time_ms": 80.2,
  "reranker_time_ms": 45.3,
  "total_candidates": 20,
  "reranker_available": true
}
```

### 3.2 检索模式说明

| 模式 | 条件 | 说明 |
|------|------|------|
| hybrid | 稠密+稀疏向量均可用 | 双路召回 + RRF 融合 |
| dense_only | 稀疏向量不可用 | 仅稠密向量检索 |

### 3.3 降级行为

| 阶段 | 降级条件 | 降级行为 |
|------|---------|---------|
| 稀疏向量 | BM25 统计数据不存在 / 稀疏向量为空 | 自动切换到 dense_only 模式 |
| 稀疏向量 | Collection 无 sparse_embedding 字段 | 自动切换到 dense_only 模式 |
| Reranker | Reranker 服务不可用 | 跳过精排，直接返回 RRF 粗排结果 |

---

## 4. 多 Collection 联合搜索

### 4.1 联合搜索

| 项目 | 说明 |
|------|------|
| 路径 | `POST /vector-index/multi-search` |
| 描述 | 在多个 Collection 中同时搜索，合并结果 |

#### 请求参数

```json
{
  "collection_names": ["idx_文档A", "idx_文档B"],
  "query_vector": [0.123, -0.456, ...],
  "top_k": 10,
  "threshold": 0.5,
  "merge_strategy": "score"
}
```

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| collection_names | string[] | 是 | - | Collection 名称列表 |
| query_vector | float[] | 是 | - | 查询向量 |
| top_k | int | 否 | 10 | 返回数量 |
| threshold | float | 否 | null | 相似度阈值 |
| merge_strategy | string | 否 | score | 合并策略: score/round_robin |

#### 合并策略说明

| 策略 | 说明 | 适用场景 |
|------|------|---------|
| score | 按相似度分数全局排序取 Top-K | 关注最相关结果 |
| round_robin | 轮询从各 Collection 交替选取 | 均衡各知识库覆盖 |

#### 响应示例

```json
{
  "success": true,
  "data": {
    "results": [
      {
        "vector_id": "vec_001",
        "score": 0.95,
        "collection_name": "idx_文档A",
        "metadata": {...}
      }
    ],
    "total": 10,
    "collections_searched": 2,
    "merge_strategy": "score",
    "search_time_ms": 15.3
  }
}
```

---

## 5. Reranker 服务

### 5.1 Reranker 健康检查

| 项目 | 说明 |
|------|------|
| 路径 | `GET /vector-index/reranker/health` |
| 描述 | 检查 Reranker 精排服务是否可用 |

#### 响应示例

```json
{
  "available": true,
  "model": "qwen3-reranker-4b",
  "latency_ms": 12.5
}
```

---

## 6. 错误码说明

### 6.1 检索相关错误码

| 错误码 | 说明 | 处理建议 |
|--------|------|----------|
| VI004 | 维度不匹配 | 确保查询向量维度与索引维度一致 |
| VI008 | 搜索失败 | 检查索引状态是否为 READY |
| VI009 | Collection 不存在 | 检查 Collection 名称 |
| VI010 | Reranker 不可用 | 检查 Reranker 服务状态 |

### 6.2 错误响应示例

```json
{
  "code": 400,
  "message": "Dimension mismatch",
  "detail": {
    "error_code": "VI004",
    "expected_dimension": 1024,
    "actual_dimension": 768
  }
}
```
