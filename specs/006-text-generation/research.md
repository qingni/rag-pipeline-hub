# Technical Research: 文本生成功能

**Feature**: 006-text-generation  
**Date**: 2025-12-26  
**Status**: Complete

## Research Topics

### 1. 大语言模型 API 调用

**Decision**: 使用 langchain-openai 的 ChatOpenAI 类

**Rationale**:
- 三个目标模型（deepseek-v3、deepseek-r1、kimi-k2-instruct）均支持 OpenAI 兼容 API
- 与现有 EmbeddingService 使用相同的 base_url，保持一致性
- langchain-openai 提供了完善的流式输出支持
- 内置重试机制和错误处理

**Alternatives Considered**:
| 方案 | 优点 | 缺点 | 结论 |
|------|------|------|------|
| 直接使用 openai 库 | 轻量、无额外依赖 | 需要自己实现重试逻辑 | 不选用 |
| langchain-openai | 与项目一致、功能完善 | 依赖较重 | ✅ 选用 |
| httpx 直接调用 | 最大灵活性 | 需要大量封装代码 | 不选用 |

**Implementation Notes**:
```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model="deepseek-v3",
    openai_api_key=api_key,
    openai_api_base=base_url,  # 与 Embedding 相同
    temperature=0.7,
    max_tokens=4096,
    streaming=True
)
```

### 2. 流式输出技术方案

**Decision**: FastAPI StreamingResponse + Server-Sent Events (SSE)

**Rationale**:
- SSE 是单向流式通信的标准方案
- 浏览器原生支持 EventSource API
- FastAPI 原生支持 StreamingResponse
- 比 WebSocket 更简单，适合单向数据流场景

**Alternatives Considered**:
| 方案 | 优点 | 缺点 | 结论 |
|------|------|------|------|
| WebSocket | 双向通信 | 实现复杂，本场景不需要双向 | 不选用 |
| SSE | 简单、标准、原生支持 | 仅支持单向 | ✅ 选用 |
| 轮询 | 兼容性最好 | 延迟高、资源浪费 | 不选用 |

**Implementation Notes**:
```python
# 后端
from fastapi.responses import StreamingResponse

async def generate_stream(request):
    async def event_generator():
        async for chunk in llm.astream(messages):
            yield f"data: {json.dumps({'content': chunk.content})}\n\n"
        yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )

# 前端
const eventSource = new EventSource('/api/generation/stream')
eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data)
    // 追加内容到显示区域
}
```

### 3. 模型配置与参数

**Decision**: 支持三种模型，统一参数接口

**Model Configurations**:

| 模型 | 上下文长度 | 默认温度 | 特点 |
|------|-----------|---------|------|
| deepseek-v3 | 128K | 0.7 | 0324最新版本，稳定可靠 |
| deepseek-r1 | 128K | 0.7 | 支持 Function Calling |
| kimi-k2-instruct | 128K | 0.7 | 1TB参数，代理体验好 |

**Common Parameters**:
- `temperature`: 0.0 - 2.0，默认 0.7
- `max_tokens`: 1 - 4096，默认 4096
- `top_p`: 0.0 - 1.0，默认 1.0（可选）

**Implementation Notes**:
```python
GENERATION_MODELS = {
    "deepseek-v3": {
        "name": "deepseek-v3",
        "context_length": 128000,
        "description": "DeepSeek V3 - 0324最新版本，稳定可靠",
        "default_temperature": 0.7,
        "default_max_tokens": 4096,
    },
    "deepseek-r1": {
        "name": "deepseek-r1",
        "context_length": 128000,
        "description": "DeepSeek R1 - 支持 Function Calling，128K超长上下文",
        "default_temperature": 0.7,
        "default_max_tokens": 4096,
    },
    "kimi-k2-instruct": {
        "name": "kimi-k2-instruct",
        "context_length": 128000,
        "description": "Kimi K2 Instruct - 1TB参数，即插即用",
        "default_temperature": 0.7,
        "default_max_tokens": 4096,
    },
}
```

### 4. Prompt 工程

**Decision**: 使用结构化 Prompt 模板，支持来源引用

**Rationale**:
- 清晰的指令有助于模型生成高质量回答
- 结构化上下文便于模型理解和引用
- 明确的引用格式便于前端解析和展示

**Prompt Template**:
```
你是一个智能问答助手。请基于以下参考资料回答用户的问题。

## 参考资料

{context}

## 用户问题

{question}

## 回答要求

1. 基于参考资料给出准确、详细的回答
2. 如果引用了某段资料，请在回答中标注来源编号，如 [1]、[2]
3. 如果参考资料不足以回答问题，请明确说明
4. 回答应该条理清晰，易于理解
```

**Context Formatting**:
```
[1] {chunk_content_1}
来源：{source_file_1}

[2] {chunk_content_2}
来源：{source_file_2}

...
```

### 5. 错误处理与重试

**Decision**: 参考 EmbeddingService 的重试机制

**Error Types**:
| 错误类型 | 处理方式 | 是否重试 |
|---------|---------|---------|
| RateLimitError | 指数退避重试 | ✅ 是 |
| APITimeoutError | 重试 | ✅ 是 |
| NetworkError | 重试 | ✅ 是 |
| AuthenticationError | 直接失败 | ❌ 否 |
| InvalidRequestError | 直接失败 | ❌ 否 |

**Retry Strategy**:
- 最大重试次数：3
- 初始延迟：1秒
- 最大延迟：32秒
- 退避因子：2

### 6. 生成历史存储

**Decision**: SQLite/PostgreSQL 数据库存储

**Rationale**:
- 与现有搜索历史保持一致
- 支持复杂查询和分页
- 便于后续扩展（如用户关联、标签等）

**Storage Strategy**:
- 最大记录数：100 条
- 超出时自动删除最旧记录
- 支持软删除

## Dependencies

### 后端依赖

```txt
langchain-openai>=0.1.0  # 已有，用于 ChatOpenAI
```

### 前端依赖

无新增依赖，使用原生 EventSource API

## Security Considerations

1. **API Key 保护**: API Key 仅在后端使用，不暴露给前端
2. **输入验证**: 对用户输入进行长度和内容验证
3. **速率限制**: 限制单用户的请求频率
4. **上下文长度检查**: 防止超出模型上下文限制

## Performance Considerations

1. **首字符延迟**: 目标 <3秒，通过流式输出实现
2. **流式传输**: 减少用户等待感知
3. **上下文优化**: 控制检索结果数量，避免上下文过长
4. **连接复用**: 复用 HTTP 连接，减少连接开销

## Conclusion

技术方案已确定，所有 NEEDS CLARIFICATION 已解决。可以进入 Phase 1 设计阶段。
