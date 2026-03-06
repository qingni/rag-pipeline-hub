# Tasks: 文档向量化功能优化

**Input**: Design documents from `/specs/003-vector-embedding-opt/`  
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, quickstart.md ✅

**Tests**: 本功能规格未明确要求测试，测试任务为可选。

**Organization**: 任务按用户故事分组，支持独立实现和测试每个故事。

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 可并行执行（不同文件，无依赖）
- **[Story]**: 任务所属的用户故事（如 US1, US2, US3）
- 描述中包含确切的文件路径

## Path Conventions

- **后端**: `backend/src/`
- **前端**: `frontend/src/`
- **测试**: `backend/tests/`, `frontend/tests/`

---

## Phase 1: Setup (共享基础设施)

**Purpose**: 项目初始化和基础结构配置

- [x] T001 添加新依赖到 `backend/requirements.txt`（langdetect>=1.0.9, scikit-learn>=1.3.0, pyyaml>=6.0）
- [x] T002 添加新依赖到 `frontend/package.json`（echarts>=5.4.0）
- [x] T003 [P] 创建模型能力预置配置文件 `backend/src/config/model_capabilities.yaml`
- [x] T004 [P] 更新数据库迁移脚本 `backend/src/database/migrations/` 添加新表和字段

---

## Phase 2: Foundational (阻塞性前置任务)

**Purpose**: 核心基础设施，所有用户故事都依赖这些任务

**⚠️ 关键**: 在完成此阶段之前，不能开始任何用户故事的工作

### 数据模型扩展

- [x] T005 [P] 扩展 `backend/src/models/embedding_task.py` 添加 config 和 progress 字段
- [x] T006 [P] 扩展 `backend/src/models/embedding_result.py` 添加 statistics 扩展字段和 is_active 字段
- [x] T007 [P] 创建缓存实体模型 `backend/src/models/vector_cache.py`
- [x] T008 [P] 创建文档特征实体模型 `backend/src/models/document_features.py`
- [x] T009 [P] 创建模型能力配置实体 `backend/src/models/model_capability.py`
- [x] T010 [P] 创建推荐结果实体 `backend/src/models/model_recommendation.py`

### 工具类

- [x] T011 [P] 扩展重试处理器 `backend/src/utils/retry_handler.py` 实现指数退避重试
- [x] T012 [P] 创建速率限制器 `backend/src/utils/rate_limiter.py` 实现自适应限流
- [x] T013 [P] 创建语言检测工具 `backend/src/utils/language_detector.py`
- [x] T014 [P] 创建领域分类工具 `backend/src/utils/domain_classifier.py`

### 基础服务

- [x] T015 [P] 创建内容哈希服务 `backend/src/services/content_hash_service.py`

**Checkpoint**: 基础设施就绪 - 可以开始用户故事实现

---

## Phase 3: User Story 1 - 多模态内容向量化 (Priority: P1) 🎯 MVP

**Goal**: 支持图片和表格的智能向量化，多模态模型优先，失败时降级为文本

**Independent Test**: 对包含图片和表格的分块结果进行向量化，验证不同类型内容的向量化策略是否正确应用

### Implementation for User Story 1

- [x] T016 [P] [US1] 创建多模态向量化器基类 `backend/src/providers/embedders/base_embedder.py` 扩展批量处理接口
- [x] T017 [US1] 创建多模态向量化器 `backend/src/providers/embedders/multimodal_embedder.py` 实现图片 base64 和 caption 降级
- [x] T018 [US1] 扩展嵌入服务 `backend/src/services/embedding_service.py` 添加多模态分块处理逻辑（根据 chunk_type 选择策略）
- [x] T019 [US1] 扩展向量化 API `backend/src/api/embedding.py` 支持多模态配置参数

**Checkpoint**: User Story 1 完成 - 多模态内容可正确向量化，图片降级机制生效

---

## Phase 4: User Story 2 - 批量向量化性能优化 (Priority: P1)

**Goal**: 支持并发处理、可配置批量大小、指数退避重试、部分成功返回

**Independent Test**: 对不同规模的分块结果进行向量化，验证并发控制、批量处理、重试机制是否正常工作

### Implementation for User Story 2

- [x] T020 [P] [US2] 创建批量处理器 `backend/src/providers/embedders/batch_embedder.py` 实现并发控制和批量分组
- [x] T021 [US2] 实现批量向量化服务逻辑 `backend/src/services/embedding_service.py` 添加并发处理和重试机制
- [x] T022 [US2] 扩展 API 支持批量配置 `backend/src/api/embedding.py` 添加 batch_size、concurrency 参数
- [x] T023 [US2] 实现部分成功返回逻辑 `backend/src/services/embedding_service.py` 处理批次失败后继续处理

**Checkpoint**: User Story 2 完成 - 批量向量化高效稳定，重试机制生效

---

## Phase 5: User Story 3 - 向量化进度实时反馈 (Priority: P1)

**Goal**: 实时推送处理进度，前端展示进度条和状态信息

**Independent Test**: 触发向量化操作，验证前端是否实时更新进度信息，进度数据是否准确

### Implementation for User Story 3

- [x] T024 [P] [US3] 创建进度跟踪服务 `backend/src/services/embedding_progress_service.py`
- [x] T025 [US3] 创建进度推送 API `backend/src/api/embedding_progress.py` 实现 SSE 实时推送
- [x] T026 [US3] 扩展任务状态查询 API `backend/src/api/embedding.py` 添加任务取消功能
- [x] T027 [P] [US3] 创建前端进度条组件 `frontend/src/components/embedding/EmbeddingProgress.vue`
- [x] T028 [US3] 创建前端 WebSocket/SSE 进度服务 `frontend/src/services/embeddingProgressService.js`
- [x] T029 [US3] 扩展前端状态管理 `frontend/src/stores/embeddingStore.js` 添加进度和取消状态

**Checkpoint**: User Story 3 完成 - 进度实时反馈，前端展示准确

---

## Phase 6: User Story 8 - 智能嵌入模型推荐 (Priority: P1) 🎯 关键优化

**Goal**: 基于文档内容特征（语言、领域、多模态比例）自动推荐最适合的嵌入模型

**Independent Test**: 上传不同类型文档（中文技术文档、英文商业文档、多模态文档），验证系统推荐结果是否合理

### Implementation for User Story 8

- [x] T030 [P] [US8] 创建文档特征分析服务 `backend/src/services/document_feature_service.py` 实现语言检测和领域分类
- [x] T031 [US8] 创建模型能力管理服务 `backend/src/services/model_capability_service.py` 加载预置配置
- [x] T032 [US8] 创建智能推荐引擎服务 `backend/src/services/model_recommend_service.py` 实现加权评分算法
- [x] T033 [US8] 创建推荐 API `backend/src/api/embedding_recommend.py` 提供特征分析和推荐接口
- [x] T034 [P] [US8] 创建前端推荐卡片组件 `frontend/src/components/embedding/ModelRecommendCard.vue`
- [x] T035 [P] [US8] 创建前端雷达图组件 `frontend/src/components/embedding/FeatureRadarChart.vue` 使用 ECharts
- [x] T036 [US8] 创建前端推荐服务 `frontend/src/services/modelRecommendService.js`
- [x] T037 [US8] 创建前端推荐状态管理 `frontend/src/stores/modelRecommendStore.js`
- [x] T038 [US8] 集成推荐组件到文档向量化页面 `frontend/src/views/DocumentEmbed.vue`

**Checkpoint**: User Story 8 完成 - 智能推荐准确，推荐卡片和雷达图展示正确

---

## Phase 7: User Story 9 - 批量文档智能推荐 (Priority: P1)

**Goal**: 批量添加文档时分析综合特征，提供统一推荐并标注异常文档

**Independent Test**: 批量上传特征相似和特征差异较大的文档组合，验证推荐和异常标注功能

### Implementation for User Story 9

- [x] T039 [US9] 扩展推荐服务 `backend/src/services/model_recommend_service.py` 添加批量推荐和异常检测逻辑
- [x] T040 [US9] 扩展推荐 API `backend/src/api/embedding_recommend.py` 添加批量推荐端点
- [x] T041 [P] [US9] 创建前端异常文档列表组件 `frontend/src/components/embedding/OutlierDocumentList.vue`
- [x] T042 [US9] 扩展推荐卡片组件 `frontend/src/components/embedding/ModelRecommendCard.vue` 支持批量特征摘要展示

**Checkpoint**: User Story 9 完成 - 批量推荐准确，异常文档正确标注

---

## Phase 8: User Story 4 - 增量向量化 (Priority: P2)

**Goal**: 文档重新分块后，仅对新增或变更的分块进行向量化

**Independent Test**: 对同一文档进行两次分块和向量化，验证第二次是否正确跳过未变化的分块

### Implementation for User Story 4

- [x] T043 [US4] 扩展嵌入服务 `backend/src/services/embedding_service.py` 添加增量检测逻辑（基于内容哈希）
- [x] T044 [US4] 实现变更分块识别 `backend/src/services/embedding_service.py` 复用未变化分块的向量
- [x] T045 [US4] 扩展 API 支持增量模式 `backend/src/api/embedding.py` 添加 incremental 和 force_recompute 参数
- [x] T046 [US4] 前端增量模式配置 `frontend/src/components/embedding/EmbeddingConfig.vue` 添加增量选项

**Checkpoint**: User Story 4 完成 - 增量向量化正确识别变更，跳过未变化分块

---

## Phase 9: User Story 5 - 向量缓存机制 (Priority: P2)

**Goal**: 基于内容哈希的缓存机制，相同内容不重复计算向量

**Independent Test**: 对包含重复内容的分块进行向量化，验证第二次是否命中缓存

### Implementation for User Story 5

- [x] T047 [P] [US5] 创建缓存服务 `backend/src/services/embedding_cache_service.py` 实现 LRU 缓存和 Redis 支持
- [x] T048 [US5] 创建缓存装饰器 `backend/src/providers/embedders/cached_embedder.py` 封装缓存逻辑
- [x] T049 [US5] 创建缓存管理 API `backend/src/api/embedding_cache.py` 提供查询、清除接口
- [x] T050 [P] [US5] 创建前端缓存状态组件 `frontend/src/components/embedding/CacheStatus.vue`
- [x] T051 [US5] 前端展示缓存命中率 `frontend/src/views/DocumentEmbed.vue` 集成缓存统计

**Checkpoint**: User Story 5 完成 - 缓存命中正确，LRU 淘汰生效

---

## Phase 10: User Story 6 - 多模型切换与对比 (Priority: P2)

**Goal**: 方便切换向量化模型，并对比不同模型的向量化结果

**Independent Test**: 使用不同模型对同一文档进行向量化，验证对比功能是否正确展示差异

### Implementation for User Story 6

- [x] T052 [US6] 扩展结果管理服务 `backend/src/services/embedding_service.py` 支持多结果保存和活跃状态
- [x] T053 [US6] 创建对比 API `backend/src/api/embedding.py` 添加 compare 和 activate 端点
- [x] T054 [P] [US6] 创建前端模型对比组件 `frontend/src/components/embedding/ModelComparison.vue`
- [x] T055 [US6] 前端对比功能集成 `frontend/src/views/DocumentEmbed.vue` 支持多结果管理
- [x] T055.1 [US6] 扩展结果删除功能 `backend/src/api/embedding.py` 添加 delete 端点（仅允许删除非活跃结果）
- [x] T055.2 [P] [US6] 前端删除按钮 `frontend/src/views/DocumentEmbed.vue` 在结果列表中支持删除非活跃结果

**Checkpoint**: User Story 6 完成 - 模型对比清晰，活跃结果切换正确，非活跃结果可删除

---

## Phase 11: User Story 10 - 模型能力配置管理 (Priority: P2)

**Goal**: 管理员可查看和调整系统预置的模型能力特征配置

**Independent Test**: 通过管理界面修改某模型的能力评分，验证推荐结果是否相应变化

### Implementation for User Story 10

- [x] T056 [US10] 扩展模型能力服务 `backend/src/services/model_capability_service.py` 支持 CRUD 操作
- [x] T057 [US10] 创建能力管理 API `backend/src/api/embedding_recommend.py` 添加模型能力管理端点
- [x] T058 [P] [US10] 创建前端模型能力管理组件 `frontend/src/components/embedding/ModelCapabilityManager.vue`
- [x] T059 [US10] 创建前端管理员配置页面 `frontend/src/views/ModelCapabilityAdmin.vue`
- [x] T060 [US10] 添加路由和导航 `frontend/src/router/` 配置管理页面入口

**Checkpoint**: User Story 10 完成 - 模型能力可配置，推荐结果随配置变化

---

## Phase 12: User Story 7 - 向量化结果可视化 (Priority: P3)

**Goal**: 直观查看向量化结果，包括统计图表和详细信息

**Independent Test**: 完成向量化后查看结果页面，验证统计图表是否正确展示

### Implementation for User Story 7

- [x] T061 [P] [US7] 创建前端统计图表组件 `frontend/src/components/embedding/EmbeddingStatistics.vue` 使用 ECharts
- [x] T062 [US7] 前端结果页面增强 `frontend/src/views/DocumentEmbed.vue` 集成统计图表
- [x] T063 [US7] 前端导出功能 `frontend/src/services/embeddingService.js` 添加 JSON 导出

**Checkpoint**: User Story 7 完成 - 结果可视化清晰，导出功能正常

---

## Phase 13: Polish & Cross-Cutting Concerns

**Purpose**: 影响多个用户故事的改进和优化

- [x] T064 [P] 前端高级配置面板完善 `frontend/src/components/embedding/EmbeddingConfig.vue` 整合所有配置项
- [x] T065 [P] 更新 quickstart.md 文档添加智能推荐示例
- [x] T066 代码清理和重构，确保模块边界清晰
- [x] T067 性能优化：批量处理和缓存效率检查
- [x] T068 [P] 安全加固：API 参数校验和错误处理
- [x] T069 运行 quickstart.md 验证所有功能正常

---

## Phase 14: Hotfix - Contextual Retrieval 批量 LLM 请求优化

**Purpose**: 将 embedding 前 Contextual Retrieval 从逐 chunk LLM 调用切换为批量调用，降低请求数并保证 chunk 对齐。

- [x] T070 [US2] 扩展 `backend/src/services/contextual_retrieval_service.py`：按 batch 请求 LLM，要求结构化返回 `chunk_id + context`，并按 `chunk_id` 回填
- [x] T071 [US2] 扩展配置与接入：更新 `backend/src/config/__init__.py`、`backend/.env.example`、`backend/src/services/embedding_service.py`，新增并启用 `CONTEXTUAL_RETRIEVAL_BATCH_SIZE`（默认 10）
- [x] T072 [US2] 同步规格文档：更新 `specs/003-vector-embedding-opt/spec.md` 与 `specs/003-vector-embedding-opt/plan.md`，补充 Contextual Retrieval 批量请求行为与约束

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Setup)
    │
    ▼
Phase 2 (Foundational) ───────────────────────────────────────┐
    │                                                          │
    ▼                                                          │
┌───────────────────────────────────────────────────────────┐  │
│ P1 User Stories (可并行)                                   │  │
│   Phase 3: US1 - 多模态向量化                              │  │
│   Phase 4: US2 - 批量处理优化                              │  │
│   Phase 5: US3 - 进度实时反馈                              │  │
│   Phase 6: US8 - 智能模型推荐 ◄─── 关键优化                │  │
│   Phase 7: US9 - 批量文档推荐                              │  │
└───────────────────────────────────────────────────────────┘  │
    │                                                          │
    ▼                                                          │
┌───────────────────────────────────────────────────────────┐  │
│ P2 User Stories (可并行)                                   │  │
│   Phase 8: US4 - 增量向量化                                │  │
│   Phase 9: US5 - 向量缓存                                  │  │
│   Phase 10: US6 - 模型对比                                 │  │
│   Phase 11: US10 - 模型能力管理                            │  │
└───────────────────────────────────────────────────────────┘  │
    │                                                          │
    ▼                                                          │
Phase 12 (US7 - 结果可视化) ◄──────────────────────────────────┘
    │
    ▼
Phase 13 (Polish)
```

### User Story Dependencies

| 用户故事 | 优先级 | 依赖 | 说明 |
|----------|--------|------|------|
| US1 多模态向量化 | P1 | Foundational | 可独立实现 |
| US2 批量处理优化 | P1 | Foundational | 可独立实现 |
| US3 进度实时反馈 | P1 | Foundational | 可独立实现 |
| US8 智能模型推荐 | P1 | Foundational | 可独立实现，**关键优化** |
| US9 批量文档推荐 | P1 | US8 | 依赖智能推荐服务 |
| US4 增量向量化 | P2 | T015 | 依赖内容哈希服务（content_hash_service.py），不强制依赖 US5 缓存机制 |
| US5 向量缓存 | P2 | Foundational | 可独立实现 |
| US6 模型对比 | P2 | Foundational | 可独立实现 |
| US10 模型能力管理 | P2 | US8 | 依赖模型能力服务 |
| US7 结果可视化 | P3 | US1-US6 | 依赖前置功能 |

### Parallel Opportunities

**Phase 2 (Foundational)** - 以下任务可并行:
```
T005, T006, T007, T008, T009, T010  (数据模型)
T011, T012, T013, T014              (工具类)
T015                                 (基础服务)
```

**P1 User Stories** - 以下故事可并行实现:
```
US1 (多模态) ─┬─ 不同团队成员可同时进行
US2 (批量)   ─┤
US3 (进度)   ─┤
US8 (推荐)   ─┘
```

**US8 内部并行**:
```
T034 (推荐卡片) ─┬─ 前端组件可并行开发
T035 (雷达图)   ─┘
```

---

## Parallel Example: User Story 8 (智能推荐)

```bash
# 后端服务可按顺序实现:
T030: 文档特征分析服务
T031: 模型能力管理服务
T032: 智能推荐引擎服务
T033: 推荐 API

# 前端组件可并行开发:
Task T034: 推荐卡片组件  ───┬─── 同时进行
Task T035: 雷达图组件    ───┘

# 前端集成:
T036 → T037 → T038 (顺序执行)
```

---

## Implementation Strategy

### MVP First (P1 User Stories)

1. ✅ 完成 Phase 1: Setup
2. ✅ 完成 Phase 2: Foundational（关键 - 阻塞所有故事）
3. ✅ 完成 Phase 3-7: P1 User Stories（重点是 US8 智能推荐）
4. **停止并验证**: 独立测试所有 P1 功能
5. 如果就绪可部署/演示

### Incremental Delivery

1. Setup + Foundational → 基础就绪
2. 添加 US1 (多模态) → 独立测试 → 部署/演示
3. 添加 US2 (批量) → 独立测试 → 部署/演示
4. 添加 US3 (进度) → 独立测试 → 部署/演示
5. 添加 US8+US9 (智能推荐) → 独立测试 → 部署/演示 (**关键优化**)
6. 添加 P2 Stories → 独立测试 → 部署/演示
7. 添加 US7 (可视化) → 最终验证

### Parallel Team Strategy

多开发者情况下:

1. 团队共同完成 Setup + Foundational
2. Foundational 完成后:
   - 开发者 A: US1 多模态 + US2 批量
   - 开发者 B: US3 进度 + US5 缓存
   - 开发者 C: US8 + US9 智能推荐 (**核心优化**)
3. 故事独立完成并集成

---

## Summary

| 阶段 | 任务数 | 并行任务 | 说明 |
|------|--------|----------|------|
| Phase 1: Setup | 4 | 2 | 依赖和配置 |
| Phase 2: Foundational | 11 | 10 | 数据模型和工具类 |
| Phase 3: US1 多模态 | 4 | 1 | P1 |
| Phase 4: US2 批量 | 4 | 1 | P1 |
| Phase 5: US3 进度 | 6 | 2 | P1 |
| Phase 6: US8 推荐 | 9 | 3 | P1 关键优化 |
| Phase 7: US9 批量推荐 | 4 | 1 | P1 |
| Phase 8: US4 增量 | 4 | 0 | P2 |
| Phase 9: US5 缓存 | 5 | 2 | P2 |
| Phase 10: US6 对比 | 4 | 1 | P2 |
| Phase 11: US10 管理 | 5 | 1 | P2 |
| Phase 12: US7 可视化 | 3 | 1 | P3 |
| Phase 13: Polish | 6 | 3 | 收尾 |
| **总计** | **69** | **29** | 42% 可并行 |

---

## Notes

- [P] 任务 = 不同文件，无依赖，可并行
- [Story] 标签将任务映射到具体用户故事，便于追溯
- 每个用户故事应可独立完成和测试
- 每个任务或逻辑组完成后提交
- 在任何检查点停止以独立验证故事
- 避免：模糊任务、同文件冲突、破坏独立性的跨故事依赖
- **US8 (智能推荐)** 是本次优化的核心功能，建议优先实现
