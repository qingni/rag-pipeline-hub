# API接口文档 - 文本生成模块

**生成日期**: 2025-12-26  
**项目**: RAG Framework - 文本生成模块  
**最后更新**: 2026-03-06  
**API版本**: v1  

---

## 📋 目录

1. [接口概述](#1-接口概述)
2. [生成接口](#2-生成接口)
3. [模型接口](#3-模型接口)
4. [历史记录接口](#4-历史记录接口)
5. [错误码说明](#5-错误码说明)
6. [SDK使用示例](#6-sdk使用示例)

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
| POST | /generation/generate | 非流式生成 |
| POST | /generation/stream | 流式生成 (SSE) |
| POST | /generation/cancel/{request_id} | 取消生成 |
| GET | /generation/models | 获取可用模型 |
| GET | /generation/history | 获取历史列表 |
| GET | /generation/history/{id} | 获取历史详情 |
| DELETE | /generation/history/{id} | 删除历史记录 |
| DELETE | /generation/history/clear | 清空历史 |

---

## 2. 生成接口

### 2.1 非流式生成

| 项目 | 说明 |
|------|------|
| 路径 | `POST /generation/generate` |
| 描述 | 生成文本回答（等待完成后返回） |

#### 请求参数

```json
{
  "question": "如何在自选股中添加股票？",
  "model": "deepseek-v3.2",
  "temperature": 0.7,
  "max_tokens": 4096,
  "context": [
    {
      "content": "在股票APP的自选页面中，添加股票到自选列表主要有以下两种方式...",
      "source_file": "技术文档.md",
      "similarity": 0.92
    }
  ],
  "stream": false
}
```

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| question | string | 是 | - | 用户问题，1-10000字符 |
| model | string | 否 | deepseek-v3.2 | 模型名称 |
| temperature | float | 否 | 0.7 | 温度参数，0-2 |
| max_tokens | int | 否 | 4096 | 最大输出长度，1-8192 |
| context | array | 否 | [] | 检索上下文 |
| stream | bool | 否 | false | 是否流式输出；调用 `/stream` 时通常传 `true` |

#### Context Item 结构

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| content | string | 是 | 文档内容 |
| source_file | string | 否 | 来源文件，默认"未知来源" |
| similarity | float | 否 | 相似度分数，默认0.0 |
| chunk_id | string | 否 | Chunk ID |
| metadata | object | 否 | 额外元数据 |

#### 响应示例

```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "answer": "根据参考资料，在自选股中添加股票主要有以下两种方式：\n\n### 1. 通过搜索功能添加 [1]\n- 点击顶部导航栏的搜索栏\n- 输入股票名称或代码进行搜索\n- 在搜索结果中点击"+"按钮添加\n\n### 2. 通过推荐引导弹窗添加 [2]\n- 系统会自动弹出推荐引导弹窗\n- 直接选择感兴趣的股票添加",
  "model": "deepseek-v3.2",
  "token_usage": {
    "prompt_tokens": 856,
    "completion_tokens": 245,
    "total_tokens": 1101
  },
  "processing_time_ms": 3245.67,
  "sources": [
    {
      "index": 1,
      "source_file": "技术文档.md",
      "similarity": 0.92
    }
  ]
}
```

### 2.2 流式生成 (SSE)

| 项目 | 说明 |
|------|------|
| 路径 | `POST /generation/stream` |
| 描述 | 流式生成文本回答 (Server-Sent Events) |

#### 请求参数

与非流式生成相同，`stream` 参数设为 `true`。

#### 响应格式

响应为 SSE (Server-Sent Events) 格式。当前实现采用“后端返回 SSE，前端使用 `fetch + ReadableStream` 逐行解析”的方式消费流，而不是浏览器 `EventSource`。

```
data: {"request_id": "550e8400-e29b-41d4-a716-446655440000", "content": "", "done": false}

data: {"content": "根据", "done": false}

data: {"content": "参考", "done": false}

data: {"content": "资料", "done": false}

...

data: {"content": "", "done": true, "token_usage": {"prompt_tokens": 856, "completion_tokens": 245, "total_tokens": 1101}, "processing_time_ms": 3245.67, "sources": [{"index": 1, "source_file": "技术文档.md", "similarity": 0.92}]}

data: [DONE]
```

#### 流式事件说明

| 事件类型 | 字段 | 说明 |
|---------|------|------|
| 开始 | `request_id` | 首个 chunk 通常携带请求 ID |
| 内容 | `content` | 生成的内容片段 |
| 完成 | `done=true` | 生成完成标志 |
| 统计 | `token_usage` | Token 使用统计，仅最后一块返回 |
| 耗时 | `processing_time_ms` | 处理耗时，仅最后一块返回 |
| 来源 | `sources` | 引用来源，仅最后一块返回 |
| 取消 | `cancelled=true` | 生成被取消时返回 |
| 异常 | `error` | 生成异常时返回错误信息 |
| 结束 | `[DONE]` | 流结束标志 |

#### 前端接入建议

```javascript
const response = await fetch('/api/v1/generation/stream', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    question: '请总结这份文档',
    model: 'deepseek-v3.2',
    stream: true,
    context: []
  })
})

const reader = response.body.getReader()
const decoder = new TextDecoder()
let buffer = ''

while (true) {
  const { done, value } = await reader.read()
  if (done) break

  buffer += decoder.decode(value, { stream: true })
  const lines = buffer.split('\n')
  buffer = lines.pop() || ''

  for (const line of lines) {
    if (!line.startsWith('data: ')) continue
    const payload = line.slice(6)
    if (payload === '[DONE]') return
    const chunk = JSON.parse(payload)
    // 处理 chunk.content / chunk.request_id / chunk.token_usage 等字段
  }
}
```

### 2.3 取消生成

| 项目 | 说明 |
|------|------|
| 路径 | `POST /generation/cancel/{request_id}` |
| 描述 | 取消正在进行的生成请求 |

#### 路径参数

| 参数 | 类型 | 说明 |
|------|------|------|
| request_id | string | 要取消的请求ID |

#### 响应示例

```json
{
  "success": true,
  "message": "Generation cancelled"
}
```

---

## 3. 模型接口

### 3.1 获取可用模型列表

| 项目 | 说明 |
|------|------|
| 路径 | `GET /generation/models` |
| 描述 | 获取所有可用的生成模型 |

#### 响应示例

```json
{
  "models": [
    {
      "name": "deepseek-v3.2",
      "context_length": 128000,
      "description": "DeepSeek V3.2 - 685B参数，【文本推荐】，工具使用和代理任务方面性能显著提高",
      "default_temperature": 0.7,
      "default_max_tokens": 4096
    },
    {
      "name": "deepseek-v3.1",
      "context_length": 128000,
      "description": "DeepSeek V3.1 - 671B参数，【文本推荐】，支持思考与非思考模式",
      "default_temperature": 0.7,
      "default_max_tokens": 4096
    }
  ]
}
```

#### 模型信息字段

| 字段 | 类型 | 说明 |
|------|------|------|
| name | string | 模型名称 |
| context_length | int | 最大上下文长度 |
| description | string | 模型描述 |
| default_temperature | float | 默认温度 |
| default_max_tokens | int | 默认最大输出长度 |

---

## 4. 历史记录接口

### 4.1 获取历史列表

| 项目 | 说明 |
|------|------|
| 路径 | `GET /generation/history` |
| 描述 | 获取生成历史记录列表 |

#### 请求参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| page | int | 否 | 1 | 页码 |
| page_size | int | 否 | 20 | 每页数量，1-100 |
| status | string | 否 | - | 状态筛选 |

#### 响应示例

```json
{
  "items": [
    {
      "id": 1,
      "request_id": "550e8400-e29b-41d4-a716-446655440000",
      "question": "如何在自选股中添加股票？",
      "answer_preview": "根据参考资料，在自选股中添加股票主要有以下两种方式：\n\n### 1. 通过搜索功能添加 [1]\n- 点击顶部导航栏的搜索栏\n- 输入股票名称或代码进行搜索...",
      "model": "deepseek-v3.2",
      "status": "completed",
      "created_at": "2025-12-26T10:30:00Z"
    }
  ],
  "total": 15,
  "page": 1,
  "page_size": 20,
  "total_pages": 1
}
```

### 4.2 获取历史详情

| 项目 | 说明 |
|------|------|
| 路径 | `GET /generation/history/{id}` |
| 描述 | 获取单条历史记录的详细信息 |

#### 响应示例

```json
{
  "id": 1,
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "question": "如何在自选股中添加股票？",
  "answer": "根据参考资料，在自选股中添加股票主要有以下两种方式...",
  "model": "deepseek-v3.2",
  "temperature": 0.7,
  "max_tokens": 4096,
  "context_sources": [
    {
      "content": "在股票APP的自选页面中...",
      "source_file": "技术文档.md",
      "similarity": 0.92,
      "metadata": {
        "source": "技术文档.md"
      }
    }
  ],
  "token_usage": {
    "prompt_tokens": 856,
    "completion_tokens": 245,
    "total_tokens": 1101
  },
  "processing_time_ms": 3245.67,
  "status": "completed",
  "error_message": null,
  "created_at": "2025-12-26T10:30:00Z"
}
```

### 4.3 删除历史记录

| 项目 | 说明 |
|------|------|
| 路径 | `DELETE /generation/history/{id}` |
| 描述 | 软删除指定的历史记录 |

#### 响应示例

```json
{
  "success": true,
  "message": "History deleted"
}
```

### 4.4 清空历史记录

| 项目 | 说明 |
|------|------|
| 路径 | `DELETE /generation/history/clear` |
| 描述 | 清空所有历史记录（软删除） |

#### 响应示例

```json
{
  "success": true,
  "message": "All history cleared"
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

### 5.2 业务错误

| 错误类型 | 说明 | 处理建议 |
|---------|------|----------|
| ModelNotFoundError | 模型不存在 | 检查模型名称是否正确 |
| GenerationError | 生成失败 | 检查上下文长度或重试 |
| GenerationCancelledError | 生成被取消 | 用户主动取消 |

### 5.3 错误响应示例

```json
{
  "detail": "Model 'unknown-model' not found. Available models: ['deepseek-v3.2', 'deepseek-v3.1']"
}
```

---

## 6. SDK使用示例

### 6.1 JavaScript/TypeScript

```javascript
// generationApi.js

const API_BASE = '/api/v1/generation'

/**
 * 非流式生成文本
 */
export async function generateText(request) {
  const response = await fetch(`${API_BASE}/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ...request, stream: false })
  })
  
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.message || '生成失败')
  }
  
  return response.json()
}

/**
 * 流式生成文本
 */
export function generateTextStream(request, onChunk, onError, onComplete) {
  const abortController = new AbortController()
  
  fetch(`${API_BASE}/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ...request, stream: true }),
    signal: abortController.signal
  })
    .then(async (response) => {
      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.message || '生成失败')
      }
      
      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      
      while (true) {
        const { done, value } = await reader.read()
        
        if (done) {
          if (onComplete) onComplete()
          break
        }
        
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6)
            if (data === '[DONE]') {
              if (onComplete) onComplete()
              return
            }
            try {
              const chunk = JSON.parse(data)
              onChunk(chunk)
            } catch (e) {
              console.warn('Failed to parse SSE data:', data)
            }
          }
        }
      }
    })
    .catch((error) => {
      if (error.name === 'AbortError') return
      if (onError) onError(error)
    })
  
  return { abort: () => abortController.abort() }
}

/**
 * 获取可用模型列表
 */
export async function getModels() {
  const response = await fetch(`${API_BASE}/models`)
  if (!response.ok) throw new Error('获取模型列表失败')
  return response.json()
}

/**
 * 获取生成历史列表
 */
export async function getHistoryList(params = {}) {
  const searchParams = new URLSearchParams()
  if (params.page) searchParams.set('page', params.page)
  if (params.page_size) searchParams.set('page_size', params.page_size)
  if (params.status) searchParams.set('status', params.status)
  
  const url = `${API_BASE}/history${searchParams.toString() ? '?' + searchParams.toString() : ''}`
  const response = await fetch(url)
  if (!response.ok) throw new Error('获取历史列表失败')
  return response.json()
}

export async function clearHistory() {
  const response = await fetch(`${API_BASE}/history/clear`, {
    method: 'DELETE'
  })
  if (!response.ok) throw new Error('清空失败')
  return response.json()
}
```

### 6.2 Python

```python
# generation_client.py
import requests
import json
from typing import List, Optional, Dict, Any, Callable
from dataclasses import dataclass

@dataclass
class ContextItem:
    content: str
    source_file: str = "未知来源"
    similarity: float = 0.0
    chunk_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class GenerationClient:
    def __init__(self, base_url: str = "http://localhost:8000/api/v1"):
        self.base_url = base_url
    
    def generate(
        self,
        question: str,
        model: str = "deepseek-v3.2",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        context: Optional[List[ContextItem]] = None
    ) -> Dict[str, Any]:
        """非流式生成"""
        response = requests.post(
            f"{self.base_url}/generation/generate",
            json={
                "question": question,
                "model": model,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "context": [vars(c) for c in (context or [])],
                "stream": False
            }
        )
        response.raise_for_status()
        return response.json()
    
    def generate_stream(
        self,
        question: str,
        on_chunk: Callable[[Dict], None],
        model: str = "deepseek-v3.2",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        context: Optional[List[ContextItem]] = None
    ):
        """流式生成"""
        response = requests.post(
            f"{self.base_url}/generation/stream",
            json={
                "question": question,
                "model": model,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "context": [vars(c) for c in (context or [])],
                "stream": True
            },
            stream=True
        )
        response.raise_for_status()
        
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line.startswith('data: '):
                    data = line[6:]
                    if data == '[DONE]':
                        break
                    try:
                        chunk = json.loads(data)
                        on_chunk(chunk)
                    except json.JSONDecodeError:
                        pass
    
    def get_models(self) -> List[Dict]:
        """获取可用模型列表"""
        response = requests.get(f"{self.base_url}/generation/models")
        response.raise_for_status()
        return response.json()["models"]
    
    def get_history(self, page: int = 1, page_size: int = 20) -> Dict:
        """获取历史列表"""
        response = requests.get(
            f"{self.base_url}/generation/history",
            params={"page": page, "page_size": page_size}
        )
        response.raise_for_status()
        return response.json()

# 使用示例
if __name__ == "__main__":
    client = GenerationClient()
    
    # 非流式生成
    result = client.generate(
        question="如何在自选股中添加股票？",
        context=[
            ContextItem(
                content="在股票APP的自选页面中，添加股票到自选列表主要有以下两种方式...",
                source_file="技术文档.md",
                similarity=0.92
            )
        ]
    )
    print(result["answer"])
    
    # 流式生成
    def on_chunk(chunk):
        if chunk.get("content"):
            print(chunk["content"], end="", flush=True)
    
    client.generate_stream(
        question="如何在自选股中添加股票？",
        on_chunk=on_chunk
    )
```
