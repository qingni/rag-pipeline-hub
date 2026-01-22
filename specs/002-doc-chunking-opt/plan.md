# Implementation Plan: 文档分块功能优化

**Branch**: `002-doc-chunking-opt` | **Date**: 2026-01-20 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-doc-chunking-opt/spec.md`

## Summary

本次优化基于现有分块功能（002-doc-chunking），通过引入父子文档分块、多模态内容分块、智能策略推荐等高级分块技巧，结合 qwen3-embedding-8b 多模态向量化支持，全面提升 RAG 系统的检索效果。前端同步优化分块配置界面，提供更直观的策略选择和效果预览功能。

## Technical Context

**Language/Version**: Python 3.11 (后端) + JavaScript ES2020+ (前端)  
**Primary Dependencies**: FastAPI 0.104.1, LangChain (SemanticChunker), sentence-transformers, Vue 3, Vite, TDesign Vue Next, Pinia  
**Storage**: SQLite/PostgreSQL (元数据) + JSON (结果持久化)  
**Testing**: pytest (后端), Vitest (前端)  
**Target Platform**: Linux/macOS 服务器, 现代浏览器  
**Project Type**: Web 应用（前后端分离）  
**Performance Goals**: 分块预览 <3s (10000字符), 策略推荐 <1s, 流式处理支持 >50MB 文档  
**Constraints**: 内存使用 <2GB (大文档流式处理), API 响应 <5s p95  
**Scale/Scope**: 单文档最大 100MB, 并发分块任务 ≤3

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 原则 | 状态 | 说明 |
|------|------|------|
| I. 模块化架构 | ✅ PASS | 新增分块器作为 BaseChunker 子类，遵循策略模式；新增推荐服务独立实现 |
| II. 多提供商支持 | ✅ PASS | 语义分块升级支持 Embedding 模型（多提供商），保留 TF-IDF 作为 fallback |
| III. 结果持久化 | ✅ PASS | 分块结果保存为 JSON，支持版本管理和历史对比 |
| IV. 用户体验优先 | ✅ PASS | 前端采用 Vue3 + TDesign，优化策略推荐卡片、树形视图、类型图标 |
| V. API标准化 | ✅ PASS | 新增 API 遵循 RESTful 规范，统一错误处理 |

**Gate Result**: ✅ ALL PASS - 可进入 Phase 0

## Project Structure

### Documentation (this feature)

```text
specs/002-doc-chunking-opt/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── chunking-api.yaml
└── tasks.md             # Phase 2 output (by /speckit.tasks)
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── api/
│   │   ├── chunking.py              # 扩展：父子分块、混合策略端点
│   │   ├── chunking_preview.py      # 扩展：策略对比预览
│   │   └── chunking_recommend.py    # 新增：策略推荐 API
│   ├── models/
│   │   ├── chunk.py                 # 扩展：parent_id, chunk_type 字段
│   │   ├── chunking_result.py       # 已有版本管理支持
│   │   └── multimodal_chunk.py      # 新增：多模态分块模型
│   ├── providers/
│   │   └── chunkers/
│   │       ├── base_chunker.py      # 扩展：流式处理接口
│   │       ├── parent_child_chunker.py  # 新增：父子分块器
│   │       ├── hybrid_chunker.py    # 新增：混合策略分块器
│   │       ├── semantic_chunker.py  # 重构：升级为 Embedding 相似度
│   │       └── multimodal_chunker.py # 新增：多模态内容分块器
│   ├── services/
│   │   ├── chunking_service.py      # 扩展：流式处理、版本管理
│   │   ├── chunking_recommend_service.py  # 新增：推荐服务
│   │   └── embedding_service.py     # 扩展：qwen3-embedding-8b 多模态
│   └── utils/
│       └── chunking_helpers.py      # 扩展：文档结构分析
└── tests/
    ├── unit/
    │   └── chunkers/
    └── integration/

frontend/
├── src/
│   ├── components/
│   │   └── chunking/
│   │       ├── StrategySelector.vue     # 重构：策略推荐卡片
│   │       ├── ParameterConfig.vue      # 扩展：父子分块、混合策略参数
│   │       ├── ChunkList.vue            # 重构：树形视图支持
│   │       ├── ChunkDetail.vue          # 扩展：父块预览
│   │       ├── StrategyRecommendCard.vue # 新增：推荐卡片组件
│   │       ├── StrategyComparison.vue   # 新增：策略对比组件
│   │       └── ChunkTypeIcon.vue        # 新增：类型图标组件
│   ├── views/
│   │   └── DocumentChunk.vue            # 扩展：新布局
│   ├── stores/
│   │   └── chunkingStore.js             # 扩展：推荐、对比状态
│   └── services/
│       └── chunkingService.js           # 扩展：新 API 调用
└── tests/
```

**Structure Decision**: 沿用现有 Web 应用架构，在 backend/frontend 目录下扩展功能模块。

## Complexity Tracking

> 无宪章违规项，本节留空。
