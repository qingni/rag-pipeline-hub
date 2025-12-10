# Implementation Plan: 文档分块功能

**Branch**: `002-doc-chunking` | **Date**: 2025-12-05 | **Spec**: [spec.md](./spec.md)  
**Input**: Feature specification from `/specs/002-doc-chunking/spec.md`

## Summary

实现文档分块功能，支持从已保存的文档加载/解析JSON结果中读取内容，应用4种分块策略（按字数、按段落、按标题、按语义）将文档切分为合适大小的块，保存为标准JSON格式供后续向量嵌入使用。系统支持并发队列管理、自动降级机制、分块结果管理（查看、对比、删除、导出）和性能优化（分页加载）。

## Technical Context

**Language/Version**: Python 3.11+ (后端), JavaScript ES2020+ (前端)  
**Primary Dependencies**: 
- 后端: FastAPI 0.104.1, SQLAlchemy 2.0.23, langchain-text-splitters 0.3.4 (分块核心)
- 前端: Vue 3.3.8, Vue Router 4.2.5, Pinia 2.1.7, TDesign Vue Next 1.13.1, Axios 1.6.2

**Storage**: 
- SQLite (开发) / PostgreSQL (生产) - 数据库索引
- 文件系统 - JSON结果文件存储于 `results/chunking/`

**Testing**: 
- 后端: pytest 7.4.3, pytest-asyncio 0.21.1, httpx 0.25.2
- 前端: Vite test environment

**Target Platform**: 
- 后端: Linux/macOS server, Python runtime
- 前端: 现代浏览器 (Chrome 90+, Firefox 88+, Safari 14+)

**Project Type**: Web application (frontend + backend)

**Performance Goals**: 
- 标准文档 (10k字符) 分块时间 < 5秒
- 大型文档 (50k字符) 分块时间 < 30秒
- 分页加载 (500条记录) 响应时间 < 1秒
- 管理操作响应时间 < 2秒

**Constraints**: 
- 最多3个并发分块任务，其他任务队列等待
- 块大小范围: 50-5000字符
- 重叠度范围: 0-500字符
- 支持最大文档大小: 50MB (~5000万字符)

**Scale/Scope**: 
- 4种分块策略实现
- 支持历史记录分页管理 (500+ 记录)
- JSON + CSV 双格式导出
- 完整的前后端UI交互

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### ✅ Principle I: 模块化架构
- **Pass**: 分块功能设计为独立模块，通过 `chunking_service.py` 实现
- **Pass**: 通过读取 JSON 文件与其他模块松耦合
- **Pass**: 支持4种分块策略的插件化设计

### ✅ Principle II: 多提供商支持  
- **Pass**: 支持4种分块策略（按字数、按段落、按标题、按语义）
- **Pass**: 策略间可独立配置和切换
- **Pass**: 未来可扩展更多策略

### ✅ Principle III: 结果持久化 (NON-NEGOTIABLE)
- **Pass**: 分块结果保存为 JSON 格式到 `results/chunking/`
- **Pass**: 文件命名规范: `文档名_chunk_时间戳.json`
- **Pass**: 包含完整的文档级元信息和chunks列表
- **Pass**: 数据库建立索引便于查询和管理

### ✅ Principle IV: 用户体验优先
- **Pass**: 采用 Vue3 + Vite + TailwindCSS + TDesign 技术栈
- **Pass**: 左侧控制面板 + 右侧内容显示的统一布局
- **Pass**: 提供分块预览、结果对比、实时参数预览功能
- **Pass**: 支持历史记录分页和过滤排序

### ✅ Principle V: API标准化
- **Pass**: 基于 FastAPI 实现 RESTful API
- **Pass**: 统一的错误处理和响应格式
- **Pass**: 清晰的 API 端点设计 (/api/chunking/*)

### ✅ Technical Constraints
- **Pass**: 前端使用 Vue3 + TailwindCSS + TDesign
- **Pass**: 后端使用 FastAPI + chunking_service.py
- **Pass**: JSON 格式结果存储
- **Pass**: 符合核心功能模块架构

**Overall Status**: ✅ All gates passed - proceed to Phase 0

## Project Structure

### Documentation (this feature)

```text
specs/002-doc-chunking/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (chunking algorithms & libraries)
├── data-model.md        # Phase 1 output (entities & database schema)
├── quickstart.md        # Phase 1 output (developer setup guide)
├── contracts/           # Phase 1 output (API contracts)
│   └── chunking-api.yaml
└── tasks.md             # Phase 2 output (/speckit.tasks - NOT created yet)
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── models/
│   │   ├── chunking_task.py          # NEW: ChunkingTask entity
│   │   ├── chunking_strategy.py      # NEW: ChunkingStrategy entity
│   │   ├── document_chunk.py         # EXISTS: Update for new fields
│   │   └── chunking_result.py        # NEW: ChunkingResult entity
│   ├── services/
│   │   └── chunking_service.py       # NEW: Core chunking logic
│   ├── providers/
│   │   └── chunkers/
│   │       ├── __init__.py           # NEW: Strategy factory
│   │       ├── base_chunker.py       # NEW: Base class
│   │       ├── character_chunker.py  # NEW: 按字数分块
│   │       ├── paragraph_chunker.py  # NEW: 按段落分块
│   │       ├── heading_chunker.py    # NEW: 按标题分块
│   │       └── semantic_chunker.py   # NEW: 按语义分块
│   ├── api/
│   │   └── chunking.py               # NEW: API endpoints
│   ├── storage/
│   │   └── json_storage.py           # EXISTS: Extend for chunking
│   └── utils/
│       ├── chunking_validators.py    # NEW: Parameter validation
│       └── chunking_helpers.py       # NEW: Helper functions
└── tests/
    ├── unit/
    │   ├── test_character_chunker.py # NEW
    │   ├── test_paragraph_chunker.py # NEW
    │   ├── test_heading_chunker.py   # NEW
    │   ├── test_semantic_chunker.py  # NEW
    │   └── test_chunking_service.py  # NEW
    ├── integration/
    │   └── test_chunking_api.py      # NEW
    └── contract/
        └── test_chunking_contracts.py # NEW

frontend/
├── src/
│   ├── views/
│   │   └── ChunkingView.vue          # NEW: Main chunking page
│   ├── components/
│   │   ├── chunking/
│   │   │   ├── DocumentSelector.vue  # NEW: Select parsed docs
│   │   │   ├── StrategySelector.vue  # NEW: Choose strategy
│   │   │   ├── ParameterConfig.vue   # NEW: Config params
│   │   │   ├── ChunkingProgress.vue  # NEW: Progress bar
│   │   │   ├── ChunkList.vue         # NEW: Display chunks
│   │   │   ├── ChunkDetail.vue       # NEW: Chunk details
│   │   │   ├── HistoryList.vue       # NEW: History with pagination
│   │   │   ├── CompareResults.vue    # NEW: Compare two results
│   │   │   └── ExportDialog.vue      # NEW: Export options
│   ├── services/
│   │   └── chunkingService.js        # NEW: API calls
│   ├── stores/
│   │   └── chunkingStore.js          # NEW: State management
│   └── router/
│       └── index.js                  # UPDATE: Add chunking route
└── tests/
    └── components/
        └── chunking/                 # NEW: Component tests

results/
└── chunking/                         # NEW: Chunking JSON output directory
```

**Structure Decision**: Web application structure with separate frontend/backend directories. Backend follows existing patterns with models, services, providers, and API layers. Frontend uses Vue3 component architecture with dedicated chunking module. This maintains consistency with existing document loading and parsing modules.

## Complexity Tracking

> **No violations detected** - All constitution principles are satisfied without compromise.

The implementation follows the established patterns:
- Modular service design consistent with `loading_service.py` and `parsing_service.py`
- Multi-strategy support similar to multi-loader pattern
- JSON persistence matching existing result storage
- Standard Vue3 + TDesign UI patterns
- RESTful API design following existing conventions
