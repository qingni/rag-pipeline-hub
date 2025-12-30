# Quick Start: 文本生成功能

**Feature**: 006-text-generation  
**Date**: 2025-12-26

## 概述

文本生成功能是 RAG 系统的最后一环，将向量检索结果与用户问题结合，调用大语言模型生成高质量回答。

## 前置条件

1. 后端服务已启动 (`python -m uvicorn src.main:app --reload`)
2. 前端服务已启动 (`npm run dev`)
3. 已完成向量检索，有可用的检索结果
4. API Key 已配置（与 Embedding 服务相同）

## 快速体验

### 场景 1: 基础 RAG 问答

1. 在搜索页面完成向量检索
2. 点击"生成回答"按钮
3. 选择模型（默认 deepseek-v3）
4. 等待流式输出完成
5. 查看生成的回答和引用来源

### 场景 2: 调整生成参数

1. 在生成配置面板中调整参数：
   - **温度 (Temperature)**: 0.0-2.0，越高越有创意
   - **最大长度 (Max Tokens)**: 1-8192，控制回答长度
2. 选择不同模型对比效果：
   - `deepseek-v3`: 稳定可靠，适合通用场景
   - `deepseek-r1`: 支持 Function Calling
   - `kimi-k2-instruct`: 1TB 参数，代理体验好

### 场景 3: 查看生成历史

1. 切换到"历史记录"标签
2. 查看过往的生成记录
3. 点击记录查看完整详情
4. 对比不同模型的生成效果

## API 快速入门

### 流式生成（推荐）

```bash
curl -X POST http://localhost:8000/api/generation/stream \
  -H "Content-Type: application/json" \
  -d '{
    "question": "什么是 RAG？",
    "model": "deepseek-v3",
    "temperature": 0.7,
    "context": [
      {
        "content": "RAG（检索增强生成）是一种结合检索和生成的技术...",
        "source_file": "rag-intro.pdf",
        "similarity": 0.92
      }
    ]
  }'
```

### 非流式生成

```bash
curl -X POST http://localhost:8000/api/generation/generate \
  -H "Content-Type: application/json" \
  -d '{
    "question": "什么是 RAG？",
    "model": "deepseek-v3",
    "stream": false,
    "context": [...]
  }'
```

### 获取可用模型

```bash
curl http://localhost:8000/api/generation/models
```

### 获取生成历史

```bash
curl "http://localhost:8000/api/generation/history?page=1&page_size=20"
```

## 前端集成示例

### 流式输出处理

```javascript
// 使用 EventSource 处理 SSE
const eventSource = new EventSource('/api/generation/stream', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    question: '什么是 RAG？',
    model: 'deepseek-v3',
    context: searchResults
  })
})

let answer = ''
eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data)
  if (data.done) {
    eventSource.close()
    console.log('Token usage:', data.token_usage)
  } else {
    answer += data.content
    // 更新 UI
  }
}

eventSource.onerror = (error) => {
  console.error('Generation error:', error)
  eventSource.close()
}
```

### 使用 fetch 处理流式响应

```javascript
async function generateStream(question, context) {
  const response = await fetch('/api/generation/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, context, model: 'deepseek-v3' })
  })

  const reader = response.body.getReader()
  const decoder = new TextDecoder()

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    
    const chunk = decoder.decode(value)
    // 解析 SSE 格式
    const lines = chunk.split('\n')
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = JSON.parse(line.slice(6))
        if (!data.done) {
          // 更新 UI
          appendContent(data.content)
        }
      }
    }
  }
}
```

## 常见问题

### Q: 生成速度慢怎么办？

A: 
1. 检查网络连接
2. 减少上下文数量（Top K 设小一些）
3. 降低 max_tokens 参数
4. 尝试不同模型

### Q: 生成结果不准确？

A:
1. 确保检索结果相关性高
2. 优化问题表述，更具体
3. 调低温度参数（如 0.3）
4. 增加检索结果数量

### Q: 如何取消正在进行的生成？

A:
```javascript
// 关闭 EventSource 连接
eventSource.close()

// 或调用取消 API
await fetch(`/api/generation/cancel/${requestId}`, { method: 'POST' })
```

## 下一步

1. 运行 `/speckit.tasks` 生成详细任务列表
2. 按任务顺序实现功能
3. 完成后进行集成测试
