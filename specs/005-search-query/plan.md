# Implementation Plan: 搜索查询功能

**Branch**: `005-search-query` | **Date**: 2025-12-25 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/005-search-query/spec.md`

## Summary

搜索查询功能实现 RAG 系统的核心检索能力，允许用户通过自然语言查询在已构建的向量索引中检索相关文档。

**核心功能**:
- 语义搜索：将查询文本向量化，通过相似度检索返回相关文档片段
- 结果展示：卡片列表形式展示，包含摘要、相似度分数、来源信息
- 搜索配置：支持 TopK、相似度阈值、相似度方法、目标索引选择
- 历史记录：记录搜索历史，支持快速重复查询
- 多索引搜索：支持跨多个索引的联合检索

**技术方案**:
- 复用 Embedding 服务 (003) 进行查询向量化
- 调用 VectorIndexService (004) 执行相似度检索
- 前端采用与现有模块一致的布局和组件风格

## Technical Context

**Language/Version**: Python 3.11 (后端) + Vue 3 + Vite (前端)  
**Primary Dependencies**: FastAPI 0.104.1, pymilvus 2.3.4, faiss-cpu 1.7.4, TDesign Vue Next, Pinia  
**Storage**: SQLite/PostgreSQL (搜索历史) + Milvus/FAISS (向量检索)  
**Testing**: pytest (后端), Vitest (前端)  
**Target Platform**: Linux/macOS 服务器 + 现代浏览器  
**Project Type**: Web Application (frontend + backend)  
**Performance Goals**: 端到端响应 <3s (P95), 20 并发, 10 QPS  
**Constraints**: 查询文本 ≤2000 字符, 历史记录 ≤50 条  
**Scale/Scope**: 单租户，依赖已有向量索引

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| **I. 模块化架构** | ✅ PASS | 独立 `search_service.py`，复用 Embedding 和 VectorIndex 服务 |
| **II. 多提供商支持** | ✅ PASS | 通过 VectorIndexService 支持 Milvus + FAISS |
| **III. 结果持久化** | ✅ PASS | 搜索历史存储在数据库，JSON 格式配置 |
| **IV. 用户体验优先** | ✅ PASS | Vue3 + TDesign，与现有模块一致的布局风格 |
| **V. API标准化** | ✅ PASS | RESTful API，统一响应格式，OpenAPI 文档 |

**Constitution Gate**: ✅ PASSED

## Project Structure

### Documentation (this feature)

```text
specs/005-search-query/
├── plan.md              # 本文件 - 实现计划
├── research.md          # Phase 0 - 技术调研 ✅
├── data-model.md        # Phase 1 - 数据模型设计 ✅
├── quickstart.md        # Phase 1 - 快速开始指南 ✅
├── contracts/           # Phase 1 - API 契约 ✅
│   └── search-api.yaml
├── tasks.md             # Phase 2 - 任务分解 (待生成)
└── checklists/
    └── requirements.md  # 需求检查清单 ✅
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── api/
│   │   └── search.py                # API 路由 (需创建)
│   ├── models/
│   │   └── search.py                # 数据模型 (需创建)
│   ├── services/
│   │   └── search_service.py        # 核心服务 (需创建)
│   └── schemas/
│       └── search.py                # Pydantic schemas (需创建)
└── tests/
    └── test_search/                 # 测试用例 (需创建)

frontend/
├── src/
│   ├── views/
│   │   └── Search.vue               # 主页面 (需创建)
│   ├── components/
│   │   └── Search/
│   │       ├── SearchInput.vue      # 搜索输入框 (需创建)
│   │       ├── SearchConfig.vue     # 配置面板 (需创建)
│   │       ├── SearchResults.vue    # 结果列表 (需创建)
│   │       ├── ResultCard.vue       # 结果卡片 (需创建)
│   │       ├── ResultDetail.vue     # 结果详情弹窗 (需创建)
│   │       └── SearchHistory.vue    # 历史记录 (需创建)
│   ├── services/
│   │   └── searchApi.js             # API 服务 (需创建)
│   └── stores/
│       └── searchStore.js           # Pinia Store (需创建)
└── tests/
    └── components/                   # 组件测试 (需创建)
```

**Structure Decision**: Web Application 结构，前后端分离。前端参考现有模块的布局模式，后端复用 EmbeddingService 和 VectorIndexService。

## Key Design Decisions

### 1. 查询向量化

**Decision**: 复用 EmbeddingService 将查询文本转换为向量

**Rationale**: 
- 查询向量必须与文档向量使用相同模型
- 避免重复实现，降低维护成本

### 2. 相似度检索

**Decision**: 通过 VectorIndexService 调用已注册的 Provider

**Implementation Flow**:
```python
SearchService.search(query_text, config)
  → EmbeddingService.embed(query_text)
  → VectorIndexService.search(query_vector, index_ids, top_k, threshold)
  → 合并排序结果
```

### 3. 前端组件设计

**Decision**: 采用与现有模块一致的布局

**Layout**:
- 顶部：搜索输入框 + 搜索按钮
- 左侧：配置面板（索引选择、TopK、阈值、方法）
- 右侧：Tab 切换（搜索结果 | 历史记录）

### 4. 搜索历史

**Decision**: 数据库存储，最多保留 50 条

**Auto-cleanup**: 超出限制时自动删除最旧记录

## Complexity Tracking

> 无宪章违规，无需记录

## Generated Artifacts

| Artifact | Path | Status |
|----------|------|--------|
| research.md | specs/005-search-query/research.md | ✅ Complete |
| data-model.md | specs/005-search-query/data-model.md | ✅ Complete |
| search-api.yaml | specs/005-search-query/contracts/search-api.yaml | ✅ Complete |
| quickstart.md | specs/005-search-query/quickstart.md | ✅ Complete |

## Next Steps

运行 `/speckit.tasks` 生成详细的任务分解。
