# Tasks: 搜索查询功能

**Input**: Design documents from `/specs/005-search-query/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/search-api.yaml ✅

**Tests**: 未明确要求测试，本任务列表不包含测试任务。

**Organization**: 任务按用户故事分组，支持独立实现和测试。

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 可并行执行（不同文件，无依赖）
- **[Story]**: 所属用户故事（US1-US5）
- 包含精确文件路径

---

## Phase 1: Setup (项目初始化)

**Purpose**: 创建搜索查询模块的基础结构

- [x] T001 创建后端搜索模块目录结构 `backend/src/api/search.py`, `backend/src/services/search_service.py`, `backend/src/models/search.py`, `backend/src/schemas/search.py`
- [x] T002 [P] 创建前端搜索模块目录结构 `frontend/src/views/Search.vue`, `frontend/src/components/Search/`, `frontend/src/services/searchApi.js`, `frontend/src/stores/searchStore.js`
- [x] T003 [P] 添加前端路由配置 `frontend/src/router/index.js` 添加 `/search` 路由

---

## Phase 2: Foundational (基础设施)

**Purpose**: 核心基础设施，所有用户故事依赖此阶段

**⚠️ CRITICAL**: 此阶段完成前不能开始任何用户故事

- [x] T004 创建搜索数据模型 `backend/src/models/search.py` - 包含 SearchHistory, SearchConfig 实体
- [x] T005 [P] 创建 Pydantic Schemas `backend/src/schemas/search.py` - 包含 SearchRequest, SearchResponse, SearchResultItem 等
- [x] T006 [P] 创建数据库迁移脚本 `migrations/006_search_history.sql` - 创建 search_history 和 search_config 表
- [x] T007 创建搜索服务基础类 `backend/src/services/search_service.py` - 定义 SearchService 类骨架
- [x] T008 [P] 创建前端 API 服务 `frontend/src/services/searchApi.js` - 定义所有 API 调用方法
- [x] T009 [P] 创建 Pinia Store `frontend/src/stores/searchStore.js` - 定义状态管理

**Checkpoint**: 基础设施就绪 - 可以开始用户故事实现 ✅

---

## Phase 3: User Story 1 - 语义搜索查询 (Priority: P1) 🎯 MVP

**Goal**: 用户输入自然语言查询，系统返回相关文档片段列表

**Independent Test**: 输入"什么是向量数据库？"，验证返回相关文档片段，检查相似度评分

### Implementation for User Story 1

- [x] T010 [US1] 实现查询向量化逻辑 `backend/src/services/search_service.py` - 调用 EmbeddingService 将查询文本转为向量
- [x] T011 [US1] 实现向量检索逻辑 `backend/src/services/search_service.py` - 调用 VectorIndexService 执行相似度检索
- [x] T012 [US1] 实现搜索结果处理 `backend/src/services/search_service.py` - 结果排序、摘要生成、格式化
- [x] T013 [US1] 实现搜索 API 端点 `backend/src/api/search.py` - POST /api/v1/search 端点
- [x] T014 [P] [US1] 注册搜索路由 `backend/src/main.py` - 添加 search router
- [x] T015 [P] [US1] 创建搜索输入组件 `frontend/src/components/Search/SearchInput.vue` - 搜索框 + 按钮
- [x] T016 [US1] 创建搜索主页面 `frontend/src/views/Search.vue` - 页面布局框架
- [x] T017 [US1] 实现搜索状态管理 `frontend/src/stores/searchStore.js` - search action, loading 状态
- [x] T018 [US1] 实现搜索 API 调用 `frontend/src/services/searchApi.js` - executeSearch 方法
- [x] T019 [US1] 添加错误处理 `backend/src/services/search_service.py` - 空查询、服务超时、索引不存在等

**Checkpoint**: 用户故事 1 完成 - 可独立测试基础搜索功能 ✅

---

## Phase 4: User Story 2 - 搜索结果展示与交互 (Priority: P1)

**Goal**: 搜索结果以卡片列表展示，支持查看详情

**Independent Test**: 执行搜索后验证结果卡片显示所有必要信息，点击操作正常响应

### Implementation for User Story 2

- [x] T020 [P] [US2] 创建结果卡片组件 `frontend/src/components/Search/ResultCard.vue` - 显示摘要、分数、来源
- [x] T021 [P] [US2] 创建结果列表组件 `frontend/src/components/Search/SearchResults.vue` - 卡片列表容器
- [x] T022 [P] [US2] 创建结果详情弹窗 `frontend/src/components/Search/ResultDetail.vue` - 完整内容展示
- [x] T023 [US2] 集成结果展示到主页面 `frontend/src/views/Search.vue` - 添加 SearchResults 组件
- [x] T024 [US2] 实现分页/无限滚动 `frontend/src/components/Search/SearchResults.vue` - 滚动加载更多
- [x] T025 [US2] 添加加载状态和空结果提示 `frontend/src/views/Search.vue` - loading spinner, empty state

**Checkpoint**: 用户故事 2 完成 - 搜索结果展示功能可独立测试 ✅

---

## Phase 5: User Story 3 - 搜索配置与过滤 (Priority: P2)

**Goal**: 用户可配置 TopK、相似度阈值、相似度方法、目标索引

**Independent Test**: 修改配置参数后执行搜索，验证结果符合配置预期

### Implementation for User Story 3

- [x] T026 [US3] 实现获取可用索引 API `backend/src/api/search.py` - GET /api/v1/search/indexes 端点
- [x] T027 [P] [US3] 创建配置面板组件 `frontend/src/components/Search/SearchConfig.vue` - 索引选择、TopK、阈值、方法
- [x] T028 [US3] 实现配置状态管理 `frontend/src/stores/searchStore.js` - config state, updateConfig action
- [x] T029 [US3] 集成配置面板到主页面 `frontend/src/views/Search.vue` - 左侧配置面板布局
- [x] T030 [US3] 实现索引列表 API 调用 `frontend/src/services/searchApi.js` - getAvailableIndexes 方法
- [x] T031 [US3] 搜索请求携带配置参数 `frontend/src/stores/searchStore.js` - 将配置参数传递给搜索 API

**Checkpoint**: 用户故事 3 完成 - 搜索配置功能可独立测试 ✅

---

## Phase 6: User Story 4 - 搜索历史记录 (Priority: P2)

**Goal**: 系统记录搜索历史，用户可查看、重新执行、清除历史

**Independent Test**: 执行多次搜索后验证历史记录正确保存，点击历史记录能重新执行搜索

### Implementation for User Story 4

- [x] T032 [US4] 实现历史记录保存 `backend/src/services/search_service.py` - 搜索完成后自动保存历史
- [x] T033 [US4] 实现历史记录数量限制 `backend/src/services/search_service.py` - 超过50条自动删除最旧记录
- [x] T034 [US4] 实现获取历史 API `backend/src/api/search.py` - GET /api/v1/search/history 端点
- [x] T035 [US4] 实现删除单条历史 API `backend/src/api/search.py` - DELETE /api/v1/search/history/{id} 端点
- [x] T036 [US4] 实现清空历史 API `backend/src/api/search.py` - DELETE /api/v1/search/history 端点
- [x] T037 [P] [US4] 创建历史记录组件 `frontend/src/components/Search/SearchHistory.vue` - 历史列表展示
- [x] T038 [US4] 实现历史记录状态管理 `frontend/src/stores/searchStore.js` - history state, loadHistory action
- [x] T039 [US4] 实现历史 API 调用 `frontend/src/services/searchApi.js` - getHistory, deleteHistory, clearHistory 方法
- [x] T040 [US4] 集成历史记录到主页面 `frontend/src/views/Search.vue` - Tab 切换（搜索结果 | 历史记录）
- [x] T041 [US4] 实现点击历史快速搜索 `frontend/src/components/Search/SearchHistory.vue` - 点击记录填充查询框并执行

**Checkpoint**: 用户故事 4 完成 - 搜索历史功能可独立测试 ✅

---

## Phase 7: User Story 5 - 多索引联合搜索 (Priority: P3)

**Goal**: 用户可选择多个索引进行联合搜索，结果合并排序

**Independent Test**: 选择多个索引执行搜索，验证结果来自所有选中索引，排序正确

### Implementation for User Story 5

- [x] T042 [US5] 实现多索引检索逻辑 `backend/src/services/search_service.py` - 并行检索多个索引
- [x] T043 [US5] 实现结果合并排序 `backend/src/services/search_service.py` - 合并各索引结果，按相似度统一排序
- [x] T044 [US5] 更新配置面板支持多选 `frontend/src/components/Search/SearchConfig.vue` - 索引多选功能
- [x] T045 [US5] 结果卡片显示来源索引 `frontend/src/components/Search/ResultCard.vue` - 添加来源索引标签
- [x] T046 [US5] 更新状态管理支持多索引 `frontend/src/stores/searchStore.js` - selectedIndexes 数组

**Checkpoint**: 用户故事 5 完成 - 多索引联合搜索功能可独立测试 ✅

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: 跨用户故事的优化和完善

- [x] T047 [P] 添加搜索页面导航菜单项 `frontend/src/components/Layout/` - 侧边栏添加搜索入口（已存在）
- [x] T048 [P] 统一界面样式 `frontend/src/views/Search.vue` - 与现有模块保持一致的 TDesign 风格
- [x] T049 添加日志记录 `backend/src/services/search_service.py` - 搜索请求、耗时、错误日志
- [x] T050 性能优化 `backend/src/services/search_service.py` - 超时设置、并发控制
- [x] T051 运行 quickstart.md 验证 - 验证所有场景正常工作

---

## Implementation Status

**完成时间**: 2025-12-25

| 阶段 | 状态 | 完成任务 |
|------|------|----------|
| Phase 1: Setup | ✅ 完成 | 3/3 |
| Phase 2: Foundational | ✅ 完成 | 6/6 |
| Phase 3: US1 语义搜索 | ✅ 完成 | 10/10 |
| Phase 4: US2 结果展示 | ✅ 完成 | 6/6 |
| Phase 5: US3 配置过滤 | ✅ 完成 | 6/6 |
| Phase 6: US4 历史记录 | ✅ 完成 | 10/10 |
| Phase 7: US5 多索引 | ✅ 完成 | 5/5 |
| Phase 8: Polish | ✅ 完成 | 5/5 |

**总进度**: 51/51 任务完成 (100%)

---

## Created Files

### Backend
- `backend/src/api/search.py` - 搜索 API 路由
- `backend/src/models/search.py` - 搜索数据模型
- `backend/src/schemas/search.py` - Pydantic Schemas
- `backend/src/services/search_service.py` - 搜索服务
- `migrations/006_search_history.sql` - 数据库迁移脚本

### Frontend
- `frontend/src/views/Search.vue` - 搜索主页面
- `frontend/src/components/Search/SearchInput.vue` - 搜索输入组件
- `frontend/src/components/Search/SearchConfig.vue` - 配置面板组件
- `frontend/src/components/Search/SearchResults.vue` - 结果列表组件
- `frontend/src/components/Search/ResultCard.vue` - 结果卡片组件
- `frontend/src/components/Search/ResultDetail.vue` - 结果详情弹窗
- `frontend/src/components/Search/SearchHistory.vue` - 历史记录组件
- `frontend/src/services/searchApi.js` - API 服务
- `frontend/src/stores/searchStore.js` - Pinia Store

### Modified Files
- `backend/src/main.py` - 注册搜索路由
- `backend/src/models/__init__.py` - 导出搜索模型
