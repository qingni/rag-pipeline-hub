# Implementation Plan: 检索查询模块（优化版）

**Branch**: `005-search-query-opt` | **Date**: 2026-02-26 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/005-search-query-opt/spec.md`

## Summary

基于已实现的 005-search-query 模块进行优化升级，整合 004-vector-index-opt 中的混合检索能力（稠密+稀疏双路召回 → RRF 粗排 → Reranker 精排），实现完整的检索查询链路。

**核心变更**:
- **混合检索集成**: 在 SearchService 中集成 BM25 稀疏向量查询 + MilvusProvider.hybrid_search() + RRF 粗排
- **Reranker 精排**: 集成 RerankerService（qwen3-reranker-4b），对 RRF 粗排候选集进行精排重排序
- **多 Collection 联合搜索**: 支持并行在最多 5 个 Collection 中检索，合并候选集后统一 Reranker 精排
- **智能降级**: 稀疏向量不可用时降级纯稠密；Reranker 不可用时跳过精排
- **前端增强**: 搜索配置面板增加检索模式只读状态指示、Reranker 参数配置，结果卡片展示混合检索元数据

**技术方案**:
- 复用已有 `BM25SparseService`（查询时懒加载 BM25 统计数据）
- 复用已有 `MilvusProvider.hybrid_search()`（Milvus 原生 RRFRanker）
- 复用已有 `RerankerService`（qwen3-reranker-4b 单例）
- 扩展 `SearchService.search()` 添加混合检索和多 Collection 并行逻辑

## Technical Context

**Language/Version**: Python 3.11 (后端) + Vue 3 + Vite (前端)
**Primary Dependencies**: FastAPI 0.104.1, pymilvus 2.3.4, FlagEmbedding>=1.2.0, jieba, TDesign Vue Next, Pinia
**Storage**: SQLite (搜索历史 - search_history 表) + Milvus 2.x (向量检索)
**Testing**: pytest (后端), Vitest (前端)
**Target Platform**: Linux/macOS 服务器 + 现代浏览器
**Project Type**: Web Application (frontend + backend)
**Performance Goals**: 纯稠密 <100ms P95, 混合检索 <200ms P95, Reranker 精排 <100ms P95, 端到端 <3s P95
**Constraints**: 查询文本 ≤2000 字符, 历史记录 ≤50 条, RRF k=60(后端配置), Reranker 候选集 N=20, 联合搜索最多 5 Collection
**Scale/Scope**: 单租户，10K 向量级别索引，20 并发 10 QPS

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| **I. 模块化架构** | ✅ PASS | 扩展已有 `search_service.py`，复用 BM25/Reranker/Milvus 独立服务；新增逻辑通过方法拆分保持单一职责 |
| **II. 多提供商支持** | ✅ PASS | 向量检索通过 MilvusProvider 抽象；Reranker 通过 RerankerService 单例封装，模型可配置 |
| **III. 结果持久化** | ✅ PASS | 搜索历史扩展 search_mode/reranker 字段存储在 SQLite；BM25 统计持久化到 JSON |
| **IV. 用户体验优先** | ✅ PASS | Vue3 + TDesign，混合检索元数据（search_mode/rrf_score/reranker_score）可视化展示 |
| **V. API标准化** | ✅ PASS | RESTful API，统一响应格式，新增 hybrid-search 端点和 reranker/health 端点 |

**Constitution Gate**: ✅ PASSED

**Post-Phase 1 Re-check**: ✅ PASSED — 数据模型和 API 契约设计均符合宪章约束。

## Project Structure

### Documentation (this feature)

```text
specs/005-search-query-opt/
├── plan.md              # 本文件 - 实现计划
├── research.md          # Phase 0 - 技术调研
├── data-model.md        # Phase 1 - 数据模型设计
├── quickstart.md        # Phase 1 - 快速开始指南
├── contracts/           # Phase 1 - API 契约
│   └── search-api.yaml
├── tasks.md             # Phase 2 - 任务分解 (由 /speckit.tasks 生成)
└── checklists/
    └── requirements.md  # 需求检查清单
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── api/
│   │   └── search.py                  # ⚡ 扩展：新增 hybrid-search、reranker/health 端点
│   ├── models/
│   │   └── search.py                  # ⚡ 扩展：SearchHistory 增加 search_mode 字段
│   ├── schemas/
│   │   └── search.py                  # ⚡ 扩展：新增 HybridSearchRequest/Response、Reranker 相关 schema
│   ├── services/
│   │   ├── search_service.py          # ⚡ 重点扩展：混合检索、多 Collection 并行、Reranker 精排、降级逻辑
│   │   ├── bm25_service.py            # ✅ 已有：BM25SparseService.encode_query()
│   │   ├── reranker_service.py        # ✅ 已有：RerankerService.rerank()
│   │   └── providers/
│   │       └── milvus_provider.py     # ✅ 已有：hybrid_search()
│   ├── config/
│   │   └── __init__.py                # ⚡ 扩展：新增 RRF_K、RERANKER_TOP_N 等配置项
│   └── vector_config.py               # ✅ 已有：MilvusConfig、Collection 命名
└── tests/
    └── test_search/
        ├── test_hybrid_search.py      # 🆕 新建：混合检索测试
        ├── test_multi_collection.py   # 🆕 新建：多 Collection 联合搜索测试
        └── test_reranker_integration.py # 🆕 新建：Reranker 集成测试

frontend/
├── src/
│   ├── views/
│   │   └── Search.vue                 # ⚡ 扩展：适配混合检索结果展示
│   ├── components/
│   │   └── search/                    # (已有目录，注意大小写兼容)
│   │       ├── SearchInput.vue        # ✅ 已有：无需修改
│   │       ├── SearchConfig.vue       # ⚡ 扩展：增加检索模式只读状态指示、Reranker 参数
│   │       ├── SearchResults.vue      # ⚡ 扩展：混合检索元数据展示
│   │       ├── ResultCard.vue         # ⚡ 扩展：search_mode 标签、rrf/reranker 分数
│   │       ├── ResultDetail.vue       # ⚡ 扩展：精排详情展示
│   │       └── SearchHistory.vue      # ⚡ 扩展：历史记录显示 search_mode
│   ├── services/
│   │   └── searchApi.js               # ⚡ 扩展：新增 hybrid-search API 调用
│   └── stores/
│       └── searchStore.js             # ⚡ 扩展：混合检索配置状态管理
└── tests/
    └── components/                     # 组件测试
```

**Structure Decision**: 沿用 Web Application 前后端分离结构。本次为**增量扩展**，所有修改基于 005-search-query 已有代码，不创建新的服务文件（除测试外），保持模块内聚。

## Key Design Decisions

### 1. 混合检索集成方案

**Decision**: 扩展 `SearchService.search()` 方法，根据 search_mode 参数分发到纯稠密或混合检索路径

**Implementation Flow**:
```
SearchService.search(request)
  ├─ 纯稠密模式 (dense_only)
  │   → EmbeddingService.embed(query)
  │   → MilvusProvider.search(dense_vector)
  │   → RerankerService.rerank(candidates) [可选]
  │   → 返回结果
  │
  └─ 混合检索模式 (hybrid) [默认]
      → EmbeddingService.embed(query) [稠密向量]
      → BM25SparseService.encode_query(index_id, query) [稀疏向量]
      → MilvusProvider.hybrid_search(dense, sparse, rrf_k=60) [RRF 粗排]
      → RerankerService.rerank(top_n_candidates, top_k) [精排]
      → 返回结果（含 search_mode/rrf_score/reranker_score）
```

**Rationale**: 复用已有的 BM25SparseService、MilvusProvider.hybrid_search()、RerankerService，最小化代码变更。

### 2. 多 Collection 联合搜索

**Decision**: 并行在各 Collection 执行检索+RRF 粗排，合并候选集后统一一次 Reranker 精排

**Implementation Flow**:
```
multi_collection_search(collections, request)
  → asyncio.gather(*[search_single_collection(c) for c in collections])  # 并行各 Collection
  → merge_candidates(all_top_n_results)  # 合并候选集 (最大 5×20=100 条)
  → RerankerService.rerank(merged, top_k)  # 统一精排
  → 标注 source_collection
```

**Rationale**: 各 Collection 的 RRF 分数不可跨 Collection 比较，必须通过统一 Reranker 获得全局可比分数。

### 3. 降级策略

**Decision**: 三层降级，确保检索服务始终可用

| 降级条件 | 行为 | search_mode |
|---------|------|-------------|
| Collection 无稀疏向量字段 | 跳过 BM25，纯稠密检索 → Reranker | dense_only |
| BM25 统计数据缺失 | 跳过稀疏路，纯稠密检索 → Reranker | dense_only |
| Reranker 服务不可用 | 跳过精排，返回 RRF/dense 粗排结果 | hybrid/dense_only + reranker_available=false |

### 4. 后端配置管理

**Decision**: 新增配置项到 `config/__init__.py`，通过环境变量可覆盖

```python
# 混合检索配置
RRF_K: int = 60                    # RRF 融合参数（前端不暴露）
RERANKER_TOP_N: int = 20           # Reranker 候选集大小
MAX_COLLECTIONS: int = 5           # 联合搜索最大 Collection 数
DEFAULT_SEARCH_MODE: str = "auto"  # auto/hybrid/dense_only
```

### 5. 前端组件扩展

**Decision**: 最小化修改已有组件，通过条件渲染适配混合检索

**Changes**:
- `SearchConfig.vue`: 新增检索模式只读状态指示器（显示「当前：混合检索」或「当前：纯稠密检索」，由系统自动决定，用户无需手动选择）、Reranker top_n/top_k 参数
- `ResultCard.vue`: 新增 search_mode 标签、rrf_score/reranker_score 展示
- `searchStore.js`: 扩展 config 状态增加 search_mode（只读）/reranker 参数

## Complexity Tracking

> 无宪章违规，无需记录

## Generated Artifacts

| Artifact | Path | Status |
|----------|------|--------|
| plan.md | specs/005-search-query-opt/plan.md | ✅ Complete |
| research.md | specs/005-search-query-opt/research.md | ✅ Complete |
| data-model.md | specs/005-search-query-opt/data-model.md | ✅ Complete |
| search-api.yaml | specs/005-search-query-opt/contracts/search-api.yaml | ✅ Complete |
| quickstart.md | specs/005-search-query-opt/quickstart.md | ✅ Complete |

## Next Steps

运行 `/speckit.tasks` 生成详细的任务分解。
