# Implementation Plan: 文本生成功能

**Branch**: `006-text-generation` | **Date**: 2025-12-26 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/006-text-generation/spec.md`

## Summary

文本生成功能是 RAG 系统的最后一环，基于向量检索结果和用户问题，调用大语言模型生成高质量的回答。

**核心功能**:
- RAG 问答生成：将检索结果作为上下文，结合用户问题生成回答
- 多模型支持：deepseek-v3.2、deepseek-v3.1 两种模型
- 流式输出：实时展示生成内容，提升用户体验
- 参数配置：支持温度、最大输出长度等参数调整
- 生成历史：保存生成记录，支持回顾和对比

**技术方案**:
- 使用 OpenAI 兼容 API 格式调用模型（与 Embedding 服务使用相同的 base_url）
- 采用 Server-Sent Events (SSE) 实现流式输出
- 前端采用与现有模块一致的布局和组件风格

## Technical Context

**Language/Version**: Python 3.11 (后端) + Vue 3 + Vite (前端)  
**Primary Dependencies**: FastAPI 0.104.1, langchain-openai, TDesign Vue Next, Pinia  
**Storage**: SQLite/PostgreSQL (生成历史)  
**Testing**: pytest (后端), Vitest (前端)  
**Target Platform**: Linux/macOS 服务器 + 现代浏览器  
**Project Type**: Web Application (frontend + backend)  
**Performance Goals**: 首字符响应 <3s, 流式延迟 <100ms/字符  
**Constraints**: 上下文长度 ≤128K tokens, 单次生成 ≤4096 tokens  
**Scale/Scope**: 单租户，依赖已有搜索结果

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| **I. 模块化架构** | ✅ PASS | 独立 `generation_service.py`，与 SearchService 解耦 |
| **II. 多提供商支持** | ✅ PASS | 支持 deepseek-v3.2、deepseek-v3.1 两种模型 |
| **III. 结果持久化** | ✅ PASS | 生成历史存储在数据库，JSON 格式配置 |
| **IV. 用户体验优先** | ✅ PASS | Vue3 + TDesign，流式输出，与现有模块一致的布局风格 |
| **V. API标准化** | ✅ PASS | RESTful API + SSE，统一响应格式，OpenAPI 文档 |

**Constitution Gate**: ✅ PASSED

## Project Structure

### Documentation (this feature)

```text
specs/006-text-generation/
├── plan.md              # 本文件 - 实现计划
├── research.md          # Phase 0 - 技术调研
├── data-model.md        # Phase 1 - 数据模型设计
├── quickstart.md        # Phase 1 - 快速开始指南
├── contracts/           # Phase 1 - API 契约
│   └── generation-api.yaml
├── tasks.md             # Phase 2 - 任务分解 (待生成)
└── checklists/
    └── requirements.md  # 需求检查清单 ✅
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── api/
│   │   └── generation.py            # API 路由 (需创建)
│   ├── models/
│   │   └── generation.py            # 数据模型 (需创建)
│   ├── services/
│   │   └── generation_service.py    # 核心服务 (需创建)
│   └── schemas/
│       └── generation.py            # Pydantic schemas (需创建)
└── tests/
    └── test_generation/             # 测试用例 (需创建)

frontend/
├── src/
│   ├── views/
│   │   └── Generation.vue           # 主页面 (需创建)
│   ├── components/
│   │   └── Generation/
│   │       ├── GenerationInput.vue  # 输入区域 (需创建)
│   │       ├── GenerationConfig.vue # 配置面板 (需创建)
│   │       ├── GenerationResult.vue # 结果展示 (需创建)
│   │       ├── GenerationHistory.vue# 历史记录 (需创建)
│   │       └── SourceReference.vue  # 来源引用 (需创建)
│   ├── services/
│   │   └── generationApi.js         # API 服务 (需创建)
│   └── stores/
│       └── generationStore.js       # Pinia Store (需创建)
└── tests/
    └── components/                   # 组件测试 (需创建)
```

**Structure Decision**: Web Application 结构，前后端分离。参考现有 Search 模块的布局模式，后端参考 EmbeddingService 的 API 调用模式。

## Key Design Decisions

### 1. 模型调用方式

**Decision**: 使用 langchain-openai 的 ChatOpenAI 类，与 EmbeddingService 保持一致

**Rationale**: 
- 三个模型均支持 OpenAI 兼容 API 格式
- 复用相同的 base_url 和认证方式
- 降低维护成本

### 2. 流式输出实现

**Decision**: 后端使用 FastAPI StreamingResponse + SSE，前端使用 EventSource

**Implementation Flow**:
```python
GenerationService.generate_stream(request)
  → 构建 Prompt（用户问题 + 检索上下文）
  → ChatOpenAI.stream(messages)
  → yield SSE events
```

### 3. 上下文构建

**Decision**: 将检索结果格式化为结构化上下文

**Prompt Template**:
```
你是一个智能助手。请基于以下参考资料回答用户的问题。

参考资料：
[1] {document_1_content}
来源：{source_1}

[2] {document_2_content}
来源：{source_2}

...

用户问题：{user_question}

请基于参考资料给出准确、详细的回答。如果参考资料不足以回答问题，请明确说明。
```

### 4. 前端组件设计

**Decision**: 采用与 Search 模块一致的布局

**Layout**:
- 顶部：问题输入框 + 生成按钮
- 左侧：配置面板（模型选择、参数配置）
- 右侧上方：生成结果展示区（流式输出）
- 右侧下方：来源引用列表

### 5. 生成历史

**Decision**: 数据库存储，最多保留 100 条

**Auto-cleanup**: 超出限制时自动删除最旧记录

### 6. Constitution Compliance (结果持久化)

**说明**: 关于宪章第 III 条"结果持久化"要求：
- 文本生成结果存储在数据库 `generation_history` 表中
- 数据库记录包含完整的 JSON 结构化数据（context_sources, token_usage 等字段）
- 与 Embedding/Search 模块不同，文本生成是交互式功能，不需要独立的 JSON 文件输出
- 如需导出，可通过 API 获取 JSON 格式的历史记录详情

## Complexity Tracking

> 无宪章违规，无需记录

## Generated Artifacts

| Artifact | Path | Status |
|----------|------|--------|
| research.md | specs/006-text-generation/research.md | ✅ Complete |
| data-model.md | specs/006-text-generation/data-model.md | ✅ Complete |
| generation-api.yaml | specs/006-text-generation/contracts/generation-api.yaml | ✅ Complete |
| quickstart.md | specs/006-text-generation/quickstart.md | ✅ Complete |

## Next Steps

运行 `/speckit.tasks` 生成详细的任务分解。
