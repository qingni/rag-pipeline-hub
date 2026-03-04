# Feature Specification: 向量索引模块（优化版）

**Feature Branch**: `004-vector-index-opt`  
**Created**: 2026-02-05  
**Status**: Draft  
**Input**: User description: "基于 004-vector-index 进行优化，移除 FAISS，仅使用 Milvus 向量数据库"

## 版本变更说明

本版本基于 `004-vector-index` 进行优化，主要变更：

- **移除 FAISS 支持**：简化架构，专注于 Milvus 向量数据库
- **统一存储后端**：所有向量索引统一使用 Milvus，降低维护成本
- **简化前端选项**：移除向量数据库选择，默认使用 Milvus

## Clarifications

### Session 2024-12-24 (继承自 004-vector-index)

- Q: 向量索引历史记录的前端展示形式应该是什么？ → A: 采用左右分栏布局 - 左侧为索引配置区（选择向量化结果、索引算法），右侧为双Tab卡片（索引结果 + 历史记录），样式参考文档向量化模块

### Session 2026-02-06

- Q: 稀疏向量的生成方式？ → A: ~~使用 BGE-M3 模型同时输出稠密向量和稀疏向量（一次推理，双路输出）~~ [Updated: 2026-02-25] 使用 BM25 算法独立生成稀疏向量（jieba 分词 + 自建词表），与嵌入模型 API 的稠密向量分离生成
- Q: 混合检索的融合与排序策略？ → A: 两阶段方案——Milvus 原生 RRFRanker 做多路粗排融合 + qwen3-reranker-4b 模型做精排重排序
- Q: 稀疏向量为空或质量低时的降级策略？ → A: 自动降级到纯稠密向量检索（跳过 RRF 融合），直接将稠密检索 Top-N 送入 Reranker 精排
- Q: 稀疏向量索引类型选择？ → A: 使用 SPARSE_INVERTED_INDEX（Milvus 专用稀疏向量倒排索引），度量方式为 IP（内积）
- Q: 稀疏向量生成的集成位置？ → A: ~~在现有 Embedding 模块中启用 BGE-M3 的稀疏向量输出（一次推理同时输出稠密和稀疏向量），Embedding 接口同时返回双路向量~~ [Updated: 2026-02-25] 在索引构建阶段（VectorIndexService.create_index_from_embedding）中由 BM25SparseService 独立生成稀疏向量，与嵌入模型 API 解耦
- Q: 智能推荐索引算法和度量类型的交互方式？ → A: 自动填充 + 推荐理由标签——用户选择向量化任务后，系统根据向量特征自动填充推荐的索引算法和度量类型，旁边显示推荐理由，用户可手动覆盖
- Q: 智能推荐的决策维度？ → A: 基于向量维度 + 数据量 + Embedding 模型类型三个维度进行推荐决策，业内最佳实践的核心决策因子组合
- Q: 智能推荐的默认规则映射表？ → A: 采用基于数据量的分层规则匹配方案（业界主流实践），具体规则：数据量<1万用FLAT，1万~50万用HNSW（业界首选），50万~500万用IVF_SQ8（标量量化节省约75%内存），≥500万用IVF_PQ；度量类型按模型推断（BGE/OpenAI归一化模型用COSINE，未识别模型默认L2）
- Q: 推荐规则无法匹配时的兜底策略？ → A: 使用兜底默认推荐（HNSW + COSINE）+ 提示标签"未精确匹配推荐规则，已使用通用默认值"，用户仍可手动修改
- Q: 智能推荐结果的验收标准？ → A: 推荐采纳率 ≥ 80%（用户未手动修改推荐值的比例）+ 推荐延迟 ≤ 500ms（从选择向量化任务到推荐值填充完成）

### Session 2026-02-05

- Q: 当用户尝试删除不存在的向量ID时，系统应该报错还是静默忽略？ → A: 静默忽略，返回成功（幂等性设计）
- Q: Milvus 连接失败时应该采用什么重试策略？ → A: 指数退避重试（1s → 2s → 4s，最多3次）
- Q: 向量元数据的必需字段应该包含哪些？ → A: 最小必需字段集：`doc_id`（文档ID）+ `chunk_index`（分块索引）+ `created_at`（创建时间），其他为可选自定义字段
- Q: 前端索引构建时应如何展示进度？ → A: 实时进度条（显示百分比 + 已处理/总数）+ 状态文字提示（如"正在构建索引..."）
- Q: 索引构建失败时，前端应如何展示错误信息？ → A: 错误弹窗（Modal/Alert）+ 显示错误类型、详细错误信息和建议操作
- Q: 首期需要支持哪些向量数据库？ → A: 仅支持 Milvus 向量数据库
- Q: 前端应提供哪些索引算法选项？ → A: FLAT + IVF_FLAT + IVF_SQ8 + IVF_PQ + HNSW 五种索引算法
- Q: 历史记录需要支持哪些操作？ → A: 支持查看详情 + 删除记录

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 向量数据索引构建 (Priority: P1)

作为RAG系统的核心组件，向量索引模块需要能够接收文档的向量表示并通过 Milvus 构建高效的索引结构，以支持后续的相似度检索。用户上传文档后，系统将文档分块、向量化，然后通过向量索引模块将这些向量数据组织成可快速检索的索引。

**Why this priority**: 这是向量索引模块的基础功能，没有索引构建就无法进行后续的检索操作。这是整个模块的MVP核心。

**Independent Test**: 可以通过提交一批向量数据（如100条），验证索引是否成功创建，索引大小是否合理，以及能否通过索引查询接口访问这些数据。

**Acceptance Scenarios**:

1. **Given** 用户提供了一批文档向量数据（维度为1536，数量为1000条），**When** 调用索引构建接口，**Then** 系统在30秒内完成索引构建并返回索引ID，状态变为 `READY`
2. **Given** 索引构建过程中，**When** 遇到维度不一致的向量数据，**Then** 系统拒绝该向量并返回明确的错误信息，不影响其他有效向量的索引构建
3. **Given** 用户构建了一个包含10000条向量的索引，**When** 系统重启后，**Then** Milvus 中的索引数据能够自动恢复并可用，无需重新构建

---

### User Story 2 - 向量相似度检索 (Priority: P1)

作为RAG系统的检索引擎，向量索引模块需要能够接收查询向量，并通过 Milvus 快速返回最相似的K个向量及其元数据。用户输入问题后，系统将问题向量化，然后通过向量索引模块找到最相关的文档片段。

**Why this priority**: 这是向量索引模块存在的核心价值，与P1的索引构建共同构成了完整的索引生命周期。

**Independent Test**: 可以通过提交一个查询向量，验证系统是否能在指定时间内返回TopK个最相似的结果，并验证相似度分数的准确性。

**Acceptance Scenarios**:

1. **Given** 已存在包含10000条向量的 Milvus 索引，**When** 提交一个查询向量并指定返回Top5结果，**Then** 系统在100ms内返回5个最相似的结果，每个结果包含向量ID、相似度分数和元数据
2. **Given** 用户提交查询向量，**When** 指定相似度阈值为0.8，**Then** 系统只返回相似度分数大于等于0.8的结果，即使不足K个
3. **Given** Milvus 索引中包含多个 Collection 的向量，**When** 用户指定特定 Collection 进行查询，**Then** 系统只返回该 Collection 内的相似向量

---

### User Story 3 - 索引更新与删除 (Priority: P2)

作为一个动态的知识库系统，向量索引需要支持增量更新。当用户添加新文档、修改或删除文档时，Milvus 索引应该能够相应地更新，而无需重建整个索引。

**Why this priority**: 这是生产环境必需的功能，但在MVP阶段可以通过重建索引的方式暂时替代。

**Independent Test**: 可以通过向现有 Milvus 索引添加新向量、更新特定向量、删除指定向量，验证这些操作是否成功且不影响检索性能。

**Acceptance Scenarios**:

1. **Given** 已存在一个包含1000条向量的 Milvus 索引，**When** 添加100条新向量，**Then** 索引在10秒内完成更新，新向量可立即被检索到
2. **Given** 用户需要更新某个文档对应的向量，**When** 提交更新请求（包含向量ID和新向量），**Then** Milvus 替换旧向量，后续检索使用新向量
3. **Given** 用户删除某个文档，**When** 提交删除请求（包含向量ID列表），**Then** 这些向量从 Milvus 索引中移除，后续检索不再返回这些结果

---

### User Story 4 - 索引持久化与恢复 (Priority: P2)

向量索引作为系统的核心数据结构，Milvus 提供原生的数据持久化能力。系统重启或故障恢复后，索引数据能够自动从 Milvus 中恢复。

**Why this priority**: 这对生产环境至关重要，Milvus 原生支持持久化简化了实现。

**Independent Test**: 可以通过构建索引、重启 Milvus 服务、验证索引恢复来测试。

**Acceptance Scenarios**:

1. **Given** 用户构建了一个包含50000条向量的 Milvus 索引，**When** Milvus 服务重启，**Then** 索引数据自动恢复，无需手动操作
2. **Given** Milvus 系统发生故障重启，**When** 系统恢复后尝试查询，**Then** 最后一次成功写入的数据都能被检索到
3. **Given** 用户需要将索引迁移到另一台 Milvus 服务器，**When** 使用 Milvus 的数据迁移工具，**Then** 索引在新服务器上正常工作，检索结果与原服务器一致

---

### User Story 5 - 多索引管理 (Priority: P3)

系统应支持创建和管理多个独立的 Milvus Collection，每个 Collection 对应不同的知识库或用户空间。用户可以在不同 Collection 间切换，或同时查询多个 Collection。

**Why this priority**: 这是面向多租户或多项目场景的高级功能，对单一用户的MVP不是必需的。

**Independent Test**: 可以通过创建多个命名 Collection、分别构建和查询、验证 Collection 间隔离性来测试。

**Acceptance Scenarios**:

1. **Given** 用户创建了3个不同的 Milvus Collection（"法律文档"、"技术手册"、"客服对话"），**When** 向每个 Collection 添加不同的向量数据，**Then** 每个 Collection 独立存储，互不干扰
2. **Given** 用户需要跨 Collection 检索，**When** 同时查询"法律文档"和"技术手册" Collection，**Then** 系统返回合并后的TopK结果，并标注每个结果的来源 Collection
3. **Given** 用户需要删除某个 Collection，**When** 执行删除操作，**Then** 该 Collection 及其数据被完全移除，其他 Collection 不受影响

---

### User Story 6 - 前端索引管理界面 (Priority: P1)

用户通过Web界面进行向量索引的创建和管理。界面采用左右分栏布局，左侧配置索引参数（向量化任务选择、索引算法选择），右侧查看索引结果和历史记录。

**Why this priority**: 这是用户与向量索引模块交互的主要入口，直接影响用户体验。

**Independent Test**: 可以通过UI自动化测试验证界面布局、交互流程和数据展示的正确性。

**Acceptance Scenarios**:

1. **Given** 用户进入向量索引页面，**When** 页面加载完成，**Then** 左侧显示配置区（向量化任务选择、索引算法选择），右侧显示双Tab（索引结果、历史记录）
2. **Given** 用户在左侧选择了向量化任务，**When** 下拉框展开，**Then** 显示所有已完成的向量化任务列表，包含任务名称和创建时间
3. **Given** 用户完成索引配置并点击"开始索引"，**When** Milvus 索引构建完成，**Then** 右侧"索引结果"Tab自动更新显示索引详情
4. **Given** 用户切换到"历史记录"Tab，**When** 点击某条历史记录的"查看详情"，**Then** 显示该索引的完整配置和统计信息
5. **Given** 用户在历史记录中选择删除某条记录，**When** 确认删除操作，**Then** 该记录从列表中移除，对应的 Milvus Collection 被清理

---

### User Story 7 - 混合检索基础能力 (Priority: P1)

作为RAG系统的检索引擎，向量索引模块需要支持稠密+稀疏双路向量召回，并通过 RRF 粗排融合和 Reranker 精排重排序，提升检索精度。当稀疏向量不可用时，系统自动降级到纯稠密检索模式。

**Why this priority**: 混合检索是提升 RAG 检索质量的核心能力，直接影响最终问答效果。

**Independent Test**: 创建含稠密+稀疏向量的 Collection，执行混合检索，验证 RRF 融合 + Reranker 精排流程；移除稀疏向量后验证自动降级。

**Acceptance Scenarios**:

1. **Given** 已存在包含稠密和稀疏向量的 Milvus Collection，**When** 提交混合检索请求（包含 query_vector、sparse_vector 和 query_text），**Then** 系统返回经 RRF 粗排 + Reranker 精排后的 Top-K 结果，每个结果包含 rrf_score 和 reranker_score，search_mode 为 `hybrid`
2. **Given** Collection 包含稠密和稀疏向量，**When** 提交的查询稀疏向量为空或缺失，**Then** 系统自动降级到纯稠密检索模式，search_mode 返回 `dense_only`，检索服务不中断
3. **Given** 已配置 Reranker 服务，**When** 对 20 条候选集执行精排，**Then** 精排耗时在 100ms 以内（P95），返回的 reranker_score 可用于结果排序
4. **Given** Reranker 服务不可用，**When** 提交混合检索请求，**Then** 系统跳过精排步骤，直接返回 RRF 粗排结果，并在响应中标注 reranker_available=false

---

### User Story 8 - 前端混合检索界面 (Priority: P2)

用户通过 Web 界面切换纯稠密/混合检索模式，配置 Reranker 参数（top_n、top_k），查看混合检索结果（包含 search_mode 标签、rrf_score、reranker_score 和耗时指标）。

**Why this priority**: 前端需要透出混合检索能力，让用户感知检索模式和精排效果。

**Independent Test**: 在 VectorSearch 组件中切换到"混合检索"模式，发起检索请求，验证结果列表展示 search_mode 标签、reranker_score 分数和耗时指标。

**Acceptance Scenarios**:

1. **Given** 用户进入向量检索页面，**When** 切换检索模式为"混合检索"，**Then** 界面显示额外的 Reranker 参数配置（top_n、top_k），检索请求发送到 hybrid-search 端点
2. **Given** 用户执行混合检索，**When** 结果返回，**Then** 结果列表中每条记录显示 search_mode 标签（hybrid/dense_only）、rrf_score、reranker_score 和耗时指标
3. **Given** 用户在索引创建页面，**When** 勾选"启用稀疏向量"复选框，**Then** 创建的 Collection 包含 sparse_embedding 字段，IndexList 和 IndexHistory 中显示 has_sparse 标识

---

### Edge Cases

- 当提交的向量维度与 Milvus Collection 定义的维度不匹配时，系统如何处理？
- 当 Milvus Collection 为空时执行查询，系统返回什么？
- 当查询的K值大于 Milvus Collection 中的向量总数时，系统如何响应？
- 当 Milvus 服务不可用时，系统如何处理并向用户提示？
- 当多个并发请求同时修改同一个 Collection 时，如何保证数据一致性？
- 当向量数据包含NaN或Inf值时，索引构建是否应该拒绝？
- 当用户尝试删除不存在的向量ID时，系统应该报错还是静默忽略？ → **静默忽略**（幂等性设计，返回成功状态）
- 当 Milvus 连接超时时，系统如何进行重试和错误处理？ → **指数退避重试**（间隔 1s → 2s → 4s，最多3次后返回错误）
- 当 Reranker 服务不可用时，混合检索应如何处理？ → **跳过精排**，直接返回 RRF 粗排结果，响应中标注 reranker_available=false
- 当 RRF 融合参数 k 设置为非正数时，系统如何响应？ → **参数验证拒绝**，返回 ERR_VALIDATION 错误
- 当 query_text 为空但启用了 Reranker 时，系统如何处理？ → **跳过 Reranker 精排**，直接返回 RRF 粗排结果（Reranker 需要文本输入）
- 当稀疏向量全部权重为零时，是否视为有效？ → **视为无效**，触发降级到纯稠密检索
- 当推荐规则均无法匹配用户向量特征组合（如罕见维度/模型组合）时？ → **使用兜底默认值**（HNSW + COSINE），显示"未精确匹配推荐规则，已使用通用默认值"提示标签
- 当用户选择向量化任务后推荐延迟超过 500ms 时？ → **仍展示推荐值**，但不阻塞用户操作，用户可先行手动选择

## Requirements *(mandatory)*

### Functional Requirements

#### 前端界面需求

- **FR-UI-001**: 前端采用左右分栏布局，左侧为索引配置区，右侧为结果展示区
- **FR-UI-002**: 左侧配置区包含：向量化任务选择（下拉框）、索引算法选择（FLAT/IVF_FLAT/IVF_SQ8/IVF_PQ/HNSW）
- **FR-UI-003**: 右侧展示区包含两个Tab：「索引结果」和「历史记录」
- **FR-UI-004**: 历史记录Tab支持查看索引详情和删除记录操作
- **FR-UI-005**: 界面样式与文档向量化模块保持一致（使用 TDesign Vue Next 组件库默认主题，布局参考现有文档向量化模块的左右分栏样式）
- **FR-UI-006**: 索引构建过程中，前端需展示实时进度条（百分比 + 已处理/总数）和状态文字提示
- **FR-UI-007**: 索引构建失败时，前端需通过错误弹窗（Modal/Alert）展示错误类型、详细错误信息和建议操作

#### 数据源与集成

- **FR-DS-001**: 系统必须支持从已完成的向量化任务中选择数据源，通过下拉框展示可用的向量化任务列表
- **FR-DS-002**: 选择向量化任务后，系统自动获取对应的向量数据（包括向量值、维度、元数据）

#### 向量数据库支持

- **FR-DB-001**: 系统必须支持 Milvus 向量数据库作为唯一存储后端
- **FR-DB-002**: 系统必须通过 Milvus SDK（pymilvus）与 Milvus 服务进行交互
- **FR-DB-003**: 系统必须支持 Milvus Collection 的创建、查询、更新和删除操作

#### 索引算法支持

- **FR-ALG-001**: 系统必须支持 FLAT 索引算法（暴力搜索，精确匹配）
- **FR-ALG-002**: 系统必须支持 IVF_FLAT 索引算法（倒排文件索引）
- **FR-ALG-003**: 系统必须支持 IVF_PQ 索引算法（倒排文件 + 乘积量化）
- **FR-ALG-004**: 系统必须支持 HNSW 索引算法（层次化可导航小世界图）
- **FR-ALG-004a**: 系统必须支持 IVF_SQ8 索引算法（倒排文件 + 标量量化，节省约75%内存）
- **FR-ALG-005**: 用户可通过前端下拉框选择索引算法类型（适用于稠密向量索引）
- **FR-ALG-006**: 稀疏向量字段必须使用 SPARSE_INVERTED_INDEX 索引类型，度量方式为 IP（内积），由系统自动创建，无需用户手动选择

#### 智能推荐引擎

- **FR-REC-001**: 用户选择向量化任务后，系统必须根据向量特征（维度、数据量、Embedding 模型类型）自动填充推荐的索引算法和度量类型，推荐值预填入对应下拉框，用户可手动覆盖
- **FR-REC-002**: 推荐的索引算法和度量类型旁需显示推荐理由标签（如"基于 BGE-M3 1024维 + 5000条向量推荐"），帮助用户理解推荐依据
- **FR-REC-003**: 智能推荐引擎采用基于数据量的分层规则匹配策略（业界主流方案），决策优先级为：数据量 → Embedding 模型类型，具体规则如下：
  - 数据量 < 10,000：推荐 **FLAT**（小数据量暴力搜索保证 100% 精确召回）
  - 数据量 10,000 ~ 500,000：推荐 **HNSW**（图索引兼顾高召回率与低延迟，业界首选，Milvus/Qdrant/Weaviate 默认算法）
  - 数据量 500,000 ~ 5,000,000：推荐 **IVF_SQ8**（标量量化在精度损失极小的情况下节省约 75% 内存）
  - 数据量 ≥ 5,000,000：推荐 **IVF_PQ**（乘积量化大幅压缩内存占用）
  - 度量类型：BGE 系列（归一化输出）→ **COSINE**；Qwen 系列（归一化输出）→ **COSINE**；OpenAI Ada（归一化输出）→ **COSINE**；Cohere（归一化输出）→ **COSINE**；未识别/自定义模型 → **L2**（通用安全默认值）
- **FR-REC-004**: 推荐规则应以可配置的规则表形式存储，便于后续扩展和调整，无需修改代码即可更新推荐策略
- **FR-REC-005**: 当推荐规则无法匹配用户的向量特征组合时，系统使用兜底默认推荐（**HNSW** + **COSINE**），并显示提示标签"未精确匹配推荐规则，已使用通用默认值"，用户仍可手动修改
- **FR-REC-006**: 系统需记录用户对推荐值的采纳/修改行为日志（推荐值、最终选择值、是否修改），用于推荐采纳率指标统计

#### 核心功能需求

- **FR-001**: 系统必须支持接收向量数据并通过 Milvus 构建索引，向量维度可配置（支持 128、256、512、768、1024、1536、2048、3072、4096）
- **FR-002**: 系统必须支持基于余弦相似度、欧氏距离或点积的相似度计算方法，并允许用户选择
- **FR-003**: 系统必须支持TopK查询，用户可指定返回结果的数量（K值）
- **FR-004**: 系统必须支持相似度阈值过滤，只返回相似度分数高于指定阈值的结果
- **FR-005**: 系统必须在索引构建时验证向量数据的有效性（维度一致性、数值有效性）
- **FR-006**: 系统必须支持向量的元数据存储，**必需字段**：`doc_id`（文档ID）、`chunk_index`（分块索引）、`created_at`（创建时间）；**可选字段**：文本内容、来源文件名等自定义字段
- **FR-007**: 系统必须支持增量索引更新，包括添加、更新和删除向量操作
- **FR-008**: 系统依赖 Milvus 原生的持久化机制，无需单独实现持久化逻辑
- **FR-009**: 系统必须支持多个 Milvus Collection 的创建和管理，每个 Collection 相互隔离
- **FR-010**: 系统必须提供索引统计信息查询接口，包括向量数量、索引大小、维度等
- **FR-011**: 系统必须在查询失败时返回明确的错误信息和错误代码
- **FR-012**: 系统必须支持批量向量查询，一次请求可提交多个查询向量
- **FR-013**: 系统必须记录关键操作日志，包括索引创建、更新、查询等操作
- **FR-014**: 系统必须支持 Milvus 原生的数据迁移能力，以便在不同环境间迁移（由 Milvus 原生 backup/restore 工具提供，无需额外实现）
- **FR-015**: 系统必须支持并发访问并保证数据一致性，利用 Milvus 原生的并发控制机制（由 Milvus 内置多读多写并发控制保证，无需额外实现）

#### 混合检索与精排

- **FR-HYB-001**: 系统必须支持混合检索模式，同时使用稠密向量（FLOAT_VECTOR）和稀疏向量（SPARSE_FLOAT_VECTOR）进行双路召回
- **FR-HYB-002**: 系统必须使用 Milvus 原生 RRFRanker（Reciprocal Rank Fusion）对稠密和稀疏两路检索结果进行粗排融合
- **FR-HYB-003**: 系统必须集成 qwen3-reranker-4b 模型，对 RRFRanker 融合后的候选集（Top-N）进行精排重排序，输出最终 Top-K 结果
- **FR-HYB-004**: 精排阶段的候选集大小（N）应可配置，默认为 20
- **FR-HYB-005**: 当稀疏向量为空或不可用时，系统必须自动降级到纯稠密向量检索模式（跳过 RRF 融合），直接将稠密检索 Top-N 结果送入 Reranker 精排，确保检索服务不中断

### Key Entities

- **VectorIndex（向量索引）**: 代表一个完整的 Milvus Collection，包含 Collection 名称、向量维度、索引算法类型、创建时间、向量数量等属性
- **Vector（向量）**: 代表单个向量数据点，包含唯一ID、向量值（浮点数数组）、元数据（键值对）等属性
- **QueryResult（查询结果）**: 代表单个查询的结果项，包含向量ID、相似度分数、元数据等属性
- **IndexMetadata（索引元数据）**: 包含 Milvus Collection 的统计信息，如向量总数、索引占用空间、最后更新时间等
- **RecommendationRule（推荐规则）**: 智能推荐引擎的决策规则实体，包含匹配条件（向量维度范围、数据量范围、Embedding 模型类型列表）和输出推荐（推荐索引算法、推荐度量类型、推荐理由文案），规则按优先级排序匹配，首个命中规则生效；当所有规则均不匹配时，使用兜底默认值（HNSW + COSINE）

### Non-Functional Considerations

- **性能（稠密检索）**: 对于10000条向量的 Milvus 索引，单次纯稠密 TopK 查询响应时间应在100ms以内（P95）
- **性能（混合检索）**: 混合检索 Top-K 查询（含 RRF 粗排 + Reranker 精排）总耗时应在200ms以内（P95）
- **性能（Reranker 精排）**: qwen3-reranker-4b 对 20 条候选集的精排推理耗时应在100ms以内（P95）
- **可扩展性**: Milvus 索引应支持从1000到100万级别的向量规模
- **可靠性**: Milvus 原生支持数据持久化，数据不应因系统故障而丢失
- **并发性**: 利用 Milvus 原生的并发控制，支持多读多写操作
- **可用性**: 系统应能检测 Milvus 服务状态，在服务不可用时提供友好的错误提示
- **可用性（降级）**: 当稀疏向量不可用或 Reranker 服务异常时，系统自动降级到纯稠密检索模式，确保检索服务不中断
- **性能（智能推荐）**: 从用户选择向量化任务到推荐值填充完成，推荐延迟 ≤ 500ms（P95）

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 对于包含10000条向量的 Milvus 索引，单次TopK查询（K=5）的响应时间在100ms以内（95%分位）
- **SC-002**: 索引构建速度达到每秒1000条向量以上（对于1536维向量）
- **SC-003**: 系统支持至少10个并发查询请求，总体吞吐量达到50 QPS（queries per second）
- **SC-004**: Milvus 服务重启后，索引数据自动恢复可用，无需人工干预
- **SC-005**: 检索准确率：返回的TopK结果与暴力搜索的重叠率达到95%以上（对于近似索引算法）
- **SC-006**: 增量更新操作（添加/删除1000条向量）在10秒内完成，不影响正在进行的查询
- **SC-007**: 系统在处理无效输入时100%返回明确的错误信息，不发生崩溃
- **SC-008**: Milvus 连接失败时，系统能在3次重试内恢复或向用户提供明确的错误提示
- **SC-009**: 混合检索 Top-K 查询（含 RRF 粗排 + Reranker 精排，候选集 N=20）的总响应时间在200ms以内（P95）
- **SC-010**: qwen3-reranker-4b 对 20 条候选集的精排推理耗时在100ms以内（P95）
- **SC-011**: 稀疏向量为空或 Reranker 不可用时，系统自动降级到纯稠密检索，降级响应时间不超过纯稠密检索的110%
- **SC-012**: 智能推荐引擎的推荐采纳率 ≥ 80%（用户未手动修改推荐值的比例，统计周期为上线后首月）
- **SC-013**: 智能推荐引擎从用户选择向量化任务到推荐值填充完成的延迟 ≤ 500ms（P95）

## Assumptions

- 假设向量数据已经通过Embedding模型（BGE-M3）生成，本模块不负责文本到向量的转换
- ~~假设 Embedding 模块已启用 BGE-M3 的双路输出能力（`return_dense=True, return_sparse=True`），一次推理同时生成稠密向量和稀疏向量~~ [Updated: 2026-02-25] 假设稀疏向量由 BM25 算法在索引构建阶段独立生成，不依赖 BGE-M3 的 sparse 输出能力，无需 GPU 或本地大模型
- ~~假设单个 Milvus Collection 支持多种维度的向量字段（动态命名 dense_dim{N}），新维度通过 Schema 动态扩展自动添加，无需重建 Collection~~ [Updated: 2026-02-25] 假设采用 Dify 方案的「逻辑与物理分层」架构：对外暴露逻辑知识库名（如 default_collection），底层按「知识库 + 维度」拆分为多个物理 Collection（如 default_collection_dim1024），每个物理 Collection 只包含一个固定维度的 embedding 字段，从根源解决维度冲突问题
- **假设统一使用 Milvus 作为唯一的向量数据库后端**
- 假设 Milvus 运行在独立服务器或 Docker 容器中，通过网络 API 访问
- 假设向量数据的元数据以 JSON 格式存储，不超过1KB每条
- 假设默认使用余弦相似度（L2归一化 + 内积）作为相似度度量方法
- 假设 Milvus 提供原生的数据持久化和并发控制能力
- 假设生产环境已部署 Milvus 服务，开发环境可使用 Docker 部署的 Milvus

## Dependencies

- 依赖向量Embedding服务提供标准化的向量数据（稠密向量 FLOAT_VECTOR，由嵌入模型 API 输出；稀疏向量 SPARSE_FLOAT_VECTOR，由 BM25 算法在索引构建阶段独立生成）
- 依赖文档管理模块提供文档的元数据信息
- **核心依赖**: Milvus 向量数据库（2.x 版本）及其 Python SDK（pymilvus）
- 依赖 Milvus 服务的网络可达性和可用性
- 依赖 qwen3-reranker-4b 模型（通过远程 API 调用），用于混合检索的精排重排序

## Out of Scope

- 向量Embedding生成（由独立的Embedding模块负责，~~该模块需升级以支持 BGE-M3 双路输出~~ [Updated: 2026-02-25] 稀疏向量由 BM25 独立生成，无需 Embedding 模块改动）
- 分布式向量索引（单机 Milvus 版本优先，可选 Milvus Cluster）
- GPU加速的向量检索（依赖 Milvus 配置）
- 索引的自动分片和负载均衡（由 Milvus Cluster 提供）
- 细粒度的权限控制和多租户隔离
- 向量数据的加密存储
- 实时索引更新通知机制
- **FAISS 本地索引支持**（本版本已移除）

## Change Log

| 日期 | 类型 | 变更内容 | 影响需求 |
|------|------|----------|----------|
| 2026-02-06 | BEHAVIOR_CHANGE | [VIBE] 实现混合检索全部 Phase 9-12 (T047-T072)：后端基础设施（FlagEmbedding 依赖、Reranker 配置、稀疏向量工具、RerankerService）、Milvus Provider 扩展（稀疏字段、SPARSE_INVERTED_INDEX、hybrid_search + RRFRanker、自动降级）、API 端点集成（hybrid-search 端点、timing 指标、结果持久化）、前端扩展（检索模式切换、Reranker 参数配置、结果展示 search_mode/rrf_score/reranker_score、enable_sparse 复选框、has_sparse badge） | US7, US8, FR-HYB-001~005, SC-009, SC-010, SC-011 |
| 2026-02-06 | BEHAVIOR_CHANGE | [VIBE] 实现智能推荐引擎 (T018-T020, T033-T035, T039-T040)：后端 RecommendationEngine 分层规则匹配服务（recommendation_service.py）、推荐行为日志记录（RecommendationLogService）、3 个推荐 API 端点（POST /recommend, POST /recommend/log, GET /recommend/stats）、RecommendationRule + RecommendationLog SQLAlchemy 模型和 Pydantic schemas、前端 RecommendBadge.vue 推荐理由标签组件、RecommendFallback.vue 兜底提示组件、IndexCreate.vue 推荐自动填充集成、Pinia store 推荐状态管理、推荐规则 JSON 配置（4 条默认规则）、数据库迁移脚本 008_recommendation.sql | US1, US6, FR-REC-001~006, SC-012 |
| 2026-02-06 | BEHAVIOR_CHANGE | [VIBE] 完成全部 74 个任务 (T001-T074)：Phase 3-11 全部完成。新增前端组件 IndexProgress.vue（索引进度展示）、IndexList.vue（索引列表+搜索+has_sparse badge）、IndexHistory.vue（历史记录分页+删除）。确认已有 service 层代码满足所有需求：vector_index_service.py（索引构建/进度追踪/维度校验/向量CRUD/多Collection联合查询）、search_service.py（检索/阈值过滤/批量查询）、milvus_provider.py（hybrid_search/稀疏降级/连接恢复）、reranker_service.py（精排/降级）。新增 database.py 迁移执行逻辑（推荐表初始化）。新增性能基准测试 test_performance.py（SC-002/SC-003/SC-005）和边界测试 test_edge_cases.py（5个边界场景验证） | ALL US1-US8, FR-*, SC-* |
| 2026-02-25 | BEHAVIOR_CHANGE | [VIBE] 稀疏向量生成方式变更：从 "BGE-M3 一次推理双路输出" 变更为 "API dense + BM25 sparse" 方案。新增 BM25SparseService（jieba 分词 + 自建词表 + IDF 持久化），在索引构建阶段（create_index_from_embedding）自动生成 sparse 向量，在混合检索时（hybrid_search）自动为查询生成 sparse 向量。新增 jieba 依赖，IndexConfig 增加 enable_sparse 字段，CreateIndexFromEmbeddingRequest 增加 enable_sparse 参数（默认 true）。优势：零模型依赖、纯 CPU 毫秒级计算、与现有 Milvus SPARSE_FLOAT_VECTOR 完全兼容 | US7, FR-HYB-001~005, Assumptions, Dependencies, Out of Scope |
| 2026-02-25 | BEHAVIOR_CHANGE + DATA_STRUCTURE | [VIBE] Collection 管理重构：从"一个文档对应一个 Collection"改为"一个知识库对应一个 Collection"。新增默认 Collection（default_collection）概念，向量化文档创建索引时默认追加到 default_collection，同时预留多 Collection 能力。VectorIndex 模型新增 `collection_name` 字段（默认值 'default_collection'）。MilvusProvider 新增 `ensure_collection_exists` 方法（幂等创建/复用 Collection）和 `get_collection_names` 方法。`create_index_from_embedding` 从"每次创建新 Collection"改为"向已有 Collection 追加向量"。新增 `get_collections` API 端点。前端 IndexCreate.vue 新增 Collection 选择器（支持选择已有/创建新 Collection）。数据库迁移自动添加 collection_name 列。 | US1-US8, FR-IDX-001~003, data-model |
| 2026-02-25 | DATA_STRUCTURE | [VIBE] 引入 Milvus Partition Key 分区优化：Collection Schema 新增 `doc_id` 顶级字段并标记为 `is_partition_key=True`，Milvus 自动按文档 ID 哈希到不同分区（默认 64 个分区），查询时加 `filter='doc_id == "xxx"'` 可自动路由到对应分区，避免全 Collection 扫描。`doc_id` 从 metadata JSON 中提升为独立字段。`add_vectors` / `add_vectors_with_sparse` 方法新增 `doc_ids` 参数。`_load_vectors_from_embedding` 返回 `doc_ids` 列表。搜索结果的 `output_fields` 默认包含 `doc_id`。需要删除旧 Collection 并重新创建（Schema 变更不支持热更新）。 | data-model, US1-US8, FR-IDX-001~003 |
| 2026-02-25 | BEHAVIOR_CHANGE + DATA_STRUCTURE | [VIBE] ~~多维度向量字段架构：从固定单一 `embedding` 字段改为按维度动态命名的多向量字段（`dense_dim1024`、`dense_dim4096` 等）~~ [Updated: 2026-02-25] 参考 Dify 方案重构为「逻辑与物理分层」架构：对外暴露逻辑知识库名（如 default_collection），底层按「知识库 + 维度」拆分为多个物理 Collection（如 default_collection_dim1024、default_collection_dim2048）。每个物理 Collection 只包含一个固定的 `embedding` 字段，从根源解决 Milvus 不支持动态添加 FLOAT_VECTOR 字段的问题。`vector_config.py` 新增 `get_physical_collection_name` / `parse_physical_collection_name` 工具函数。MilvusProvider 改造：`ensure_collection_exists` 自动创建维度专属物理 Collection；`_create_collection_schema` 恢复为固定 `embedding` 字段名；`add_vectors`/`add_vectors_with_sparse` 移除零向量填充逻辑；`search`/`hybrid_search` 维度校验改为匹配 Collection 维度。VectorIndex 模型新增 `physical_collection_name` 字段。`get_collections` 改为按逻辑知识库聚合展示。数据库迁移自动添加 `physical_collection_name` 列并回填历史记录。 | US1-US8, FR-001, FR-DB-001~003, Assumptions |
