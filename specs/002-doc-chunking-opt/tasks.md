# Tasks: 文档分块功能优化

**Input**: Design documents from `/specs/002-doc-chunking-opt/`  
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/chunking-api.yaml ✅, quickstart.md ✅

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1-US6)

## Path Conventions

- **Backend**: `backend/src/`
- **Frontend**: `frontend/src/`
- **Tests**: `backend/tests/`, `frontend/tests/`

---

## Phase 1: Setup (项目初始化)

**Purpose**: 数据库迁移和新依赖安装

- [x] T001 执行数据库迁移脚本，创建 `parent_chunks`, `hybrid_chunking_configs` 表，扩展 `chunks` 表字段 in `migrations/002-chunking-opt.sql`
- [x] T002 [P] 更新后端依赖：添加 `langchain_experimental`, `langchain_openai` 到 `backend/requirements.txt`
- [x] T003 [P] 添加环境变量配置 `SEMANTIC_CHUNKER_MODEL`, `MULTIMODAL_EMBEDDING_MODEL`, `LARGE_DOCUMENT_THRESHOLD` 到 `backend/src/config/settings.py`

---

## Phase 2: Foundational (基础设施)

**Purpose**: 核心模型和枚举扩展，所有用户故事依赖此阶段

**⚠️ CRITICAL**: 必须完成此阶段后才能开始用户故事实现

- [x] T004 扩展 `ChunkType` 枚举，添加 `TABLE`, `IMAGE`, `CODE` 类型 in `backend/src/models/chunk.py`
- [x] T005 [P] 扩展 `StrategyType` 枚举，添加 `PARENT_CHILD`, `HYBRID`, `MULTIMODAL` 类型 in `backend/src/models/chunking_strategy.py`
- [x] T006 [P] 扩展 `Chunk` 模型，添加 `chunk_type`, `parent_id` 字段 in `backend/src/models/chunk.py`
- [x] T007 创建 `ParentChunk` 模型 in `backend/src/models/parent_chunk.py`
- [x] T008 [P] 创建 `HybridChunkingConfig` 模型 in `backend/src/models/hybrid_chunking_config.py`
- [x] T009 扩展 `BaseChunker` 抽象类，添加 `chunk_stream` 方法签名（生成器接口）in `backend/src/providers/chunkers/base_chunker.py`
- [x] T010 创建多模态分块元数据 JSON Schema（TextChunkMetadata, TableChunkMetadata, ImageChunkMetadata, CodeChunkMetadata）in `backend/src/models/chunk_metadata.py`
- [x] T010a [P] 扩展 `CharacterChunker`，添加滑动窗口参数支持（window_size, step_size）实现 FR-005 in `backend/src/providers/chunkers/character_chunker.py`

**Checkpoint**: 基础模型就绪，可开始用户故事实现

---

## Phase 3: User Story 1 - 智能分块策略推荐与选择 (Priority: P1) 🎯 MVP

**Goal**: 用户能够获得系统推荐的最佳分块策略，并快速选择合适的分块方式

**Independent Test**: 上传不同类型文档，验证推荐策略是否合理

### Implementation for User Story 1

- [ ] T011 [US1] 创建 `DocumentFeatures` 数据类 in `backend/src/models/document_features.py`
- [ ] T012 [P] [US1] 创建 `ChunkingRecommendation` 数据类 in `backend/src/models/chunking_recommendation.py`
- [ ] T013 [US1] 实现文档结构分析逻辑（标题计数、段落分析、表格/图片/代码块统计）in `backend/src/utils/document_analyzer.py`
- [ ] T014 [US1] 实现 `ChunkingRecommendService`，包含推荐规则引擎 in `backend/src/services/chunking_recommend_service.py`
- [ ] T015 [US1] 实现 `/chunking/recommend` API 端点 in `backend/src/api/chunking_recommend.py`
- [ ] T016 [P] [US1] 实现 `/chunking/analyze` API 端点 in `backend/src/api/chunking_recommend.py`
- [ ] T017 [US1] 注册新路由到主应用 in `backend/src/main.py`
- [ ] T018 [P] [US1] 创建 `StrategyRecommendCard.vue` 组件（推荐卡片，显示策略名称、理由、预估块数、应用按钮）in `frontend/src/components/chunking/StrategyRecommendCard.vue`
- [ ] T019 [P] [US1] 创建 `ChunkTypeIcon.vue` 组件（显示不同分块类型图标）in `frontend/src/components/chunking/ChunkTypeIcon.vue`
- [ ] T020 [US1] 扩展 `chunkingStore.js`，添加推荐状态管理（recommendations, documentFeatures）in `frontend/src/stores/chunkingStore.js`
- [ ] T021 [US1] 扩展 `chunkingService.js`，添加 `getRecommendations()`, `analyzeDocument()` 方法 in `frontend/src/services/chunkingService.js`
- [ ] T022 [US1] 重构 `StrategySelector.vue`，集成策略推荐卡片显示 in `frontend/src/components/chunking/StrategySelector.vue`

**Checkpoint**: 用户可以获取策略推荐，MVP 完成

---

## Phase 4: User Story 2 - 父子文档分块处理 (Priority: P1)

**Goal**: 用户能够使用父子文档分块，小块检索+大块上下文

**Independent Test**: 对同一文档使用父子分块和普通分块，对比检索效果

### Implementation for User Story 2

- [x] T023 [US2] 实现 `ParentChildChunker` 分块器（生成父块、子块，子块包含 parent_id）in `backend/src/providers/chunkers/parent_child_chunker.py`
- [x] T024 [US2] 注册 `ParentChildChunker` 到分块器工厂 in `backend/src/providers/chunkers/__init__.py`
- [x] T025 [US2] 扩展 `ChunkingService`，支持父子分块任务创建和结果保存（包含 ParentChunk 存储）in `backend/src/services/chunking_service.py`
- [x] T026 [US2] 实现 `/chunking/result/{result_id}/parents` API 端点（获取父块列表）in `backend/src/api/chunking.py`
- [x] T027 [US2] 扩展 `/chunking/result/{result_id}/chunks` 支持 `parent_id` 和 `include_parent` 参数 in `backend/src/api/chunking.py`
- [x] T028 [P] [US2] 扩展 `ParameterConfig.vue`，添加父子分块参数配置（父块大小、子块大小、子块重叠度）in `frontend/src/components/chunking/ParameterConfig.vue`
- [x] T029 [US2] 重构 `ChunkList.vue`，支持树形视图展示父子关系 in `frontend/src/components/chunking/ChunkList.vue`
- [x] T030 [US2] 扩展 `ChunkDetail.vue`，添加父块内容预览和跳转功能 in `frontend/src/components/chunking/ChunkDetail.vue`
- [x] T031 [US2] 扩展 `chunkingStore.js`，添加父块状态管理 in `frontend/src/stores/chunkingStore.js`
- [x] T032 [US2] 扩展 `chunkingService.js`，添加 `getParentChunks()` 方法 in `frontend/src/services/chunkingService.js`

**Checkpoint**: 父子分块功能完整可用 ✅

---

## Phase 5: User Story 3 - 多模态内容分块 (Priority: P2)

**Goal**: 表格、图片等非文本内容独立分块处理

**Independent Test**: 上传包含表格和图片的文档，验证独立分块和类型标识

### Implementation for User Story 3

- [x] T033 [US3] 实现 `MultimodalChunker` 分块器（从文档加载结果提取表格/图片，生成独立分块）in `backend/src/providers/chunkers/multimodal_chunker.py`
- [x] T034 [US3] 注册 `MultimodalChunker` 到分块器工厂 in `backend/src/providers/chunkers/__init__.py`
- [x] T035 [US3] 扩展 `/chunking/result/{result_id}/chunks` API，支持 `chunk_type` 筛选参数 in `backend/src/api/chunking.py`
- [x] T036 [P] [US3] 扩展 `ParameterConfig.vue`，添加多模态分块参数配置（include_tables, include_images, text_strategy）in `frontend/src/components/chunking/ParameterConfig.vue`
- [x] T037 [US3] 扩展 `ChunkList.vue`，添加类型筛选下拉框和类型图标显示 in `frontend/src/components/chunking/ChunkList.vue`
- [x] T038 [US3] 扩展 `ChunkDetail.vue`，根据 chunk_type 显示不同的元数据信息 in `frontend/src/components/chunking/ChunkDetail.vue`

**Checkpoint**: 多模态分块功能完整可用 ✅

---

## Phase 6: User Story 4 - 混合分块策略配置 (Priority: P2)

**Goal**: 针对不同内容类型应用不同分块策略

**Independent Test**: 上传包含正文、代码、表格的技术文档，验证混合策略分块

### Implementation for User Story 4

- [ ] T039 [US4] 实现 `HybridChunker` 分块器（根据内容类型分发到不同子分块器）in `backend/src/providers/chunkers/hybrid_chunker.py`
- [ ] T040 [US4] 注册 `HybridChunker` 到分块器工厂 in `backend/src/providers/chunkers/__init__.py`
- [ ] T041 [US4] 扩展 `ChunkingService`，支持混合分块配置保存（HybridChunkingConfig）in `backend/src/services/chunking_service.py`
- [ ] T042 [P] [US4] 扩展 `ParameterConfig.vue`，添加混合策略配置 UI（各内容类型策略选择下拉框）in `frontend/src/components/chunking/ParameterConfig.vue`
- [ ] T043 [US4] 扩展分块统计信息，显示各类型内容的分块数量 in `frontend/src/components/chunking/ChunkList.vue`

**Checkpoint**: 混合分块策略功能完整可用

---

## Phase 7: User Story 5 - 分块效果预览与对比 (Priority: P3)

**Goal**: 预览分块效果，对比不同策略

**Independent Test**: 选择不同策略和参数，验证预览和对比功能

### Implementation for User Story 5

- [ ] T044 [US5] 实现 `/chunking/preview` API 端点（使用文档前 10% 进行试分块）in `backend/src/api/chunking_preview.py`
- [ ] T045 [US5] 实现 `/chunking/compare` API 端点（并排对比最多 3 种策略）in `backend/src/api/chunking_preview.py`
- [ ] T046 [US5] 注册预览路由到主应用 in `backend/src/main.py`
- [ ] T047 [P] [US5] 创建 `StrategyComparison.vue` 组件（并排展示策略对比结果、统计图表）in `frontend/src/components/chunking/StrategyComparison.vue`
- [ ] T048 [US5] 扩展 `chunkingStore.js`，添加预览和对比状态管理 in `frontend/src/stores/chunkingStore.js`
- [ ] T049 [US5] 扩展 `chunkingService.js`，添加 `preview()`, `compare()` 方法 in `frontend/src/services/chunkingService.js`
- [ ] T050 [US5] 扩展 `ParameterConfig.vue`，添加实时预估更新（块数量、平均大小、预计时间）in `frontend/src/components/chunking/ParameterConfig.vue`
- [ ] T051 [US5] 更新 `DocumentChunk.vue` 页面，集成预览和对比功能入口 in `frontend/src/views/DocumentChunk.vue`

**Checkpoint**: 预览和对比功能完整可用

---

## Phase 8: User Story 6 - 支持 qwen3-embedding-8b 多模态向量化准备 (Priority: P2)

**Goal**: 为分块结果保存多模态向量化所需数据（图片 base64、类型标识）

**Independent Test**: 验证图片分块包含 base64 数据，表格分块包含 Markdown 格式

**注意**: 此阶段仅为后续向量化（003/004 分支）做数据准备，不执行实际向量化

### Implementation for User Story 6

- [ ] T052 [US6] 扩展 `MultimodalChunker`，确保图片分块保存 base64 数据 in `backend/src/providers/chunkers/multimodal_chunker.py`
- [ ] T053 [US6] 扩展 `MultimodalChunker`，确保表格分块保存完整 Markdown 格式 in `backend/src/providers/chunkers/multimodal_chunker.py`
- [ ] T054 [US6] 添加分块元数据验证，确保多模态块包含必要字段 in `backend/src/services/chunking_service.py`

**Checkpoint**: 分块结果包含多模态向量化所需的完整数据

---

## Phase 9: 扩展功能（大文档流式处理 + 版本管理）

**Purpose**: 处理大文档的流式分块和分块结果版本管理

### 流式处理

- [ ] T055 实现 `StreamingChunker` 基类，支持生成器模式分块 in `backend/src/providers/chunkers/streaming_chunker.py`
- [ ] T056 扩展各分块器，继承流式处理能力 in `backend/src/providers/chunkers/*.py`
- [ ] T057 实现 `/chunking/stream` SSE 端点（流式分块）in `backend/src/api/chunking.py`

### 版本管理

- [ ] T058 扩展 `ChunkingService`，实现版本创建逻辑（previous_version_id, is_active 管理）in `backend/src/services/chunking_service.py`
- [ ] T059 实现 `/chunking/versions/{document_id}` API 端点（获取版本历史）in `backend/src/api/chunking_version.py`
- [ ] T060 实现 `/chunking/versions/{result_id}/rollback` API 端点（版本回滚）in `backend/src/api/chunking_version.py`
- [ ] T061 实现 `/chunking/versions/compare` API 端点（版本对比）in `backend/src/api/chunking_version.py`
- [ ] T062 注册版本管理路由到主应用 in `backend/src/main.py`

---

## Phase 10: 语义分块算法升级

**Purpose**: 将语义分块从 TF-IDF 升级为 Embedding 相似度

- [ ] T063 重构 `SemanticChunker`，使用 LangChain `SemanticChunker` 实现 Embedding 相似度分块 in `backend/src/providers/chunkers/semantic_chunker.py`
- [ ] T064 实现 TF-IDF fallback 机制（Embedding 服务不可用时自动降级）in `backend/src/providers/chunkers/semantic_chunker.py`
- [ ] T065 添加环境变量配置，支持选择 Embedding 模型 in `backend/src/config/settings.py`

---

## Phase 11: Polish & 收尾

**Purpose**: 代码整理、边界情况处理、验收

- [ ] T066 [P] 添加参数验证（父块大小 > 子块大小，策略对比最多 3 种）in `backend/src/api/chunking.py`
- [ ] T067 [P] 添加边界情况处理（空文档、无结构文档、损坏表格、无效图片路径）in `backend/src/providers/chunkers/*.py`
- [ ] T068 更新 API 错误响应格式，统一错误处理 in `backend/src/api/error_handlers.py`
- [ ] T069 运行 quickstart.md 验证，确保所有示例 API 调用正常 
- [ ] T070 代码审查和清理，移除调试日志

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Setup)
    ↓
Phase 2 (Foundational) ← BLOCKS ALL USER STORIES
    ↓
Phase 3-8 (User Stories) ← 可并行执行
    ↓
Phase 9-10 (扩展功能) ← 可与 User Stories 并行
    ↓
Phase 11 (Polish)
```

### User Story Dependencies

| User Story | 前置依赖 | 可并行 |
|------------|----------|--------|
| US1 (智能推荐) | Phase 2 | ✅ |
| US2 (父子分块) | Phase 2 | ✅ |
| US3 (多模态分块) | Phase 2 | ✅ |
| US4 (混合分块) | Phase 2, US3 | ✅ (US3 完成后) |
| US5 (预览对比) | Phase 2 | ✅ |
| US6 (向量化准备) | US3 | ✅ (US3 完成后) |

### Within Each User Story

- Models → Services → API → Frontend Store → Frontend Service → Frontend Components

### Parallel Opportunities

```bash
# Phase 2 并行任务
T005, T006, T008, T010 可并行

# US1 并行任务
T012, T016, T018, T019 可并行

# US2 并行任务
T028 可并行（与后端开发）

# US3 并行任务
T036 可并行（与后端开发）
```

---

## Implementation Strategy

### MVP First (User Story 1 + 2)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL)
3. Complete Phase 3: User Story 1 (智能推荐)
4. Complete Phase 4: User Story 2 (父子分块)
5. **STOP and VALIDATE**: 验证推荐 + 父子分块核心功能
6. Deploy/Demo MVP

### Incremental Delivery

| 迭代 | 交付内容 | 累计功能 |
|------|----------|----------|
| MVP | US1 + US2 | 智能推荐、父子分块 |
| 迭代 2 | US3 + US4 | + 多模态分块、混合策略 |
| 迭代 3 | US5 | + 预览对比 |
| 迭代 4 | US6 + Phase 9-10 | + 向量化准备、流式处理、版本管理 |
| 迭代 5 | Phase 11 | 完善边界处理、收尾 |

---

## Summary

| 统计项 | 数量 |
|--------|------|
| **总任务数** | 71 |
| **Phase 1 (Setup)** | 3 |
| **Phase 2 (Foundational)** | 8 |
| **US1 (智能推荐)** | 12 |
| **US2 (父子分块)** | 10 |
| **US3 (多模态分块)** | 6 |
| **US4 (混合分块)** | 5 |
| **US5 (预览对比)** | 8 |
| **US6 (向量化准备)** | 3 |
| **Phase 9 (流式+版本)** | 8 |
| **Phase 10 (语义升级)** | 3 |
| **Phase 11 (Polish)** | 5 |
| **可并行任务 [P]** | 19 |

---

## Notes

- [P] tasks = 不同文件，无依赖，可并行执行
- [Story] label = 任务归属的用户故事，便于追溯
- 每个用户故事应独立可测试
- 每完成一个 Checkpoint 进行验收
- 提交时按任务或逻辑组提交
