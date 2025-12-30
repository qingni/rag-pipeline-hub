# Tasks: 文本生成功能

**Input**: Design documents from `/specs/006-text-generation/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 项目初始化和基础结构创建

- [X] T001 创建数据库迁移文件 `migrations/create_generation_history_table.sql`
- [X] T002 [P] 创建后端 Pydantic schemas 文件 `backend/src/schemas/generation.py`
- [X] T003 [P] 创建前端 API 服务文件 `frontend/src/services/generationApi.js`
- [X] T004 [P] 创建前端 Pinia Store 文件 `frontend/src/stores/generationStore.js`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 核心基础设施，所有用户故事依赖的基础组件

**⚠️ CRITICAL**: 必须完成此阶段后才能开始用户故事实现

- [X] T005 创建 GenerationHistory 数据模型 `backend/src/models/generation.py`
- [X] T006 创建 GenerationService 核心服务类框架 `backend/src/services/generation_service.py`
- [X] T007 定义生成模型配置 GENERATION_MODELS 字典 `backend/src/services/generation_service.py`
- [X] T008 [P] 创建 Generation API 路由文件框架 `backend/src/api/generation.py`
- [X] T009 在 main.py 中注册 Generation 路由 `backend/src/main.py`
- [X] T010 [P] 创建前端 Generation 主页面框架 `frontend/src/views/Generation.vue`
- [X] T011 在前端路由中添加 Generation 页面路由 `frontend/src/router/index.js`
- [X] T012 在前端导航菜单中添加"文本生成"入口 `frontend/src/App.vue`

**Checkpoint**: 基础设施就绪 - 可以开始用户故事实现

---

## Phase 3: User Story 1 - RAG问答生成 (Priority: P1) 🎯 MVP

**Goal**: 用户基于检索结果和问题，选择模型生成回答，支持流式输出

**Independent Test**: 用户在页面输入问题，选择模型，点击生成按钮，看到流式输出的回答

### Implementation for User Story 1

#### 后端实现

- [X] T013 [US1] 实现 Prompt 模板构建方法 `_build_prompt()` in `backend/src/services/generation_service.py`
- [X] T014 [US1] 实现 ChatOpenAI 客户端初始化方法 `_get_llm_client()` in `backend/src/services/generation_service.py`
- [X] T015 [US1] 实现非流式生成方法 `generate()` in `backend/src/services/generation_service.py`
- [X] T016 [US1] 实现流式生成方法 `generate_stream()` in `backend/src/services/generation_service.py`
- [X] T017 [US1] 实现取消生成方法 `cancel_generation()` in `backend/src/services/generation_service.py`
- [X] T018 [US1] 实现非流式生成 API 端点 `POST /generation/generate` in `backend/src/api/generation.py`
- [X] T019 [US1] 实现流式生成 API 端点 `POST /generation/stream` (SSE) in `backend/src/api/generation.py`
- [X] T020 [US1] 实现取消生成 API 端点 `POST /generation/cancel/{request_id}` in `backend/src/api/generation.py`
- [X] T021 [US1] 添加错误处理和重试机制 in `backend/src/services/generation_service.py`
- [X] T021a [US1] 实现无检索结果时的无上下文生成模式 in `backend/src/services/generation_service.py`
- [X] T021b [US1] 实现生成中断时保存已生成内容逻辑 in `backend/src/services/generation_service.py`

#### 前端实现

- [X] T022 [P] [US1] 创建问题输入组件 `frontend/src/components/Generation/GenerationInput.vue`
- [X] T023 [P] [US1] 创建结果展示组件（支持流式渲染、解析 [n] 引用标记并高亮）`frontend/src/components/Generation/GenerationResult.vue`
- [X] T024 [P] [US1] 创建来源引用组件（展示引用列表、支持点击跳转）`frontend/src/components/Generation/SourceReference.vue`
- [X] T025 [US1] 在 generationApi.js 中实现流式生成 API 调用 `frontend/src/services/generationApi.js`
- [X] T026 [US1] 在 generationStore.js 中实现生成状态管理 `frontend/src/stores/generationStore.js`
- [X] T027 [US1] 在 Generation.vue 中集成输入、结果、来源组件 `frontend/src/views/Generation.vue`
- [X] T028 [US1] 实现流式输出的 EventSource 处理逻辑 `frontend/src/views/Generation.vue`
- [X] T029 [US1] 添加生成中状态显示和取消按钮 `frontend/src/views/Generation.vue`

**Checkpoint**: User Story 1 完成 - 用户可以进行基础的 RAG 问答生成

---

## Phase 4: User Story 2 - 模型选择与配置 (Priority: P2)

**Goal**: 用户可以选择不同模型，配置温度和最大输出长度参数

**Independent Test**: 用户在配置面板选择模型、调整参数，生成时使用配置的参数

### Implementation for User Story 2

#### 后端实现

- [X] T030 [US2] 实现获取可用模型列表 API `GET /generation/models` in `backend/src/api/generation.py`
- [X] T031 [US2] 在 GenerationService 中添加参数验证逻辑 `backend/src/services/generation_service.py`

#### 前端实现

- [X] T032 [US2] 创建配置面板组件 `frontend/src/components/Generation/GenerationConfig.vue`
- [X] T033 [US2] 实现模型选择下拉框（显示模型名称和描述）`frontend/src/components/Generation/GenerationConfig.vue`
- [X] T034 [US2] 实现温度参数滑块（0.0-2.0）`frontend/src/components/Generation/GenerationConfig.vue`
- [X] T035 [US2] 实现最大输出长度输入框（1-8192）`frontend/src/components/Generation/GenerationConfig.vue`
- [X] T036 [US2] 在 generationApi.js 中实现获取模型列表 API `frontend/src/services/generationApi.js`
- [X] T037 [US2] 在 generationStore.js 中管理配置状态 `frontend/src/stores/generationStore.js`
- [X] T038 [US2] 在 Generation.vue 中集成配置面板组件 `frontend/src/views/Generation.vue`

**Checkpoint**: User Story 2 完成 - 用户可以选择模型和配置参数

---

## Phase 5: User Story 3 - 生成历史管理 (Priority: P3)

**Goal**: 用户可以查看、删除历史生成记录，查看完整详情

**Independent Test**: 用户在历史记录面板查看过往记录，点击查看详情，删除记录

### Implementation for User Story 3

#### 后端实现

- [X] T039 [US3] 实现保存生成历史记录方法 `save_history()` in `backend/src/services/generation_service.py`
- [X] T040 [US3] 实现历史记录自动清理（超过100条删除最旧）`backend/src/services/generation_service.py`
- [X] T041 [US3] 实现获取历史列表 API `GET /generation/history` in `backend/src/api/generation.py`
- [X] T042 [US3] 实现获取历史详情 API `GET /generation/history/{id}` in `backend/src/api/generation.py`
- [X] T043 [US3] 实现删除历史记录 API `DELETE /generation/history/{id}` in `backend/src/api/generation.py`
- [X] T044 [US3] 实现清空历史记录 API `DELETE /generation/history/clear` in `backend/src/api/generation.py`

#### 前端实现

- [X] T045 [US3] 创建历史记录列表组件 `frontend/src/components/Generation/GenerationHistory.vue`
- [X] T046 [US3] 实现历史记录卡片（显示问题、模型、时间、状态）`frontend/src/components/Generation/GenerationHistory.vue`
- [X] T047 [US3] 实现历史详情弹窗（完整问题、回答、上下文）`frontend/src/components/Generation/GenerationHistory.vue`
- [X] T048 [US3] 实现删除确认和清空功能 `frontend/src/components/Generation/GenerationHistory.vue`
- [X] T049 [US3] 在 generationApi.js 中实现历史相关 API `frontend/src/services/generationApi.js`
- [X] T050 [US3] 在 generationStore.js 中管理历史状态 `frontend/src/stores/generationStore.js`
- [X] T051 [US3] 在 Generation.vue 中集成历史记录组件（Tab 切换）`frontend/src/views/Generation.vue`

**Checkpoint**: User Story 3 完成 - 用户可以管理生成历史记录

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: 跨用户故事的改进和优化

- [X] T052 [P] 添加边缘情况处理：问题过长超出上下文限制 `backend/src/services/generation_service.py`
- [X] T053 [P] 优化前端流式输出渲染性能 `frontend/src/components/Generation/GenerationResult.vue`
- [X] T054 [P] 添加加载状态和错误提示优化 `frontend/src/views/Generation.vue`
- [X] T055 运行 quickstart.md 验证所有功能

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Setup)
    │
    ▼
Phase 2 (Foundational) ─── BLOCKS ALL USER STORIES
    │
    ├──────────────────────────────────────┐
    │                                      │
    ▼                                      ▼
Phase 3 (US1: RAG问答)              Phase 4 (US2: 模型配置)
    │                                      │
    └──────────────┬───────────────────────┘
                   │
                   ▼
            Phase 5 (US3: 历史管理)
                   │
                   ▼
            Phase 6 (Polish)
```

### User Story Dependencies

| User Story | 依赖 | 说明 |
|------------|------|------|
| US1 (RAG问答) | Phase 2 | 核心功能，无其他故事依赖 |
| US2 (模型配置) | Phase 2 | 可与 US1 并行，但建议 US1 先完成 |
| US3 (历史管理) | US1 | 依赖生成功能产生历史数据 |

### Within Each User Story

1. 后端模型/服务 → 后端 API → 前端组件 → 前端集成
2. 标记 [P] 的任务可以并行执行

### Parallel Opportunities

```bash
# Phase 1 - 所有任务可并行
T002, T003, T004 可同时执行

# Phase 2 - 部分任务可并行
T008, T010 可同时执行（后端 API 框架 & 前端页面框架）

# Phase 3 (US1) - 前端组件可并行
T022, T023, T024 可同时执行

# Phase 4 (US2) - 后端完成后前端可并行
T032-T035 前端组件开发可并行

# Phase 5 (US3) - 后端完成后前端可并行
T045-T048 前端组件开发可并行

# Phase 6 - 所有优化任务可并行
T052, T053, T054 可同时执行
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. ✅ Complete Phase 1: Setup (T001-T004)
2. ✅ Complete Phase 2: Foundational (T005-T012)
3. ✅ Complete Phase 3: User Story 1 (T013-T029)
4. **STOP and VALIDATE**: 测试基础 RAG 问答功能
5. 可部署/演示 MVP

### Incremental Delivery

1. Setup + Foundational → 基础就绪
2. Add US1 (RAG问答) → 测试 → **MVP 发布!**
3. Add US2 (模型配置) → 测试 → 增强版发布
4. Add US3 (历史管理) → 测试 → 完整版发布
5. Add Polish → 优化版发布

---

## Task Summary

| Phase | 任务数 | 说明 |
|-------|--------|------|
| Phase 1: Setup | 4 | 基础文件创建 |
| Phase 2: Foundational | 8 | 核心基础设施 |
| Phase 3: US1 RAG问答 | 19 | MVP 核心功能（含边缘情况） |
| Phase 4: US2 模型配置 | 9 | 配置增强 |
| Phase 5: US3 历史管理 | 13 | 历史功能 |
| Phase 6: Polish | 4 | 优化完善 |
| **Total** | **57** | |

### Per User Story

| User Story | 任务数 | 后端 | 前端 |
|------------|--------|------|------|
| US1 RAG问答 | 19 | 11 | 8 |
| US2 模型配置 | 9 | 2 | 7 |
| US3 历史管理 | 13 | 6 | 7 |

### Parallel Opportunities

- Phase 1: 3 个并行任务
- Phase 2: 2 组并行任务
- Phase 3: 3 个并行前端组件
- Phase 4: 4 个并行前端组件
- Phase 5: 4 个并行前端组件
- Phase 6: 5 个并行优化任务

---

## Notes

- [P] 任务 = 不同文件，无依赖关系
- [Story] 标签将任务映射到特定用户故事
- 每个用户故事应该可以独立完成和测试
- 每个任务或逻辑组完成后提交
- 在任何检查点停止以独立验证故事
- 避免：模糊任务、同一文件冲突、破坏独立性的跨故事依赖
