# Quick Start: 文本生成功能

**Feature**: 006-text-generation  
**Date**: 2025-12-26

## 概述

文本生成功能是 RAG 系统的最后一环，将向量检索结果与用户问题结合，调用大语言模型生成高质量回答。

## 前置条件

1. 后端服务已启动 (`python -m uvicorn src.main:app --reload`)
2. 前端服务已启动 (`npm run dev`)
3. 已完成文档加载、分块、向量化与索引构建（若需基于知识库生成）
4. API Key 已配置（与 Embedding 服务相同）

## 快速体验

### 场景 1: 基础 RAG 问答

1. 打开文本生成页面 `/generation`
2. 选择一个或多个知识库 Collection（可选，不选则使用模型自身知识）
3. 输入问题并选择模型（默认 `deepseek-v3.2`）
4. 点击“生成回答”，等待流式输出完成
5. 查看生成的回答、引用来源和 token/耗时信息

### 场景 2: 调整生成参数

1. 在生成配置面板中调整参数：
   - **温度 (Temperature)**: 0.0-2.0，越高越有创意
   - **最大长度 (Max Tokens)**: 1-8192，控制回答长度
2. 选择不同模型对比效果：
   - `deepseek-v3.2`: 685B参数，【文本推荐】，工具使用和代理任务方面性能显著提高
   - `deepseek-v3.1`: 671B参数，【文本推荐】，支持思考与非思考模式

### 场景 3: 查看生成历史

1. 切换到"历史记录"标签
2. 查看过往的生成记录
3. 点击记录查看完整详情
4. 对比不同模型的生成效果
5. 按需删除单条记录或清空全部历史

## API 快速入门

### 流式生成（推荐）

```bash
curl -X POST http://localhost:8000/api/v1/generation/stream \
  -H "Content-Type: application/json" \
  -d '{
    "question": "什么是 RAG？",
    "model": "deepseek-v3.2",
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
curl -X POST http://localhost:8000/api/v1/generation/generate \
  -H "Content-Type: application/json" \
  -d '{
    "question": "什么是 RAG？",
    "model": "deepseek-v3.2",
    "stream": false,
    "context": [...]
  }'
```

### 获取可用模型

```bash
curl http://localhost:8000/api/v1/generation/models
```

### 获取生成历史

```bash
curl "http://localhost:8000/api/v1/generation/history?page=1&page_size=20"
```

### 清空全部历史

```bash
curl -X DELETE http://localhost:8000/api/v1/generation/history/clear
```

## 前端集成示例

### 流式输出处理（当前实现）

```javascript
async function generateStream(question, context) {
  const response = await fetch('/api/v1/generation/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, context, model: 'deepseek-v3.2' })
  })

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let answer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''

    for (const line of lines) {
      if (!line.startsWith('data: ')) continue

      const payload = line.slice(6)
      if (payload === '[DONE]') {
        return answer
      }

      const data = JSON.parse(payload)
      if (data.content) {
        answer += data.content
        // 更新 UI
      }
      if (data.done) {
        console.log('Token usage:', data.token_usage)
        console.log('Processing time:', data.processing_time_ms)
      }
    }
  }

  return answer
}
```

### 结果渲染建议

```javascript
import MarkdownIt from 'markdown-it'
import DOMPurify from 'dompurify'

const md = new MarkdownIt({ html: false, breaks: true })

function renderAnswer(answer) {
  const raw = md.render(answer)
  return DOMPurify.sanitize(raw)
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
// 中止前端流式请求
abortController.abort()

// 或调用取消 API
await fetch(`/api/v1/generation/cancel/${requestId}`, { method: 'POST' })
```

## 下一步

1. 运行 `/speckit.tasks` 生成详细任务列表
2. 按任务顺序实现功能
3. 完成后进行集成测试
