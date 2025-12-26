# API接口文档 - 搜索查询模块

**生成日期**: 2025-12-26  
**项目**: RAG Framework - 搜索查询模块  
**API版本**: v1  

---

## 📋 目录

1. [接口概述](#1-接口概述)
2. [搜索执行](#2-搜索执行)
3. [索引管理](#3-索引管理)
4. [历史记录](#4-历史记录)
5. [错误码说明](#5-错误码说明)

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
| POST | /search | 执行语义搜索 |
| GET | /search/indexes | 获取可用索引列表 |
| GET | /search/history | 获取搜索历史 |
| GET | /search/history/{id} | 获取历史详情 |
| DELETE | /search/history/{id} | 删除单条历史 |
| DELETE | /search/history | 清空所有历史 |

---

## 2. 搜索执行

### 2.1 执行语义搜索

| 项目 | 说明 |
|------|------|
| 路径 | `POST /search` |
| 描述 | 在指定索引中执行语义搜索 |

#### 请求参数

```json
{
  "query": "如何实现用户认证功能",
  "index_ids": ["idx_abc123", "idx_def456"],
  "top_k": 10,
  "threshold": 0.5,
  "metric_type": "cosine"
}
```

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| query | string | 是 | - | 查询文本，最大2000字符 |
| index_ids | string[] | 否 | [] | 目标索引ID列表，空则搜索所有 |
| top_k | int | 否 | 10 | 返回结果数量，范围1-100 |
| threshold | float | 否 | 0.5 | 相似度阈值，范围0-1 |
| metric_type | string | 否 | cosine | 度量类型（仅用于记录） |

#### 响应示例

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "query": "如何实现用户认证功能",
    "results": [
      {
        "id": "vec_001",
        "score": 0.92,
        "score_percent": "92%",
        "text": "用户认证功能可以通过JWT令牌实现。首先，用户提交用户名和密码...",
        "index_id": "idx_abc123",
        "index_name": "技术文档索引",
        "metadata": {
          "source": "技术文档.pdf",
          "page": 15,
          "chunk_index": 42
        }
      },
      {
        "id": "vec_015",
        "score": 0.87,
        "score_percent": "87%",
        "text": "OAuth2.0是一种常用的用户授权协议，可以用于实现第三方登录...",
        "index_id": "idx_abc123",
        "index_name": "技术文档索引",
        "metadata": {
          "source": "技术文档.pdf",
          "page": 18,
          "chunk_index": 51
        }
      }
    ],
    "total": 2,
    "search_time_ms": 45,
    "indexes_searched": 1,
    "history_id": "hist_xyz789"
  }
}
```

#### 响应字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| query | string | 原始查询文本 |
| results | array | 搜索结果列表 |
| results[].id | string | 向量ID |
| results[].score | float | 相似度分数(0-1) |
| results[].score_percent | string | 相似度百分比 |
| results[].text | string | 匹配的文本内容 |
| results[].index_id | string | 来源索引ID |
| results[].index_name | string | 来源索引名称 |
| results[].metadata | object | 文本元数据 |
| total | int | 结果总数 |
| search_time_ms | float | 搜索耗时(毫秒) |
| indexes_searched | int | 搜索的索引数量 |
| history_id | string | 历史记录ID |

#### 使用示例

```javascript
// JavaScript
const response = await fetch('/api/v1/search', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    query: '如何实现用户认证功能',
    index_ids: ['idx_abc123'],
    top_k: 10,
    threshold: 0.5
  })
});
const result = await response.json();
console.log(result.data.results);
```

```python
# Python
import requests

response = requests.post(
    'http://localhost:8000/api/v1/search',
    json={
        'query': '如何实现用户认证功能',
        'index_ids': ['idx_abc123'],
        'top_k': 10,
        'threshold': 0.5
    }
)
result = response.json()
for item in result['data']['results']:
    print(f"[{item['score_percent']}] {item['text'][:100]}...")
```

---

## 3. 索引管理

### 3.1 获取可用索引列表

| 项目 | 说明 |
|------|------|
| 路径 | `GET /search/indexes` |
| 描述 | 获取所有可用于搜索的索引 |

#### 响应示例

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "indexes": [
      {
        "id": "idx_abc123",
        "name": "技术文档索引",
        "provider": "milvus",
        "vector_count": 150,
        "dimension": 1024,
        "metric_type": "cosine",
        "created_at": "2025-12-26T10:30:00Z"
      },
      {
        "id": "idx_def456",
        "name": "产品手册索引",
        "provider": "faiss",
        "vector_count": 80,
        "dimension": 1024,
        "metric_type": "cosine",
        "created_at": "2025-12-26T11:00:00Z"
      }
    ],
    "total": 2
  }
}
```

#### 响应字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | 索引ID |
| name | string | 索引名称 |
| provider | string | 向量数据库类型 |
| vector_count | int | 向量数量 |
| dimension | int | 向量维度 |
| metric_type | string | 度量类型 |
| created_at | string | 创建时间 |

---

## 4. 历史记录

### 4.1 获取搜索历史列表

| 项目 | 说明 |
|------|------|
| 路径 | `GET /search/history` |
| 描述 | 获取搜索历史记录列表 |

#### 请求参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| page | int | 否 | 1 | 页码 |
| page_size | int | 否 | 20 | 每页数量 |
| limit | int | 否 | 50 | 最大返回数量 |

#### 响应示例

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "items": [
      {
        "id": "hist_xyz789",
        "query": "如何实现用户认证功能",
        "result_count": 5,
        "search_time_ms": 45,
        "config": {
          "index_ids": ["idx_abc123"],
          "top_k": 10,
          "threshold": 0.5,
          "metric_type": "cosine"
        },
        "created_at": "2025-12-26T12:00:00Z"
      },
      {
        "id": "hist_abc456",
        "query": "数据库连接池配置",
        "result_count": 3,
        "search_time_ms": 38,
        "config": {
          "index_ids": [],
          "top_k": 10,
          "threshold": 0.5,
          "metric_type": "cosine"
        },
        "created_at": "2025-12-26T11:30:00Z"
      }
    ],
    "total": 15,
    "page": 1,
    "page_size": 20
  }
}
```

### 4.2 获取历史详情

| 项目 | 说明 |
|------|------|
| 路径 | `GET /search/history/{id}` |
| 描述 | 获取单条搜索历史的详细信息 |

#### 响应示例

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": "hist_xyz789",
    "query": "如何实现用户认证功能",
    "result_count": 5,
    "search_time_ms": 45,
    "config": {
      "index_ids": ["idx_abc123"],
      "top_k": 10,
      "threshold": 0.5,
      "metric_type": "cosine"
    },
    "results": [
      {
        "id": "vec_001",
        "score": 0.92,
        "text": "用户认证功能可以通过JWT令牌实现...",
        "index_name": "技术文档索引"
      }
    ],
    "created_at": "2025-12-26T12:00:00Z"
  }
}
```

### 4.3 删除单条历史

| 项目 | 说明 |
|------|------|
| 路径 | `DELETE /search/history/{id}` |
| 描述 | 删除指定的搜索历史记录 |

#### 响应示例

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": "hist_xyz789",
    "deleted": true
  }
}
```

### 4.4 清空所有历史

| 项目 | 说明 |
|------|------|
| 路径 | `DELETE /search/history` |
| 描述 | 清空所有搜索历史记录 |

#### 响应示例

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "deleted_count": 15
  }
}
```

---

## 5. 错误码说明

### 5.1 HTTP 状态码

| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

### 5.2 业务错误码

| 错误码 | 说明 | 处理建议 |
|--------|------|----------|
| S001 | 查询文本为空 | 提供有效的查询文本 |
| S002 | 查询文本过长 | 缩短查询文本至2000字符以内 |
| S003 | 索引不存在 | 检查索引ID是否正确 |
| S004 | 索引不可用 | 等待索引就绪或选择其他索引 |
| S005 | 向量化失败 | 检查Embedding服务状态 |
| S006 | 搜索超时 | 减少搜索范围或重试 |
| S007 | 历史记录不存在 | 检查历史记录ID |
| S008 | Top-K超出范围 | 设置1-100之间的值 |
| S009 | 阈值超出范围 | 设置0-1之间的值 |

### 5.3 错误响应示例

```json
{
  "code": 400,
  "message": "Query text is empty",
  "detail": {
    "error_code": "S001",
    "field": "query"
  }
}
```

---

## 6. SDK 使用示例

### 6.1 JavaScript/TypeScript

```typescript
// searchApi.ts
import axios from 'axios';

const API_BASE = '/api/v1/search';

export interface SearchRequest {
  query: string;
  index_ids?: string[];
  top_k?: number;
  threshold?: number;
  metric_type?: string;
}

export interface SearchResult {
  id: string;
  score: number;
  score_percent: string;
  text: string;
  index_id: string;
  index_name: string;
  metadata: Record<string, any>;
}

export interface SearchResponse {
  query: string;
  results: SearchResult[];
  total: number;
  search_time_ms: number;
  indexes_searched: number;
  history_id: string;
}

export const searchApi = {
  // 执行搜索
  async search(request: SearchRequest): Promise<SearchResponse> {
    const response = await axios.post(API_BASE, request);
    return response.data.data;
  },

  // 获取可用索引
  async getIndexes() {
    const response = await axios.get(`${API_BASE}/indexes`);
    return response.data.data.indexes;
  },

  // 获取搜索历史
  async getHistory(page = 1, pageSize = 20) {
    const response = await axios.get(`${API_BASE}/history`, {
      params: { page, page_size: pageSize }
    });
    return response.data.data;
  },

  // 删除历史记录
  async deleteHistory(id: string) {
    const response = await axios.delete(`${API_BASE}/history/${id}`);
    return response.data.data;
  },

  // 清空历史
  async clearHistory() {
    const response = await axios.delete(`${API_BASE}/history`);
    return response.data.data;
  }
};
```

### 6.2 Python

```python
# search_client.py
import requests
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

@dataclass
class SearchResult:
    id: str
    score: float
    score_percent: str
    text: str
    index_id: str
    index_name: str
    metadata: Dict[str, Any]

class SearchClient:
    def __init__(self, base_url: str = "http://localhost:8000/api/v1"):
        self.base_url = base_url
    
    def search(
        self,
        query: str,
        index_ids: Optional[List[str]] = None,
        top_k: int = 10,
        threshold: float = 0.5
    ) -> Dict[str, Any]:
        """执行语义搜索"""
        response = requests.post(
            f"{self.base_url}/search",
            json={
                "query": query,
                "index_ids": index_ids or [],
                "top_k": top_k,
                "threshold": threshold
            }
        )
        return response.json()["data"]
    
    def get_indexes(self) -> List[Dict]:
        """获取可用索引列表"""
        response = requests.get(f"{self.base_url}/search/indexes")
        return response.json()["data"]["indexes"]
    
    def get_history(self, page: int = 1, page_size: int = 20) -> Dict:
        """获取搜索历史"""
        response = requests.get(
            f"{self.base_url}/search/history",
            params={"page": page, "page_size": page_size}
        )
        return response.json()["data"]
    
    def delete_history(self, history_id: str) -> bool:
        """删除单条历史"""
        response = requests.delete(f"{self.base_url}/search/history/{history_id}")
        return response.json()["data"]["deleted"]
    
    def clear_history(self) -> int:
        """清空所有历史"""
        response = requests.delete(f"{self.base_url}/search/history")
        return response.json()["data"]["deleted_count"]

# 使用示例
if __name__ == "__main__":
    client = SearchClient()
    
    # 执行搜索
    result = client.search(
        query="如何实现用户认证功能",
        top_k=5,
        threshold=0.5
    )
    
    print(f"找到 {result['total']} 个结果，耗时 {result['search_time_ms']}ms")
    for item in result["results"]:
        print(f"[{item['score_percent']}] {item['text'][:50]}...")
```
