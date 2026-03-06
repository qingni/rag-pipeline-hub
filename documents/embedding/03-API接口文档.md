# API接口文档 - 文档向量化模块

**生成日期**: 2025-12-26  
**最后更新**: 2026-02-05  
**项目**: RAG Framework - 文档向量化模块

---

## 📋 目录

1. [接口概述](#1-接口概述)
2. [单文本向量化](#2-单文本向量化)
3. [批量文本向量化](#3-批量文本向量化)
4. [分块结果向量化](#4-分块结果向量化)
5. [文档向量化](#5-文档向量化)
6. [获取模型信息](#6-获取模型信息)
7. [获取向量化历史](#7-获取向量化历史)
8. [错误码说明](#8-错误码说明)

---

## 1. 接口概述

### 1.1 基础信息

| 项目 | 说明 |
|------|------|
| 基础URL | `http://localhost:8000/api/v1` |
| 协议 | HTTP/HTTPS |
| 数据格式 | JSON |
| 认证方式 | 暂无（开发环境） |

### 1.2 通用响应格式

```json
{
  "code": 200,
  "message": "success",
  "data": { ... }
}
```

### 1.3 错误响应格式

```json
{
  "code": 400,
  "message": "错误描述",
  "detail": "详细错误信息"
}
```

---

## 2. 单文本向量化

### 2.1 接口信息

| 项目 | 说明 |
|------|------|
| 路径 | `POST /api/v1/embedding/embed` |
| 描述 | 将单个文本转换为向量 |

### 2.2 请求参数

```json
{
  "text": "要向量化的文本内容",
  "model": "bge-m3"
}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| text | string | 是 | 要向量化的文本 |
| model | string | 是 | 模型名称 |

### 2.3 响应示例

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "embedding": [0.123, -0.456, 0.789, ...],
    "dimension": 1024,
    "model": "bge-m3",
    "tokens": 128
  }
}
```

### 2.4 使用示例

```javascript
// JavaScript
const response = await fetch('/api/v1/embedding/embed', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    text: '这是一段测试文本',
    model: 'bge-m3'
  })
});
const result = await response.json();
console.log(result.data.embedding);
```

```python
# Python
import requests

response = requests.post(
    'http://localhost:8000/api/v1/embedding/embed',
    json={
        'text': '这是一段测试文本',
        'model': 'bge-m3'
    }
)
result = response.json()
print(result['data']['embedding'])
```

---

## 3. 批量文本向量化

### 3.1 接口信息

| 项目 | 说明 |
|------|------|
| 路径 | `POST /api/v1/embedding/embed_batch` |
| 描述 | 批量将多个文本转换为向量 |

### 3.2 请求参数

```json
{
  "texts": ["文本1", "文本2", "文本3"],
  "model": "bge-m3"
}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| texts | string[] | 是 | 文本数组，最多1000条 |
| model | string | 是 | 模型名称 |

### 3.3 响应示例

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "embeddings": [
      [0.123, -0.456, ...],
      [0.234, -0.567, ...],
      [0.345, -0.678, ...]
    ],
    "dimension": 1024,
    "model": "bge-m3",
    "total": 3,
    "success": 3,
    "failed": 0,
    "failed_indices": []
  }
}
```

### 3.4 部分成功响应

```json
{
  "code": 200,
  "message": "partial success",
  "data": {
    "embeddings": [
      [0.123, -0.456, ...],
      null,
      [0.345, -0.678, ...]
    ],
    "dimension": 1024,
    "model": "bge-m3",
    "total": 3,
    "success": 2,
    "failed": 1,
    "failed_indices": [1],
    "errors": {
      "1": "Text too long"
    }
  }
}
```

---

## 4. 分块结果向量化

### 4.1 接口信息

| 项目 | 说明 |
|------|------|
| 路径 | `POST /api/v1/embedding/embed_chunking_result` |
| 描述 | 对分块结果进行向量化 |

### 4.2 请求参数

```json
{
  "chunking_result_id": "chunk_123456",
  "model": "bge-m3",
  "batch_size": 100
}
```

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| chunking_result_id | string | 是 | - | 分块结果ID |
| model | string | 是 | - | 模型名称 |
| batch_size | int | 否 | 100 | 批处理大小 |

### 4.3 响应示例

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": "emb_789012",
    "chunking_result_id": "chunk_123456",
    "document_name": "技术文档.pdf",
    "model": "bge-m3",
    "dimension": 1024,
    "total_chunks": 50,
    "success_count": 50,
    "failed_count": 0,
    "status": "completed",
    "result_file": "results/embedding/emb_789012.json",
    "created_at": "2025-12-26T10:30:00Z",
    "completed_at": "2025-12-26T10:30:15Z"
  }
}
```

---

## 5. 文档向量化

### 5.1 接口信息

| 项目 | 说明 |
|------|------|
| 路径 | `POST /api/v1/embedding/embed_document` |
| 描述 | 对文档的最新分块结果进行向量化 |

### 5.2 请求参数

```json
{
  "document_id": "doc_123456",
  "model": "bge-m3"
}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| document_id | string | 是 | 文档ID |
| model | string | 是 | 模型名称 |

### 5.3 响应示例

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": "emb_789012",
    "document_id": "doc_123456",
    "document_name": "技术文档.pdf",
    "chunking_result_id": "chunk_123456",
    "model": "bge-m3",
    "dimension": 1024,
    "total_chunks": 50,
    "success_count": 50,
    "failed_count": 0,
    "status": "completed"
  }
}
```

---

## 6. 获取模型信息

### 6.1 获取可用模型列表

| 项目 | 说明 |
|------|------|
| 路径 | `GET /api/v1/embedding/models` |
| 描述 | 获取所有可用的Embedding模型 |

### 6.2 响应示例

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "models": [
      {
        "name": "bge-m3",
        "display_name": "BGE-M3",
        "dimension": 1024,
        "max_sequence_length": 8192,
        "provider": "bge",
        "model_type": "text",
        "description": "BGE-M3 多语言模型，支持密集检索、多向量检索和稀疏检索"
      },
      {
        "name": "qwen3-embedding-8b",
        "display_name": "Qwen3 Embedding 8B",
        "dimension": 4096,
        "max_sequence_length": 32768,
        "provider": "qwen",
        "model_type": "text",
        "description": "通义千问 Embedding 8B，高精度、长文本支持、动态维度输出"
      },
      {
        "name": "qwen3-vl-embedding-8b",
        "display_name": "Qwen3 VL Embedding 8B",
        "dimension": 4096,
        "min_dimension": 64,
        "max_dimension": 4096,
        "max_sequence_length": 32768,
        "provider": "qwen",
        "model_type": "multimodal",
        "supported_inputs": ["text", "image", "video", "text+image"],
        "description": "通义千问多模态 Embedding 8B，支持文本、图像、视频输入"
      }
    ]
  }
}
```

---

## 7. 获取向量化历史

### 7.1 获取历史列表

| 项目 | 说明 |
|------|------|
| 路径 | `GET /api/v1/embedding/history` |
| 描述 | 获取向量化任务历史记录 |

### 7.2 请求参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| page | int | 否 | 1 | 页码 |
| page_size | int | 否 | 20 | 每页数量 |
| status | string | 否 | - | 状态过滤 |

### 7.3 响应示例

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "items": [
      {
        "id": "emb_789012",
        "document_name": "技术文档.pdf",
        "model": "bge-m3",
        "dimension": 1024,
        "total_chunks": 50,
        "success_count": 50,
        "status": "completed",
        "created_at": "2025-12-26T10:30:00Z"
      }
    ],
    "total": 15,
    "page": 1,
    "page_size": 20,
    "total_pages": 1
  }
}
```

### 7.4 获取单个历史详情

| 项目 | 说明 |
|------|------|
| 路径 | `GET /api/v1/embedding/history/{id}` |
| 描述 | 获取单个向量化任务详情 |

### 7.5 响应示例

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": "emb_789012",
    "document_name": "技术文档.pdf",
    "chunking_result_id": "chunk_123456",
    "model": "bge-m3",
    "dimension": 1024,
    "total_chunks": 50,
    "success_count": 50,
    "failed_count": 0,
    "status": "completed",
    "result_file": "results/embedding/emb_789012.json",
    "created_at": "2025-12-26T10:30:00Z",
    "completed_at": "2025-12-26T10:30:15Z",
    "duration_seconds": 15,
    "chunks_per_second": 3.33
  }
}
```

---

## 8. 错误码说明

### 8.1 HTTP 状态码

| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 401 | 认证失败 |
| 404 | 资源不存在 |
| 429 | 请求过于频繁 |
| 500 | 服务器内部错误 |

### 8.2 业务错误码

| 错误码 | 说明 | 处理建议 |
|--------|------|----------|
| E001 | 模型不存在 | 检查模型名称是否正确 |
| E002 | 文本为空 | 提供有效的文本内容 |
| E003 | 文本过长 | 缩短文本或进行分块 |
| E004 | 分块结果不存在 | 检查分块结果ID |
| E005 | 文档不存在 | 检查文档ID |
| E006 | API调用失败 | 检查API密钥和网络 |
| E007 | 向量化超时 | 减少批量大小或重试 |
| E008 | 部分向量化失败 | 查看失败详情并重试 |

### 8.3 错误响应示例

```json
{
  "code": 400,
  "message": "Invalid model name",
  "detail": {
    "error_code": "E001",
    "model": "unknown-model",
    "available_models": ["bge-m3", "qwen3-embedding-8b", "qwen3-vl-embedding-8b"]
  }
}
```

---

## 9. SDK 使用示例

### 9.1 JavaScript/TypeScript

```typescript
// embeddingApi.ts
import axios from 'axios';

const API_BASE = '/api/v1/embedding';

export const embeddingApi = {
  // 单文本向量化
  async embedText(text: string, model: string) {
    const response = await axios.post(`${API_BASE}/embed`, { text, model });
    return response.data;
  },

  // 批量向量化
  async embedBatch(texts: string[], model: string) {
    const response = await axios.post(`${API_BASE}/embed_batch`, { texts, model });
    return response.data;
  },

  // 分块结果向量化
  async embedChunkingResult(chunkingResultId: string, model: string) {
    const response = await axios.post(`${API_BASE}/embed_chunking_result`, {
      chunking_result_id: chunkingResultId,
      model
    });
    return response.data;
  },

  // 获取模型列表
  async getModels() {
    const response = await axios.get(`${API_BASE}/models`);
    return response.data;
  },

  // 获取历史记录
  async getHistory(page = 1, pageSize = 20) {
    const response = await axios.get(`${API_BASE}/history`, {
      params: { page, page_size: pageSize }
    });
    return response.data;
  }
};
```

### 9.2 Python

```python
# embedding_client.py
import requests
from typing import List, Optional

class EmbeddingClient:
    def __init__(self, base_url: str = "http://localhost:8000/api/v1"):
        self.base_url = base_url
    
    def embed_text(self, text: str, model: str) -> dict:
        """单文本向量化"""
        response = requests.post(
            f"{self.base_url}/embedding/embed",
            json={"text": text, "model": model}
        )
        return response.json()
    
    def embed_batch(self, texts: List[str], model: str) -> dict:
        """批量向量化"""
        response = requests.post(
            f"{self.base_url}/embedding/embed_batch",
            json={"texts": texts, "model": model}
        )
        return response.json()
    
    def embed_chunking_result(
        self, 
        chunking_result_id: str, 
        model: str,
        batch_size: int = 100
    ) -> dict:
        """分块结果向量化"""
        response = requests.post(
            f"{self.base_url}/embedding/embed_chunking_result",
            json={
                "chunking_result_id": chunking_result_id,
                "model": model,
                "batch_size": batch_size
            }
        )
        return response.json()
    
    def get_models(self) -> dict:
        """获取模型列表"""
        response = requests.get(f"{self.base_url}/embedding/models")
        return response.json()

# 使用示例
client = EmbeddingClient()
result = client.embed_text("这是测试文本", "bge-m3")
print(result)
```
