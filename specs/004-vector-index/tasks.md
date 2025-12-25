# Tasks: 向量索引模块

**Input**: Design documents from `/specs/004-vector-index/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

**Tests**: 未明确要求测试，本任务清单不包含测试任务。如需测试，请单独请求。

**Organization**: 任务按用户故事组织，支持独立实现和测试。

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 可并行执行（不同文件，无依赖）
- **[Story]**: 任务所属用户故事（US1, US2, US3...）
- 描述中包含精确的文件路径

## User Stories Summary (from spec.md)

| Story | Priority | Title | Description |
|-------|----------|-------|-------------|
| US1 | P1 | 向量数据索引构建 | 接收向量数据并构建索引 |
| US2 | P1 | 向量相似度检索 | TopK 相似度搜索 |
| US3 | P2 | 索引更新与删除 | 增量更新向量 |
| US4 | P2 | 索引持久化与恢复 | 磁盘持久化 |
| US5 | P3 | 多索引管理 | 多索引创建和管理 |
| US6 | P1 | 前端索引管理界面 | Web 界面交互 |

---

## Phase 1: Setup (共享基础设施)

**Purpose**: 项目初始化和基础结构

- [X] T001 创建数据库迁移文件 `migrations/005_vector_index_embedding_integration.sql`
- [X] T002 [P] 创建 Provider 基类 `backend/src/services/providers/base_provider.py`
- [X] T003 [P] 创建前端组件目录结构 `frontend/src/components/VectorIndex/`

---

## Phase 2: Foundational (阻塞性前置任务)

**Purpose**: 所有用户故事都依赖的核心基础设施

**⚠️ 关键**: 此阶段必须完成后才能开始用户故事实现

- [X] T004 扩展 VectorIndex SQLAlchemy 模型，添加 embedding_result_id 等新字段 `backend/src/models/vector_index.py`
- [X] T005 [P] 创建 Milvus Provider 实现 `backend/src/services/providers/milvus_provider.py`
- [X] T006 [P] 完善 FAISS Provider 实现，确保符合 BaseProvider 接口 `backend/src/services/providers/faiss_provider.py`
- [X] T007 扩展 IndexRegistry 支持多 Provider 注册和获取 `backend/src/services/index_registry.py`
- [X] T008 添加向量化任务查询 API 端点 `backend/src/api/vector_index.py` (GET /embedding-tasks)
- [X] T009 [P] 扩展前端 API 服务，添加新端点支持 `frontend/src/services/vectorIndexApi.js`
- [X] T010 [P] 扩展 Pinia Store，添加向量化任务和配置状态 `frontend/src/stores/vectorIndexStore.js`
- [X] T010a [P] 添加索引操作日志记录工具 `backend/src/utils/index_logging.py`
  - 记录索引创建、更新、删除、查询等关键操作
  - 日志格式：时间戳、操作类型、索引ID、用户ID、耗时、结果状态

**Checkpoint**: 基础设施就绪 - 可以开始用户故事实现

---

## Phase 3: User Story 1 - 向量数据索引构建 (Priority: P1) 🎯 MVP

**Goal**: 用户可以从已完成的向量化任务创建向量索引

**Independent Test**: 选择一个向量化任务，创建 FAISS/Milvus 索引，验证向量数量和索引状态

### Implementation for User Story 1

- [X] T011 [US1] 实现从向量化任务创建索引的服务方法 `backend/src/services/vector_index_service.py` (create_index_from_embedding)
- [X] T012 [US1] 实现向量数据加载和批量插入逻辑 `backend/src/services/vector_index_service.py` (load_embedding_vectors, batch_insert)
- [X] T013 [US1] 添加从向量化任务创建索引的 API 端点 `backend/src/api/vector_index.py` (POST /indexes/from-embedding)
- [X] T014 [US1] 实现索引构建状态跟踪和更新 `backend/src/services/vector_index_service.py` (update_index_status)
- [X] T015 [US1] 添加索引构建的错误处理和回滚逻辑 `backend/src/services/vector_index_service.py`
  - 边界情况处理：
    1. 向量维度与索引定义不匹配 → 返回 `DIMENSION_MISMATCH` 错误
    2. 索引为空时执行查询 → 返回空结果集，不报错
    3. K 值大于向量总数 → 返回所有可用向量
    4. 磁盘空间不足 → 返回 `STORAGE_FULL` 错误，回滚未完成操作
    5. 向量数据包含 NaN/Inf → 拒绝该向量，返回 `INVALID_VECTOR` 错误
    6. 删除不存在的向量 ID → 静默忽略，返回实际删除数量
    7. 并发修改冲突 → 返回 `CONCURRENT_MODIFICATION` 错误

**Checkpoint**: 用户故事 1 完成 - 可以独立测试索引构建功能

---

## Phase 4: User Story 2 - 向量相似度检索 (Priority: P1) 🎯 MVP

**Goal**: 用户可以对已创建的索引执行 TopK 相似度搜索

**Independent Test**: 向索引提交查询向量，验证返回 TopK 结果，检查延迟 <100ms

### Implementation for User Story 2

- [X] T016 [US2] 实现向量搜索服务方法 `backend/src/services/vector_index_service.py` (search_vectors)
- [X] T017 [US2] 实现相似度阈值过滤逻辑 `backend/src/services/vector_index_service.py`
- [X] T018 [US2] 添加搜索 API 端点 `backend/src/api/vector_index.py` (POST /indexes/{name}/search)
- [X] T019 [US2] 实现批量搜索支持 `backend/src/services/vector_index_service.py` (batch_search)
- [X] T020 [US2] 添加批量搜索 API 端点 `backend/src/api/vector_index.py` (POST /indexes/{name}/batch-search)
- [X] T021 [US2] 实现查询历史记录 `backend/src/services/vector_index_service.py` (log_query_history)

**Checkpoint**: 用户故事 2 完成 - 可以独立测试相似度检索功能

---

## Phase 5: User Story 6 - 前端索引管理界面 (Priority: P1) 🎯 MVP

**Goal**: 用户通过 Web 界面完成索引创建和管理

**Independent Test**: 访问向量索引页面，选择向量化任务，创建索引，查看结果和历史记录

### Implementation for User Story 6

- [X] T022 [P] [US6] 创建向量化任务选择器组件 `frontend/src/components/VectorIndex/VectorTaskSelector.vue` (集成到 IndexCreate.vue)
- [X] T023 [P] [US6] 创建数据库选择器组件 `frontend/src/components/VectorIndex/DatabaseSelector.vue` (集成到 IndexCreate.vue)
- [X] T024 [P] [US6] 创建算法选择器组件 `frontend/src/components/VectorIndex/AlgorithmSelector.vue` (集成到 IndexCreate.vue)
- [X] T025 [P] [US6] 创建索引配置面板组件 `frontend/src/components/VectorIndex/IndexConfigPanel.vue` (集成到 IndexCreate.vue)
- [X] T026 [P] [US6] 创建索引结果卡片组件 `frontend/src/components/VectorIndex/IndexResultCard.vue` (集成到 IndexList.vue)
- [ ] T027 [P] [US6] 创建历史记录列表组件 `frontend/src/components/VectorIndex/IndexHistoryList.vue`
- [X] T028 [US6] 重构主页面，实现左右分栏布局 `frontend/src/views/VectorIndex.vue`
- [X] T029 [US6] 实现索引创建流程和状态管理 `frontend/src/stores/vectorIndexStore.js` (createIndex action)
- [X] T030 [US6] 实现历史记录加载和删除功能 `frontend/src/stores/vectorIndexStore.js` (fetchHistory, deleteIndex actions)
- [X] T031 [US6] 添加加载状态、错误提示和用户反馈 `frontend/src/views/VectorIndex.vue`

**Checkpoint**: 用户故事 6 完成 - 前端界面可独立测试

---

## Phase 6: User Story 3 - 索引更新与删除 (Priority: P2)

**Goal**: 用户可以向现有索引添加、更新、删除向量

**Independent Test**: 向索引添加新向量，删除指定向量，验证检索结果更新

### Implementation for User Story 3

- [X] T032 [US3] 实现向量添加服务方法 `backend/src/services/vector_index_service.py` (add_vectors)
- [X] T033 [US3] 实现向量删除服务方法 `backend/src/services/vector_index_service.py` (delete_vectors)
- [X] T034 [US3] 实现向量更新服务方法 `backend/src/services/vector_index_service.py` (update_vector)
- [X] T035 [US3] 添加向量 CRUD API 端点 `backend/src/api/vector_index.py` (POST/DELETE /indexes/{name}/vectors)
- [ ] T036 [US3] 实现并发控制（读写锁）`backend/src/services/vector_index_service.py`
  - 支持 10 并发读操作
  - 支持 1 并发写操作（写时阻塞读）
  - 锁等待超时：5 秒
  - 使用 `asyncio.Lock` 或 `threading.RWLock` 实现

**Checkpoint**: 用户故事 3 完成 - 索引更新功能可独立测试

---

## Phase 7: User Story 4 - 索引持久化与恢复 (Priority: P2)

**Goal**: 索引数据可持久化到磁盘，系统重启后自动恢复

**Independent Test**: 创建索引，重启服务，验证索引自动加载并可用

### Implementation for User Story 4

- [X] T037 [US4] 实现 FAISS 索引持久化 `backend/src/services/providers/faiss_provider.py` (persist_index, load_index)
- [X] T038 [US4] 实现 Milvus 索引 flush 和恢复 `backend/src/services/providers/milvus_provider.py` (flush, recover)
- [X] T039 [US4] 添加持久化 API 端点 `backend/src/api/vector_index.py` (POST /indexes/{name}/persist)
- [ ] T040 [US4] 实现服务启动时自动加载索引 `backend/src/main.py` (lifespan startup)
- [ ] T041 [US4] 实现定时自动持久化 `backend/src/services/vector_index_service.py` (auto_persist_scheduler)

**Checkpoint**: 用户故事 4 完成 - 持久化功能可独立测试

---

## Phase 8: User Story 5 - 多索引管理 (Priority: P3)

**Goal**: 支持创建和管理多个独立索引

**Independent Test**: 创建 3 个不同索引，分别查询，验证隔离性

### Implementation for User Story 5

- [X] T042 [US5] 实现多索引列表查询 `backend/src/services/vector_index_service.py` (list_indexes)
- [X] T043 [US5] 实现索引删除（包含数据清理）`backend/src/services/vector_index_service.py` (delete_index)
- [ ] T044 [US5] 实现跨索引搜索 `backend/src/services/vector_index_service.py` (cross_index_search)
- [X] T045 [US5] 添加索引列表和删除 API 端点 `backend/src/api/vector_index.py` (GET/DELETE /indexes)
- [X] T046 [US5] 实现索引统计信息查询 `backend/src/services/vector_index_service.py` (get_index_stats)
- [X] T047 [US5] 添加统计信息 API 端点 `backend/src/api/vector_index.py` (GET /indexes/{name}/stats)

**Checkpoint**: 用户故事 5 完成 - 多索引管理可独立测试

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: 跨用户故事的优化和完善

- [ ] T048 [P] 实现索引导出功能 `backend/src/services/vector_index_service.py` (export_index)
- [ ] T049 [P] 实现索引导入功能 `backend/src/services/vector_index_service.py` (import_index)
- [ ] T050 添加导出/导入 API 端点 `backend/src/api/vector_index.py`
- [ ] T051 [P] 前端添加索引导出/导入 UI `frontend/src/views/VectorIndex.vue`
- [ ] T052 运行 quickstart.md 验证

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: 无依赖 - 可立即开始
- **Foundational (Phase 2)**: 依赖 Setup 完成 - **阻塞所有用户故事**
- **User Stories (Phase 3-8)**: 全部依赖 Foundational 完成
  - US1 (索引构建) → US2 (检索) → US6 (前端) 建议顺序执行
  - US3 (更新) 和 US4 (持久化) 可并行
  - US5 (多索引) 依赖 US1-US4 完成
- **Polish (Phase 9)**: 依赖所有用户故事完成

### User Story Dependencies

```
Phase 2 (Foundational)
    ↓
┌───────────────────────────────────────┐
│  US1 (索引构建) ─────────────────────→│
│       ↓                               │
│  US2 (检索) ─────────────────────────→│ MVP
│       ↓                               │
│  US6 (前端界面) ─────────────────────→│
└───────────────────────────────────────┘
    ↓
┌─────────────┬─────────────┐
│ US3 (更新)  │ US4 (持久化) │ 可并行
└─────────────┴─────────────┘
    ↓
US5 (多索引管理)
    ↓
Phase 9 (Polish)
```

### Within Each User Story

- 后端服务方法 → API 端点 → 前端组件
- 核心功能 → 错误处理 → 日志记录

### Parallel Opportunities

- Phase 1: T002, T003 可并行
- Phase 2: T005, T006, T009, T010 可并行
- Phase 5: T022-T027 所有前端组件可并行创建
- Phase 9: T048, T049, T050, T052 可并行

---

## Parallel Example: User Story 6 (前端)

```bash
# 并行创建所有前端组件：
Task: "创建向量化任务选择器组件 frontend/src/components/VectorIndex/VectorTaskSelector.vue"
Task: "创建数据库选择器组件 frontend/src/components/VectorIndex/DatabaseSelector.vue"
Task: "创建算法选择器组件 frontend/src/components/VectorIndex/AlgorithmSelector.vue"
Task: "创建索引配置面板组件 frontend/src/components/VectorIndex/IndexConfigPanel.vue"
Task: "创建索引结果卡片组件 frontend/src/components/VectorIndex/IndexResultCard.vue"
Task: "创建历史记录列表组件 frontend/src/components/VectorIndex/IndexHistoryList.vue"

# 组件完成后，顺序执行：
Task: "重构主页面 frontend/src/views/VectorIndex.vue"
Task: "实现 Store actions frontend/src/stores/vectorIndexStore.js"
```

---

## Implementation Strategy

### MVP First (仅 User Story 1, 2, 6)

1. 完成 Phase 1: Setup
2. 完成 Phase 2: Foundational (**关键 - 阻塞后续**)
3. 完成 Phase 3: User Story 1 (索引构建)
4. **STOP and VALIDATE**: 测试索引创建功能
5. 完成 Phase 4: User Story 2 (检索)
6. **STOP and VALIDATE**: 测试检索功能
7. 完成 Phase 5: User Story 6 (前端)
8. **STOP and VALIDATE**: 端到端测试
9. **Deploy/Demo MVP!**

### Incremental Delivery

1. Setup + Foundational → 基础就绪
2. 添加 US1 → 测试 → (可选 Demo)
3. 添加 US2 → 测试 → (可选 Demo)
4. 添加 US6 → 测试 → **MVP 发布**
5. 添加 US3 → 测试 → 增量发布
6. 添加 US4 → 测试 → 增量发布
7. 添加 US5 → 测试 → 增量发布
8. Polish → 最终发布

### Parallel Team Strategy

如有多个开发者：

1. 团队共同完成 Setup + Foundational
2. Foundational 完成后：
   - 开发者 A: US1 (后端索引构建)
   - 开发者 B: US6 前端组件 (T022-T027)
3. US1 完成后：
   - 开发者 A: US2 (后端检索)
   - 开发者 B: 继续 US6 (T028-T031)
4. 后续故事可并行分配

---

## Notes

- [P] 任务 = 不同文件，无依赖，可并行
- [Story] 标签将任务映射到特定用户故事
- 每个用户故事应可独立完成和测试
- 每个任务或逻辑组完成后提交
- 在任何检查点停止以独立验证故事
- 避免：模糊任务、同文件冲突、破坏独立性的跨故事依赖

---

## Summary

| Metric | Value |
|--------|-------|
| **Total Tasks** | 52 |
| **Setup Tasks** | 3 |
| **Foundational Tasks** | 8 |
| **US1 Tasks** | 5 |
| **US2 Tasks** | 6 |
| **US6 Tasks** | 10 |
| **US3 Tasks** | 5 |
| **US4 Tasks** | 5 |
| **US5 Tasks** | 6 |
| **Polish Tasks** | 5 |
| **Parallel Opportunities** | 17 tasks marked [P] |
| **MVP Scope** | US1 + US2 + US6 (21 tasks) |
