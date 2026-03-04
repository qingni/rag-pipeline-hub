# Research: 检索查询模块优化版 - 技术调研

**Feature**: 005-search-query-opt | **Date**: 2026-02-26

## 概述

本调研针对 005-search-query-opt 的技术未知项进行研究，确保所有 NEEDS CLARIFICATION 已解决。重点调研混合检索链路集成、Reranker 精排集成、多 Collection 联合搜索方案，以及与已有代码的整合路径。

---

## Research 1: 混合检索链路集成方案

### 任务
研究如何将 `MilvusProvider.hybrid_search()` 集成到 `SearchService` 中，包括 BM25 查询向量生成、RRF 融合调用。

### 发现

**已有能力盘点**:
- ✅ `BM25SparseService.encode_query(index_id, query_text)` — 按索引 ID 加载 BM25 统计数据，懒加载 + 内存缓存
- ✅ `MilvusProvider.hybrid_search(index_id, dense_vector, sparse_vector, top_n, rrf_k)` — 已实现 Milvus 原生 RRFRanker 双路召回
- ✅ `MilvusProvider._collection_has_sparse_field()` — 检测 Collection 是否含稀疏向量字段
- ✅ `is_sparse_vector_valid()` — 验证稀疏向量有效性

**集成路径**:
1. `SearchService` 新增 `_hybrid_search_in_collection()` 方法
2. 调用 `BM25SparseService.encode_query()` 生成稀疏查询向量
3. 调用 `MilvusProvider.hybrid_search()` 执行双路召回 + RRF 融合
4. 返回带 `rrf_score` 和 `search_mode` 标签的候选集

**降级判断逻辑**:
```python
# 自动检测是否可用混合检索
has_sparse = milvus_provider._collection_has_sparse_field(collection)
sparse_vector = bm25_service.encode_query(index_id, query_text)
use_hybrid = has_sparse and sparse_vector is not None and is_sparse_vector_valid(sparse_vector)
```

### 决策
- **Decision**: 扩展 SearchService，新增 `_hybrid_search_in_collection()` 和 `_dense_search_in_collection()` 两个内部方法
- **Rationale**: 复用已有 BM25SparseService 和 MilvusProvider 实现，零重复开发
- **Alternatives considered**: 新建独立 HybridSearchService — 拒绝理由：增加不必要的模块复杂度，违反宪章模块化原则（应扩展而非新建）

---

## Research 2: Reranker 精排集成

### 任务
研究 RerankerService 与 SearchService 的集成方式，包括候选集传递格式、降级策略。

### 发现

**已有 RerankerService 能力**:
- ✅ 单例模式 `RerankerService.get_instance()`
- ✅ 延迟初始化 `init()` — 首次调用时加载模型
- ✅ `rerank(query, candidates, top_k, text_key)` — batch 推理，返回 reranker_score 排序结果
- ✅ `health_check()` — 健康状态检查
- ✅ `available` 属性 — 检查可用性
- ✅ 降级内置：不可用时直接返回原始 candidates[:top_k]

**候选集格式要求**:
RerankerService.rerank() 要求 candidates 中包含文本内容字段（默认 `text_key="text"`），搜索结果中文本存储在 `metadata.source_text` 或 `metadata.text`，需要适配。

**关键集成点**:
1. RRF 粗排后取 Top-N (默认 20) 候选集
2. 从候选集的 metadata 中提取文本内容
3. 调用 `RerankerService.rerank(query, candidates, top_k)`
4. 结果包含 `reranker_score` 字段

### 决策
- **Decision**: 在 SearchService 中添加 `_rerank_candidates()` 方法，封装 Reranker 调用和降级逻辑
- **Rationale**: 统一精排入口，便于多 Collection 和单 Collection 场景复用
- **Alternatives considered**: 直接在 search() 方法中内联 Reranker 调用 — 拒绝理由：多 Collection 场景也需要调用，内联导致代码重复

---

## Research 3: 多 Collection 联合搜索

### 任务
研究多 Collection 并行检索 + 统一 Reranker 精排的最佳实践和实现方案。

### 发现

**业内实践调研**:
- **Elasticsearch**: 跨索引搜索采用 "各分片独立召回 → 协调节点统一排序" 模式
- **Milvus**: 不支持原生跨 Collection 搜索，需应用层实现
- **LlamaIndex**: MultiIndex 方案：各 Index 独立检索，结果合并后统一 Reranker
- **LangChain**: EnsembleRetriever：各 retriever 独立检索，RRF/Reranker 融合

**并发方案**:
- 使用 `asyncio.gather()` 并行在各 Collection 中执行混合检索
- 各 Collection 独立完成 RRF 粗排，返回 Top-N 候选集
- 合并候选集（标注 source_collection）后统一 Reranker 精排

**候选集大小控制**:
- 各 Collection 统一 Top-N = 20
- 最大 5 个 Collection → Reranker 输入上限 5×20 = 100 条
- qwen3-reranker-4b 处理 100 条的推理耗时约 200-500ms，在可接受范围内

### 决策
- **Decision**: 使用 asyncio.gather 并行检索，合并后统一 Reranker 精排
- **Rationale**: 与 Elasticsearch/LlamaIndex 业内主流方案一致；asyncio.gather 充分利用 IO 并行性
- **Alternatives considered**: 串行各 Collection 检索 — 拒绝理由：5 个 Collection 串行会导致延迟线性增长

---

## Research 4: BM25 统计数据懒加载性能

### 任务
研究 BM25 统计数据的懒加载策略对首次查询延迟的影响。

### 发现

**已有实现分析**:
- `BM25SparseService._get_generator()` 已实现懒加载：首次查询时从磁盘加载 JSON → 内存缓存
- JSON 文件大小：10K 文档的 BM25 统计约 500KB-2MB
- 加载耗时：500KB 文件约 20-50ms，2MB 文件约 50-100ms

**首次查询影响**:
- 首次查询会增加 50-100ms 延迟（BM25 加载）
- 后续查询直接使用内存缓存，无额外开销
- 这符合 spec 中的端到端 3s P95 要求

**多 Collection 场景**:
- 各 Collection 的 BM25 统计独立加载和缓存
- 首次联合搜索时所有 Collection 并行加载，不会串行阻塞

### 决策
- **Decision**: 维持已有懒加载策略，不做预加载优化
- **Rationale**: 首次查询额外延迟在 50-100ms，端到端仍满足 3s P95 要求；预加载会增加内存占用
- **Alternatives considered**: 服务启动时预加载所有 Collection 的 BM25 统计 — 拒绝理由：大 Collection 场景下内存浪费

---

## Research 5: 前端组件扩展方案

### 任务
研究如何最小化修改已有前端组件以适配混合检索。

### 发现

**已有组件分析**:
- `SearchConfig.vue` (6.73KB): 已有 Collection 选择、TopK、阈值配置 → 需新增检索模式只读状态指示器、Reranker 参数
- `ResultCard.vue` (4.16KB): 已有相似度分数展示 → 需新增 search_mode 标签、rrf/reranker 分数
- `searchStore.js` (6.20KB): 已有配置状态管理 → 需扩展 config 添加 search_mode/reranker 参数
- `searchApi.js` (1.67KB): 已有 executeSearch() → 新增请求参数字段即可

**扩展策略**:
- 通过条件渲染 `v-if="config.searchMode === 'hybrid'"` 显示混合检索专属配置
- ResultCard 通过检查 `result.search_mode` 决定显示 rrf_score 还是 similarity_score
- 保持 API 向后兼容：新参数均有默认值，旧的纯稠密请求仍可用

### 决策
- **Decision**: 增量扩展已有组件，通过条件渲染和可选参数实现向后兼容
- **Rationale**: 最小化变更量，保持与其他模块的 UI 一致性
- **Alternatives considered**: 创建独立的 HybridSearch.vue 页面 — 拒绝理由：造成功能分裂，用户需要在两个页面切换

---

## Research 6: 搜索历史数据模型扩展

### 任务
研究如何扩展搜索历史以记录混合检索信息。

### 发现

**已有 SearchHistory 模型**:
- `config` 字段 (JSON): 已存储 top_k, threshold, metric_type
- 需新增记录: search_mode, reranker_available, rrf_k, reranker_top_n

**扩展方案**:
- 方案 A: 在现有 `config` JSON 字段中新增 key — 无需 schema migration
- 方案 B: 新增独立字段 `search_mode` — 需要 migration

### 决策
- **Decision**: 方案 A — 在 config JSON 中新增 key（search_mode, reranker_available 等）
- **Rationale**: 无需数据库 migration，向后兼容，已有历史记录不受影响
- **Alternatives considered**: 新增独立数据库字段 — 拒绝理由：增加 migration 复杂度，JSON 字段足以满足需求

---

## 所有 NEEDS CLARIFICATION 解决状态

| 项目 | 状态 | 结果 |
|------|------|------|
| 混合检索集成路径 | ✅ 已解决 | 扩展 SearchService，复用已有 BM25/Milvus/Reranker 服务 |
| Reranker 候选集格式 | ✅ 已解决 | 从 metadata 提取文本，适配 text_key 参数 |
| 多 Collection 并发方案 | ✅ 已解决 | asyncio.gather 并行检索 + 统一 Reranker 精排 |
| BM25 懒加载性能 | ✅ 已解决 | 首次额外 50-100ms，满足 P95 要求 |
| 前端扩展方案 | ✅ 已解决 | 增量扩展 + 条件渲染 + 向后兼容 |
| 搜索历史扩展 | ✅ 已解决 | config JSON 字段扩展，无需 migration |
