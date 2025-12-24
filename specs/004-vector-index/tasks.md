# Task Breakdown: 向量索引模块

**Feature**: 004-vector-index  
**Branch**: `004-vector-index`  
**Generated**: 2025-12-23  
**Total Tasks**: 92 tasks

## Overview

本文档将向量索引模块的实现分解为 92 个可执行任务，按用户故事（User Story）组织，支持独立实现和测试。技术架构采用 **Milvus 为主、FAISS 为备选** 的双 Provider 模式，并针对 macOS 环境添加了 Colima Docker 支持。

### Task Organization

- **Phase 1**: 环境配置与基础设施 (10 tasks)
- **Phase 2**: 基础组件 (12 tasks)
- **Phase 3**: User Story 1 - 向量索引构建 (P1) (18 tasks)
- **Phase 4**: User Story 2 - 向量相似度检索 (P1) (16 tasks)
- **Phase 5**: User Story 3 - 索引更新与删除 (P2) (12 tasks)
- **Phase 6**: User Story 4 - 索引持久化与恢复 (P2) (8 tasks)
- **Phase 7**: User Story 5 - 多索引管理 (P3) (6 tasks)
- **Phase 8**: 前端实现 (6 tasks)
- **Phase 9**: 文档与部署 (4 tasks)

### MVP Scope

**推荐 MVP**: Phase 1 + Phase 2 + Phase 3 + Phase 4 + Phase 8 (62 tasks)

这将提供完整的索引构建和检索功能，满足核心用户需求。

---

## Phase 1: 环境配置与基础设施

**目标**: 搭建开发环境，配置 Milvus 和数据库（包含 Colima 支持）

**独立测试标准**: 
- Milvus 服务成功启动并可连接
- PostgreSQL 数据库创建成功
- 数据库迁移脚本执行无错误
- macOS 环境下 Colima 正常工作

### Tasks

- [X] T001 [P] 创建 Colima 启动脚本 scripts/start_colima.sh（macOS Docker 支持）
- [X] T002 配置 Milvus Docker Compose 环境，创建 docker/milvus/docker-compose.yml
- [X] T003 [P] 创建 PostgreSQL 数据库迁移脚本 migrations/vector_index/001_create_vector_indexes_table.sql
- [X] T004 [P] 创建索引统计表迁移脚本 migrations/vector_index/002_create_index_statistics_table.sql
- [X] T005 [P] 创建向量元数据表迁移脚本 migrations/vector_index/003_create_vector_metadata_table.sql
- [X] T006 [P] 创建查询历史表迁移脚本 migrations/vector_index/004_create_query_history_table.sql
- [X] T007 [P] 配置后端环境变量模板 backend/.env.example（Milvus 连接参数）
- [X] T008 [P] 创建 Milvus 连接配置类 backend/src/config/milvus_config.py
- [X] T009 [P] 创建 FAISS 配置类 backend/src/config/faiss_config.py
- [X] T010 编写环境初始化脚本 backend/scripts/init_vector_index.sh

---

## Phase 2: 基础组件（阻塞性前置任务）

**目标**: 实现 Provider 抽象层、数据模型和工具类

**独立测试标准**:
- 所有数据模型类可实例化并序列化为 JSON
- 向量验证工具正确识别无效输入
- Provider 接口定义完整

**完成标准**: 必须在进入任何 User Story 前完成

### Tasks

- [X] T011 [P] 创建 VectorIndex 数据模型 backend/src/models/vector_index.py
- [X] T012 [P] 创建 IndexStatistics 数据模型 backend/src/models/index_statistics.py
- [X] T013 [P] 创建 QueryHistory 数据模型 backend/src/models/query_history.py
- [X] T014 [P] 实现向量验证工具 backend/src/utils/vector_utils.py (validate_vector, normalize_vector)
- [X] T015 [P] 实现相似度计算工具 backend/src/utils/similarity.py (cosine, euclidean, dot_product)
- [X] T016 [P] 定义 BaseProvider 抽象接口 backend/src/services/providers/base_provider.py
- [X] T017 [P] 创建索引注册表类 backend/src/services/index_registry.py
- [X] T018 [P] 实现统一错误类 backend/src/exceptions/vector_index_errors.py
- [X] T019 [P] 创建 JSON 结果持久化工具 backend/src/utils/result_persistence.py
- [X] T020 [P] 实现日志配置 backend/src/utils/logger.py (vector_index 专用日志)
- [X] T021 实现数据库会话管理器 backend/src/database/session.py (已存在，复用)
- [X] T022 创建数据库初始化脚本 backend/scripts/init_database.py

---

## Phase 3: User Story 1 - 向量索引构建 (P1)

**用户故事**: 作为RAG系统，我需要接收向量数据并构建高效的索引结构

**独立测试标准**:
1. ✅ **Scenario 1**: 提交 1000 条 1536 维向量，30 秒内完成索引构建并返回索引 ID
2. ✅ **Scenario 2**: 提交维度不一致的向量，系统拒绝并返回明确错误信息
3. ✅ **Scenario 3**: 构建包含 10000 条向量的索引，系统重启后索引自动恢复

### Tasks

#### Milvus Provider (PRIMARY)

- [X] T023 [P] [US1] 实现 MilvusProvider 初始化和连接管理 backend/src/services/providers/milvus_provider.py
- [X] T024 [P] [US1] 实现 Milvus Collection Schema 定义和创建逻辑（create_index 方法）
- [X] T025 [P] [US1] 实现 Milvus 批量向量插入（insert_vectors 方法，batch_size=1000）
- [X] T026 [P] [US1] 实现 Milvus 索引构建（build_index 方法，支持 FLAT/IVF_FLAT/IVF_PQ/HNSW）
- [X] T027 [P] [US1] 实现 Milvus Collection 加载到内存（load_index 方法）
- [X] T028 [US1] 实现 Milvus 连接健康检查（health_check 方法）

#### FAISS Provider (FALLBACK)

- [X] T029 [P] [US1] 实现 FAISSProvider 初始化 backend/src/services/providers/faiss_provider.py
- [X] T030 [P] [US1] 实现 FAISS 索引创建（create_index，支持 IndexFlatIP/IndexIVFPQ）
- [X] T031 [P] [US1] 实现 FAISS 向量插入（insert_vectors 方法）
- [X] T032 [P] [US1] 实现 FAISS 索引训练逻辑（train_index 方法，IVF 索引）

#### Service Layer

- [X] T033 [US1] 实现 VectorIndexService 主服务类 backend/src/services/vector_index_service.py
- [X] T034 [US1] 实现 create_index 服务方法（Provider 选择逻辑：Milvus优先，FAISS备选）
- [X] T035 [US1] 实现 add_vectors 服务方法（批量插入 + 向量验证）
- [X] T036 [US1] 实现索引构建结果 JSON 持久化（保存到 results/index_build_{timestamp}.json）
- [X] T037 [US1] 实现索引状态更新逻辑（building → ready 状态转换）

#### API Layer

- [X] T038 [US1] 实现 POST /api/v1/indexes 端点 backend/src/api/routes/vector_index.py
- [X] T039 [US1] 实现 POST /api/v1/indexes/{name}/vectors 端点
- [X] T040 [US1] 实现请求参数验证（Pydantic models）

---

## Phase 4: User Story 2 - 向量相似度检索 (P1)

**用户故事**: 作为 RAG 系统，我需要快速检索最相似的 K 个向量

**独立测试标准**:
1. ✅ **Scenario 1**: 在 10000 条向量索引中查询 Top5，100ms 内返回结果
2. ✅ **Scenario 2**: 指定相似度阈值 0.8，只返回高于阈值的结果
3. ✅ **Scenario 3**: 指定命名空间查询，只返回该命名空间的向量

### Tasks

#### Milvus Provider (PRIMARY)

- [X] T041 [P] [US2] 实现 Milvus 向量搜索（search_vectors 方法，支持 TopK）
- [X] T042 [P] [US2] 实现 Milvus 过滤表达式查询（filter_expr 支持）
- [X] T043 [P] [US2] 实现 Milvus 批量查询（batch_search 方法）
- [X] T044 [P] [US2] 实现查询结果格式化（转换为 QueryResult 对象）
- [X] T045 [P] [US2] 实现 Milvus 搜索参数优化（ef/nprobe 调优）

#### FAISS Provider (FALLBACK)

- [X] T046 [P] [US2] 实现 FAISS 向量搜索（search_vectors 方法）
- [X] T047 [P] [US2] 实现 FAISS 元数据过滤（基于 PostgreSQL）
- [X] T048 [P] [US2] 实现 FAISS 批量查询

#### Service Layer

- [X] T049 [US2] 实现 search_vectors 服务方法（Provider 路由：Milvus优先）
- [X] T050 [US2] 实现相似度阈值过滤逻辑
- [X] T051 [US2] 实现查询结果 JSON 持久化（results/query_result_{timestamp}.json）
- [X] T052 [US2] 实现查询历史记录（写入 query_history 表）
- [X] T053 [US2] 实现查询性能统计（更新 avg_query_latency_ms）

#### API Layer

- [X] T054 [US2] 实现 POST /api/v1/indexes/{name}/search 端点
- [X] T055 [US2] 实现 POST /api/v1/indexes/{name}/batch-search 端点
- [ ] T056 [US2] 实现搜索请求参数验证（top_k, threshold, filter_expr）

---

## Phase 5: User Story 3 - 索引更新与删除 (P2)

**用户故事**: 作为用户，我需要增量更新索引而不重建

**独立测试标准**:
1. ✅ **Scenario 1**: 向 1000 条索引添加 100 条新向量，10 秒内完成
2. ✅ **Scenario 2**: 更新特定向量，后续查询使用新向量
3. ✅ **Scenario 3**: 删除向量列表，后续查询不返回这些结果

### Tasks

#### Milvus Provider

- [ ] T057 [P] [US3] 实现 Milvus 向量删除（delete_vectors 方法）
- [ ] T058 [P] [US3] 实现 Milvus 向量更新（upsert_vectors 方法）
- [ ] T059 [P] [US3] 实现 Milvus 删除操作的一致性保证

#### FAISS Provider

- [ ] T060 [P] [US3] 实现 FAISS 向量删除（通过 remove_ids）
- [ ] T061 [P] [US3] 实现 FAISS 增量添加（add_with_ids）
- [ ] T062 [US3] 实现 FAISS 索引重建优化（仅在必要时重建）

#### Service Layer

- [ ] T063 [US3] 实现 update_vectors 服务方法
- [ ] T064 [US3] 实现 delete_vectors 服务方法
- [ ] T065 [US3] 实现索引状态管理（updating 状态）
- [ ] T066 [US3] 实现向量计数自动更新
- [ ] T067 [US3] 实现并发写操作的锁机制（Milvus原生/FAISS RWLock）

#### API Layer

- [ ] T068 [US3] 实现 DELETE /api/v1/indexes/{name}/vectors 端点

---

## Phase 6: User Story 4 - 索引持久化与恢复 (P2)

**用户故事**: 作为系统管理员，我需要索引能持久化并在故障后恢复

**独立测试标准**:
1. ✅ **Scenario 1**: 50000 条向量索引持久化，60 秒内完成，空间占用 <120%
2. ✅ **Scenario 2**: 系统崩溃后重启，30 秒内恢复索引
3. ✅ **Scenario 3**: 索引文件迁移到新服务器，检索结果一致

### Tasks

#### Milvus Provider

- [ ] T069 [P] [US4] 实现 Milvus 手动 flush（persist_index 方法）
- [ ] T070 [P] [US4] 实现 Milvus 索引恢复（从 Collection 加载）

#### FAISS Provider

- [ ] T071 [P] [US4] 实现 FAISS 索引保存（faiss.write_index）
- [ ] T072 [P] [US4] 实现 FAISS 索引加载（faiss.read_index）
- [ ] T073 [US4] 实现自动持久化触发器（每 1000 次更新或 5 分钟）

#### Service Layer

- [ ] T074 [US4] 实现 persist_index 服务方法（Provider 路由）
- [ ] T075 [US4] 实现 load_index 服务方法（启动时自动加载）

#### API Layer

- [ ] T076 [US4] 实现 POST /api/v1/indexes/{name}/persist 端点

---

## Phase 7: User Story 5 - 多索引管理 (P3)

**用户故事**: 作为多租户系统，我需要管理多个独立索引

**独立测试标准**:
1. ✅ **Scenario 1**: 创建 3 个不同索引，各自独立存储
2. ✅ **Scenario 2**: 跨索引查询，返回合并结果并标注来源
3. ✅ **Scenario 3**: 删除一个索引，其他索引不受影响

### Tasks

#### Service Layer

- [ ] T077 [P] [US5] 实现索引注册表的 CRUD 操作（IndexRegistry）
- [ ] T078 [P] [US5] 实现跨索引查询（multi_index_search）
- [ ] T079 [P] [US5] 实现索引导出功能（export_index）
- [ ] T080 [P] [US5] 实现索引导入功能（import_index）

#### API Layer

- [ ] T081 [US5] 实现 GET /api/v1/indexes 端点（列出所有索引）
- [ ] T082 [US5] 实现 DELETE /api/v1/indexes/{name} 端点

---

## Phase 8: 前端实现

**目标**: 实现 Vue3 + TDesign 前端界面

**独立测试标准**:
- 索引列表页面正确展示所有索引
- 创建索引表单提交成功
- 搜索功能返回正确结果

### Tasks

- [X] T083 [P] 创建 VectorIndexPage 主页面 frontend/src/pages/VectorIndexPage.vue
- [X] T084 [P] 创建 IndexList 组件（t-table）frontend/src/components/VectorIndex/IndexList.vue
- [X] T085 [P] 创建 IndexCreate 组件（t-form）frontend/src/components/VectorIndex/IndexCreate.vue
- [X] T086 [P] 创建 VectorSearch 组件 frontend/src/components/VectorIndex/VectorSearch.vue
- [X] T087 [P] 实现 API 调用服务 frontend/src/services/vectorIndexApi.js
- [X] T088 [P] 实现 Pinia Store frontend/src/stores/vectorIndexStore.js

---

## Phase 9: 文档与部署

**目标**: 完善文档和部署配置

**独立测试标准**:
- Milvus 连接测试脚本运行成功
- Docker 环境一键启动
- 文档覆盖所有主要功能

### Tasks

- [ ] T089 [P] 创建 Milvus 连接测试脚本 backend/scripts/test_milvus_connection.py
- [ ] T090 [P] 更新项目 README 添加向量索引模块说明
- [ ] T091 [P] 创建 Docker 一键启动脚本 scripts/start_all.sh（Colima + Milvus + Backend）
- [ ] T092 [P] 添加 Troubleshooting 文档 docs/vector-index-troubleshooting.md

---

## Dependencies & Execution Order

### Critical Path (必须按顺序)

```
Phase 1 (环境配置)
  ↓
Phase 2 (基础组件) ← BLOCKING
  ↓
Phase 3 (US1: 索引构建) ← MVP CORE
  ↓
Phase 4 (US2: 相似度检索) ← MVP CORE
  ↓
Phase 5 (US3: 更新删除) ← 可选
  ↓
Phase 6 (US4: 持久化) ← 可选
  ↓
Phase 7 (US5: 多索引) ← 可选
```

### Parallel Execution Opportunities

#### Phase 1: 环境配置（部分可并行）
```bash
# Group A: 脚本和配置（可同时创建）
T001, T007, T008, T009, T010  # 可并行

# Group B: 数据库迁移（可同时创建）
T003, T004, T005, T006  # 可并行

# Sequential: T002 (Docker Compose) 依赖 T001 (Colima 脚本)
```

#### Phase 2: 基础组件（高度并行）
```bash
# Group A: 数据模型
T011, T012, T013  # 可同时开发

# Group B: 工具类
T014, T015, T019, T020  # 可同时开发

# Group C: Provider 基础
T016, T017, T018, T021, T022  # 可同时开发
```

#### Phase 3: US1 索引构建（高度并行）
```bash
# Group A: Milvus Provider
T023, T024, T025, T026, T027, T028  # 可同时开发

# Group B: FAISS Provider（独立于 Group A）
T029, T030, T031, T032  # 可同时开发

# Group C: Service & API（依赖 Provider 接口定义）
T033, T034, T035, T036, T037, T038, T039, T040  # Provider 完成后并行开发
```

#### Phase 4: US2 相似度检索（高度并行）
```bash
# Group A: Milvus 搜索
T041, T042, T043, T044, T045  # 可同时开发

# Group B: FAISS 搜索（独立于 Group A）
T046, T047, T048  # 可同时开发

# Group C: Service & API
T049, T050, T051, T052, T053, T054, T055, T056  # Provider 完成后并行
```

#### Phase 8: 前端（完全并行）
```bash
# 所有前端任务可同时开发
T083, T084, T085, T086, T087, T088
```

#### Phase 9: 文档与部署（完全并行）
```bash
# 所有文档任务可同时进行
T089, T090, T091, T092
```

---

## Implementation Strategy

### Week 1: MVP Foundation

**Day 1-2**: Phase 1 + Phase 2 (环境配置 + 基础组件)
- 完成任务: T001-T022
- 里程碑: 
  - ✅ Colima 脚本可用（macOS）
  - ✅ Milvus 服务成功启动
  - ✅ 数据库 Schema 创建
  - ✅ Provider 接口定义完成

**Day 3-5**: Phase 3 (US1 索引构建)
- 完成任务: T023-T040
- 里程碑:
  - ✅ Milvus/FAISS 索引构建成功
  - ✅ API 可调用
  - ✅ 1000 条向量 30 秒内完成索引

### Week 2: Core Features

**Day 1-3**: Phase 4 (US2 相似度检索)
- 完成任务: T041-T056
- 里程碑:
  - ✅ 搜索功能完整
  - ✅ 性能达标（<100ms）
  - ✅ 查询历史记录正常

**Day 4-5**: Phase 8 (前端基础)
- 完成任务: T083-T088
- 里程碑:
  - ✅ 前端可创建索引和搜索
  - ✅ E2E 流程打通

### Week 3: Advanced Features (Optional)

**Day 1-2**: Phase 5 (US3 更新删除)
- 完成任务: T057-T068

**Day 3-4**: Phase 6 (US4 持久化) + Phase 9 (文档)
- 完成任务: T069-T076, T089-T092

**Day 5**: Phase 7 (US5 多索引)
- 完成任务: T077-T082

---

## Testing Strategy

### 单元测试（Unit Tests）

覆盖所有 Provider 和 Service 方法：

```python
# backend/tests/unit/test_milvus_provider.py
def test_milvus_create_collection():
    """测试 Milvus Collection 创建"""
    pass

def test_milvus_insert_vectors():
    """测试 Milvus 向量插入"""
    pass

# backend/tests/unit/test_faiss_provider.py
def test_faiss_create_index():
    """测试 FAISS 索引创建"""
    pass

def test_faiss_search():
    """测试 FAISS 向量搜索"""
    pass
```

### 集成测试（Integration Tests）

测试 API 端点和完整流程：

```python
# backend/tests/integration/test_index_api.py
def test_create_index_api():
    """测试创建索引 API"""
    pass

def test_search_api_end_to_end():
    """测试搜索 E2E 流程"""
    pass

# backend/tests/integration/test_provider_switching.py
def test_milvus_fallback_to_faiss():
    """测试 Milvus 不可用时降级到 FAISS"""
    pass
```

### 性能测试（Performance Tests）

验证性能指标：

```python
# backend/tests/performance/test_query_latency.py
def test_query_latency_under_100ms():
    """验证 10K 向量查询延迟 <100ms"""
    pass

def test_concurrent_queries_throughput():
    """验证 10 并发查询吞吐量 >50 QPS"""
    pass
```

---

## Task Checklist Format Validation

✅ **所有任务遵循标准格式**:
- [x] 所有任务以 `- [ ]` 开头
- [x] 包含任务 ID（T001-T092）
- [x] 并行任务标记 `[P]`
- [x] User Story 任务标记 `[US1]`-`[US5]`
- [x] 包含明确的文件路径

---

## Summary

| Phase | User Story | Tasks | Parallel | MVP |
|-------|-----------|-------|----------|-----|
| Phase 1 | 环境配置 | 10 | 8 | ✅ |
| Phase 2 | 基础组件 | 12 | 10 | ✅ |
| Phase 3 | US1 (P1) | 18 | 13 | ✅ |
| Phase 4 | US2 (P1) | 16 | 12 | ✅ |
| Phase 5 | US3 (P2) | 12 | 8 | ❌ |
| Phase 6 | US4 (P2) | 8 | 5 | ❌ |
| Phase 7 | US5 (P3) | 6 | 4 | ❌ |
| Phase 8 | 前端 | 6 | 6 | ✅ |
| Phase 9 | 文档 | 4 | 4 | ❌ |
| **Total** | - | **92** | **70** | **62** |

**Parallelization Rate**: 76% (70/92 tasks 可并行执行)

**MVP Task Count**: 62 tasks (Phases 1-4 + Phase 8)

---

## Key Updates (新增内容)

### 🆕 Colima 支持（macOS 专属）

1. **T001**: Colima 启动脚本
   - 自动检测操作系统
   - 一键启动 Docker 运行时
   - 智能错误恢复

2. **T091**: 一键启动脚本
   - 集成 Colima + Milvus + Backend
   - 跨平台支持（macOS/Linux/Windows）

3. **环境配置优化**:
   - Phase 1 增加 2 个任务（T001, T009）
   - Phase 9 新增部署相关任务

### 📊 对比旧版本

| 项目 | 旧版本 | 新版本 | 变化 |
|------|--------|--------|------|
| 总任务数 | 84 | 92 | +8 (+10%) |
| 可并行任务 | 62 | 70 | +8 (+13%) |
| MVP 任务数 | 53 | 62 | +9 (+17%) |
| Phase 数量 | 8 | 9 | +1 |

**新增任务分布**:
- Phase 1: +2 (Colima 脚本 + FAISS 配置)
- Phase 4: +1 (Milvus 搜索参数优化)
- Phase 5: +1 (并发写操作锁机制)
- Phase 9: +4 (新增 Phase，文档与部署)

---

## Next Steps

1. **立即开始**: 执行 Phase 1 任务（T001-T010）
2. **macOS 用户**: 优先运行 T001 创建 Colima 脚本
3. **并行开发**: Phase 2 可由 2-3 名开发者同时进行
4. **MVP 里程碑**: 完成 Phase 4 后进行用户验收测试
5. **持续集成**: 每个 Phase 完成后运行验收测试

**Ready to Start**: ✅ 所有任务已细化，支持 macOS/Linux/Windows 多平台部署！
