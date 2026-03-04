# Implementation Plan: 向量索引模块（优化版）

**Branch**: `004-vector-index-opt` | **Date**: 2026-02-06 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/004-vector-index-opt/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

向量索引模块是 RAG 系统的核心检索基础设施，基于 Milvus 向量数据库提供索引构建、相似度检索、混合检索（稠密+稀疏双路召回 + RRF 粗排 + Reranker 精排）和智能推荐能力。本版本移除 FAISS 支持，统一使用 Milvus 作为唯一向量存储后端，并新增智能推荐引擎（根据向量特征自动推荐索引算法和度量类型）。

## Technical Context

**Language/Version**: Python 3.11 (Backend), TypeScript/JavaScript (Frontend Vue3)  
**Primary Dependencies**: FastAPI >=0.110.0, pymilvus 2.4.9, FlagEmbedding >=1.2.0, Vue 3.x, TDesign Vue Next, Pinia  
**Storage**: Milvus 2.4+ (向量数据), SQLite/PostgreSQL (任务元数据, 推荐规则, 推荐行为日志)  
**Testing**: pytest (Backend), Vitest (Frontend)  
**Target Platform**: Linux server (Docker), macOS 开发环境  
**Project Type**: web (frontend + backend)  
**Performance Goals**: 纯稠密检索 <100ms P95, 混合检索 <200ms P95, Reranker 精排 <100ms P95, 智能推荐 <500ms P95  
**Constraints**: Milvus 2.4+ (hybrid_search 支持), CPU 环境 Reranker 推理, 推荐采纳率 ≥80%  
**Scale/Scope**: 1K-1M 向量规模, 10+ 并发查询, 50 QPS 吞吐量

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| I. 模块化架构 | ✅ PASS | 向量索引模块独立设计，通过 RESTful API 通信，独立 service 文件 (index_service.py, recommendation_service.py) |
| II. 多提供商支持 | ✅ PASS | 本版本专注 Milvus（移除 FAISS），Milvus 作为 constitution 明确列出的向量数据库选项 |
| III. 结果持久化 (NON-NEGOTIABLE) | ✅ PASS | 索引结果、检索结果、推荐行为日志均以 JSON 格式持久化，文件命名含时间戳 |
| IV. 用户体验优先 | ✅ PASS | Vue3 + TDesign，左右分栏布局，智能推荐自动填充 + 理由标签 |
| V. API 标准化 | ✅ PASS | FastAPI RESTful，统一错误处理（ErrorResponse），OpenAPI 契约文档 |

**Gate Result**: ✅ ALL PASS — 无违规项

### Post-Design Re-check (Phase 1 完成后)

| Principle | Status | Evidence |
|-----------|--------|----------|
| I. 模块化架构 | ✅ PASS | RecommendationEngine 独立模块，通过 /recommend API 通信 |
| II. 多提供商支持 | ✅ PASS | 推荐规则以 JSON 配置表存储，可扩展支持其他向量数据库的推荐 |
| III. 结果持久化 | ✅ PASS | recommendation_logs 表持久化所有推荐行为 |
| IV. 用户体验优先 | ✅ PASS | 推荐理由标签、兜底提示、非阻塞推荐（延迟超时用户可手动选择） |
| V. API 标准化 | ✅ PASS | 新增 /recommend、/recommend/log、/recommend/stats 三个标准 REST 端点 |

## Project Structure

### Documentation (this feature)

```text
specs/004-vector-index-opt/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output — 13 research tasks completed
├── data-model.md        # Phase 1 output — 7 entities (incl. RecommendationRule, RecommendationLog)
├── quickstart.md        # Phase 1 output — 5 scenarios (incl. smart recommendation)
├── contracts/           # Phase 1 output
│   ├── index-api.yaml   # 索引管理 + 智能推荐 API (v2.2.0)
│   └── search-api.yaml  # 检索 API (v2.1.0)
├── checklists/
│   └── requirements.md  # 需求检查清单
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── models/              # 数据模型
│   │   └── vector_index.py  # VectorIndex, IndexTask, HybridSearchResult, RecommendationRule, RecommendationLog
│   ├── services/
│   │   ├── vector_index_service.py    # 索引构建/更新/删除服务
│   │   ├── search_service.py          # 检索 + 混合检索服务
│   │   ├── providers/
│   │   │   └── milvus_provider.py     # Milvus 连接管理/CRUD
│   │   ├── reranker_service.py        # qwen3-reranker-4b 精排服务
│   │   └── recommendation_service.py  # 智能推荐引擎（NEW）
│   ├── api/
│   │   └── vector_index.py            # 索引管理 + 检索 + 推荐 REST 端点（统一入口）
│   ├── utils/
│   │   ├── vector_utils.py            # 向量验证工具
│   │   ├── sparse_utils.py            # 稀疏向量工具
│   │   ├── result_persistence.py      # 结果持久化
│   │   ├── error_handlers.py          # 统一错误处理
│   │   └── index_logging.py           # 操作日志
│   ├── exceptions/
│   │   └── vector_index_errors.py     # 异常体系
│   └── config/
│       └── recommendation_rules.json  # 推荐规则配置表（NEW）
├── tests/
│   ├── unit/
│   │   └── test_recommendation.py     # 推荐引擎单元测试（NEW）
│   └── integration/
│       └── test_index_api.py          # API 集成测试
└── migrations/
    └── vector_index/
        └── 008_recommendation.sql     # 推荐规则表 + 行为日志表（NEW）

frontend/
├── src/
│   ├── components/
│   │   └── VectorIndex/
│   │       ├── IndexCreate.vue        # 索引配置面板（含推荐展示）
│   │       ├── IndexList.vue          # 索引列表
│   │       ├── IndexHistory.vue       # 历史记录
│   │       ├── IndexProgress.vue      # 索引进度组件
│   │       ├── VectorSearch.vue       # 检索面板（含混合检索模式切换）
│   │       ├── RecommendBadge.vue     # 推荐理由标签组件（NEW）
│   │       └── RecommendFallback.vue  # 兜底提示组件（NEW）
│   ├── services/
│   │   └── vectorIndexApi.js          # API 调用层（含推荐接口）
│   ├── stores/
│   │   └── vectorIndexStore.js        # Pinia 状态管理
│   └── views/
│       └── VectorIndex.vue            # 索引管理主页面
└── tests/
    └── components/
        └── RecommendBadge.spec.js     # 推荐标签组件测试（NEW）
```

**Structure Decision**: Web application structure (Option 2) — 前后端分离的 Vue3 + FastAPI 架构，与现有项目结构一致。

## Complexity Tracking

> 无违规项，无需 Complexity Tracking。

## Generated Artifacts

| Artifact | Path | Status |
|----------|------|--------|
| research.md | `specs/004-vector-index-opt/research.md` | ✅ Updated (13 research tasks) |
| data-model.md | `specs/004-vector-index-opt/data-model.md` | ✅ Updated (7 entities) |
| quickstart.md | `specs/004-vector-index-opt/quickstart.md` | ✅ Updated (5 scenarios) |
| index-api.yaml | `specs/004-vector-index-opt/contracts/index-api.yaml` | ✅ Updated (v2.2.0, +3 recommend endpoints) |
| search-api.yaml | `specs/004-vector-index-opt/contracts/search-api.yaml` | ✅ Unchanged (v2.1.0) |
| plan.md | `specs/004-vector-index-opt/plan.md` | ✅ This file |
