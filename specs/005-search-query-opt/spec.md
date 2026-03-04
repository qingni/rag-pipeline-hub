# Feature Specification: 检索查询模块（优化版）

**Feature Branch**: `005-search-query-opt`  
**Created**: 2026-02-26  
**Status**: Ready
**Input**: User description: "基于 005-search-query 进行优化，整合 004-vector-index-opt 中向量搜索相关能力（混合检索、RRF 融合、Reranker 精排、BM25 稀疏向量查询、智能降级等）"

## 版本变更说明

本版本基于 `005-search-query` 进行优化，主要变更：

- **整合混合检索能力**：从 004-vector-index-opt 同步稠密+稀疏双路召回 → RRF 粗排 → Reranker 精排的完整检索链路
- **集成 BM25 稀疏向量查询**：查询时自动通过 BM25 算法（jieba 分词）生成稀疏查询向量
- **智能降级策略**：稀疏向量不可用时自动降级为纯稠密检索，Reranker 不可用时跳过精排
- **多 Collection 联合搜索**：支持跨知识库搜索（最多5个 Collection），各 Collection 粗排候选集合并后统一 Reranker 精排全局排序
- **Reranker 精排集成**：使用 qwen3-reranker-4b 模型对候选集进行精排重排序

## Clarifications

### Session 2026-02-26

- Q: 用户进入检索查询页面时，默认的检索模式应该是什么？ → A: 系统默认使用混合检索（hybrid），运行时自动降级。用户无需手动选择检索模式。当稀疏向量不可用时（Collection 无稀疏字段、BM25 统计数据缺失、稀疏向量生成失败等任一原因），系统自动降级为纯稠密检索（dense_only），确保检索服务不中断。前端配置面板以只读状态文本提示当前实际使用的检索模式。理由：①检索模式是基础设施细节而非用户关心的功能选项；②业内主流搜索系统（Elasticsearch、Pinecone、Weaviate、LlamaIndex 等）均采用「乐观尝试 + 自动降级」策略，而非前置多步校验；③与现有代码实现一致（milvus_provider.py 中已是运行时判断 + 降级逻辑）
- Q: BM25 统计数据在查询时的加载方式应该是什么？ → A: 每个 Collection/Index 的 BM25 统计数据独立管理，首次查询时懒加载并缓存到内存（避免大 Collection 场景下的内存浪费，同时保证后续查询性能）
- Q: RRF 融合参数 k 是否需要在前端暴露给用户调整？ → A: 前端不暴露 RRF k 参数，仅在后端配置文件中可调整，默认 k=60（业内标准默认值，来源于 RRF 原始论文 Cormack et al. 2009，Elasticsearch/Milvus 等均采用此值）。理由：①有 Reranker 精排兜底，k 值对最终结果敏感度低；②k 在 40~80 范围内召回率波动 <2%；③暴露给普通用户容易造成困惑
- Q: 多 Collection 联合搜索的结果合并应该基于哪个分数排序？ → A: 各 Collection 的 RRF 粗排候选集合并后，统一送入一次 Reranker 精排，用 reranker_score 做全局排序。理由：①reranker_score 来自同一模型的同一次推理，分数天然具有全局可比性；②只调用一次 Reranker（候选集 = 各 Collection Top-N 的合集），性能最优；③与 Elasticsearch 跨索引搜索的先各分片召回再统一排序策略一致
- Q: 多 Collection 联合搜索时，Reranker 候选集大小（Top-N）是否需要区分单/多 Collection 场景？ → A: 不区分，各 Collection 统一使用相同的 Top-N（默认 N=20），通过限制联合搜索的最大 Collection 数量（max_collections=5）来控制 Reranker 输入上限（最大 5×20=100 条）。理由：①与 Elasticsearch/Milvus/LlamaIndex 等业内主流系统一致，各源统一使用相同 N 值，不做按比例分配；②实现简单，各 Collection 直接复用单 Collection 的 Top-N 参数；③每个 Collection 保持完整召回配额，不因 Collection 数量变化而被截断；④通过 max_collections 限制而非按比例缩减来控制性能上限

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 语义搜索查询 (Priority: P1)

用户在搜索框中输入自然语言问题或关键词，系统将查询文本转换为向量，通过已构建的向量索引进行相似度检索，返回最相关的文档片段列表。这是RAG系统的核心检索能力。

**Why this priority**: 这是搜索查询模块的核心功能，是用户与知识库交互的主要入口，直接决定了RAG系统的可用性。

**Independent Test**: 可以通过输入一个问题（如"什么是向量数据库？"），验证系统是否返回相关的文档片段，并检查返回结果的相关性评分。

**Acceptance Scenarios**:

1. **Given** 用户已有构建好的向量索引（包含1000个文档片段），**When** 用户输入查询"如何使用Python连接数据库"，**Then** 系统在2秒内返回Top10相关文档片段，每个结果包含文本内容、相似度分数和来源信息
2. **Given** 用户输入查询文本，**When** 查询文本为空或仅包含空格，**Then** 系统提示"请输入有效的查询内容"
3. **Given** 用户输入查询，**When** 索引中没有相似度高于阈值的结果，**Then** 系统返回空列表并提示"未找到相关内容，请尝试其他关键词"

---

### User Story 2 - 混合检索（稠密+稀疏双路召回） (Priority: P1)

用户通过 Web 界面发起混合检索，系统自动使用稠密向量（语义匹配）和稀疏向量（关键词匹配，BM25）双路召回，通过 RRF 粗排融合 + Reranker 精排重排序，返回高质量的检索结果。当稀疏向量不可用时，系统自动降级到纯稠密检索模式。

**Why this priority**: 混合检索是提升 RAG 检索质量的核心能力，同时覆盖语义和关键词匹配场景，直接影响最终问答效果。

**Independent Test**: 创建含稠密+稀疏向量的 Collection，执行混合检索，验证 RRF 融合 + Reranker 精排流程；移除稀疏向量后验证自动降级。

**Acceptance Scenarios**:

1. **Given** 已存在包含稠密和稀疏向量的 Milvus Collection，**When** 用户输入查询文本发起混合检索，**Then** 系统自动生成稠密查询向量（Embedding 服务）和稀疏查询向量（BM25），经 RRF 粗排 + Reranker 精排后返回 Top-K 结果，每个结果包含 rrf_score 和 reranker_score，search_mode 为 `hybrid`
2. **Given** Collection 包含稠密和稀疏向量，**When** BM25 统计数据不存在或查询稀疏向量生成失败，**Then** 系统自动降级到纯稠密检索模式，search_mode 返回 `dense_only`，检索服务不中断
3. **Given** 已配置 Reranker 服务，**When** 对 20 条候选集执行精排，**Then** 精排耗时在 100ms 以内（P95），返回的 reranker_score 可用于结果排序
4. **Given** Reranker 服务不可用，**When** 提交混合检索请求，**Then** 系统跳过精排步骤，直接返回 RRF 粗排结果，并在响应中标注 reranker_available=false

---

### User Story 3 - 搜索结果展示与交互 (Priority: P1)

用户在前端界面查看搜索结果，结果以卡片列表形式展示，每个卡片显示文档片段的核心内容、相似度分数（或 RRF 分数/Reranker 分数）、来源文档名称、检索模式标签。用户可以点击查看完整内容或跳转到原文档。

**Why this priority**: 良好的结果展示直接影响用户体验，是搜索功能可用性的关键。

**Independent Test**: 可以通过执行搜索后验证结果卡片是否正确显示所有必要信息，点击操作是否正常响应。

**Acceptance Scenarios**:

1. **Given** 搜索返回了5条结果，**When** 结果页面加载完成，**Then** 显示5张结果卡片，每张包含：文本摘要（最多200字）、相似度分数（百分比形式）、来源文档名、文档片段位置
2. **Given** 用户执行混合检索，**When** 结果返回，**Then** 结果列表中每条记录显示 search_mode 标签（hybrid/dense_only）、rrf_score、reranker_score 和耗时指标
3. **Given** 用户点击某个结果卡片的"查看详情"，**When** 详情弹窗打开，**Then** 显示完整的文档片段内容、元数据信息和相关上下文
4. **Given** 搜索结果超过10条，**When** 用户滚动到底部，**Then** 自动加载更多结果（分页加载）

---

### User Story 4 - 搜索配置与过滤 (Priority: P2)

用户可以配置搜索参数，包括选择目标索引/Collection、设置返回结果数量（TopK）、调整相似度阈值、配置 Reranker 参数（top_n、top_k）。检索模式由系统自动决定：默认使用混合检索，稀疏向量不可用时自动降级为纯稠密检索，用户无需手动选择。高级用户可以通过这些配置优化搜索效果。

**Why this priority**: 配置功能增强了搜索的灵活性，但基础搜索功能可以使用默认配置运行。

**Acceptance Scenarios**:

1. **Given** 用户打开搜索配置面板，**When** 面板显示，**Then** 展示以下可配置项：目标 Collection（下拉选择，按逻辑知识库聚合，每个选项显示知识库名、文档数量、向量数量）、返回数量（1-100）、相似度阈值（0-1）、Reranker top_n 和 top_k 参数。同时显示只读状态提示，标注当前实际检索模式（如「当前：混合检索」或「当前：纯稠密检索」），该状态在首次查询执行后根据运行时实际结果更新 [Updated: 2026-02-26]
2. **Given** 用户设置TopK=5且相似度阈值=0.7，**When** 执行搜索，**Then** 最多返回5条结果，且每条结果的相似度分数≥0.7
3. **Given** 用户选择了某个 Collection 并执行查询，**When** 系统运行时检测到稀疏向量可用，**Then** 实际使用混合检索，状态提示更新为「混合检索」，并显示额外的 Reranker 参数配置（top_n、top_k）；若稀疏向量不可用，则自动降级为纯稠密检索，状态提示更新为「纯稠密检索」

---

### User Story 5 - 搜索历史记录 (Priority: P2)

系统记录用户的搜索历史，用户可以查看历史搜索记录、快速重复执行历史查询、清除历史记录。这提升了用户的使用效率和体验。

**Why this priority**: 历史记录是提升用户体验的增强功能，核心搜索功能不依赖它。

**Acceptance Scenarios**:

1. **Given** 用户执行了一次搜索，**When** 搜索完成，**Then** 该查询自动保存到搜索历史，包含查询文本、时间戳、检索模式、结果数量
2. **Given** 用户打开搜索历史面板，**When** 点击某条历史记录，**Then** 自动填充查询框并执行搜索
3. **Given** 用户点击"清除历史"按钮，**When** 确认操作，**Then** 所有搜索历史被清除

---

### User Story 6 - 多 Collection 联合搜索 (Priority: P3)

用户可以选择多个 Milvus Collection 进行联合搜索，系统并行在各 Collection 中分别执行检索（混合检索时各自完成 RRF 粗排），将各 Collection 的粗排候选集合并后统一送入一次 Reranker 精排，用 reranker_score 做全局排序返回 Top-K。这支持跨知识库的统一检索场景。

**Why this priority**: 这是高级功能，适用于多知识库场景，单 Collection 搜索已能满足基本需求。

**Acceptance Scenarios**:

1. **Given** 用户选择了"技术文档"和"产品手册"两个 Collection，**When** 执行联合搜索，**Then** 系统并行在两个 Collection 中各自完成 RRF 粗排，合并候选集后统一经 Reranker 精排，返回按 reranker_score 全局排序的结果
2. **Given** 联合搜索返回结果，**When** 查看结果列表，**Then** 每条结果明确标注来源 Collection 名称
3. **Given** 用户设置TopK=10进行联合搜索，**When** 两个 Collection 各有足够结果，**Then** 返回合并后的Top10，而非每个 Collection 各返回10条
4. **Given** Reranker 不可用，**When** 执行多 Collection 联合搜索，**Then** 系统将各 Collection 的 RRF 粗排候选集合并后按 rrf_score 全局排序返回结果，响应中标注 reranker_available=false

---

### Edge Cases

| 边缘情况 | 处理策略 |
|----------|----------|
| 查询文本过长（超过2000字符） | 前端输入框限制最大长度，后端返回 400 错误 "查询文本超过最大长度限制" |
| 选择的 Collection 不存在或已删除 | 返回 404 错误 "所选 Collection 不存在或已被删除"，前端刷新列表 |
| Embedding 服务不可用 | 返回 503 错误 "向量化服务暂时不可用，请稍后重试"，记录错误日志 |
| 搜索请求超时（>30秒） | 中断请求，返回 504 错误 "搜索请求超时，请缩小搜索范围或稍后重试" |
| 用户快速连续发起多次搜索 | 前端实现 300ms 防抖，后端取消前一个未完成的请求 |
| 相似度阈值过高导致无结果 | 返回空列表，提示 "未找到相关内容，建议降低相似度阈值后重试" |
| Reranker 服务不可用 | 跳过精排，直接返回 RRF 粗排结果，响应中标注 reranker_available=false |
| RRF 融合参数 k 设置为非正数 | 参数验证拒绝，返回 ERR_VALIDATION 错误 |
| query_text 为空但启用了 Reranker | 跳过 Reranker 精排，直接返回 RRF 粗排结果（Reranker 需要文本输入） |
| 稀疏向量全部权重为零 | 视为无效，触发降级到纯稠密检索 |
| BM25 统计数据文件缺失 | 降级到纯稠密检索模式，记录警告日志 |
| 多 Collection 联合搜索中某个 Collection 查询失败 | 跳过失败的 Collection，返回其他成功 Collection 的结果并标注部分失败 |

## Requirements *(mandatory)*

### Functional Requirements

#### 前端界面需求

- **FR-UI-001**: 搜索页面顶部提供搜索输入框，支持回车键或点击按钮触发搜索
- **FR-UI-002**: 搜索结果以卡片列表形式展示，支持分页或无限滚动加载
- **FR-UI-003**: 每个结果卡片显示：文本摘要、相似度分数（百分比）、来源文档名、操作按钮（查看详情）
- **FR-UI-004**: 混合检索结果卡片额外显示：search_mode 标签（hybrid/dense_only）、rrf_score、reranker_score、检索耗时指标
- **FR-UI-005**: 提供搜索配置面板，包含 Collection 选择（按逻辑知识库聚合展示，每个选项显示知识库名称、文档数量、总向量数量，而非展示单个文档级别的索引记录）、TopK 设置、相似度阈值。检索模式由系统自动决定：默认使用混合检索，稀疏向量不可用时自动降级为纯稠密检索（降级原因包括：Collection 无稀疏字段、BM25 统计数据缺失、稀疏向量生成失败等）。用户无需手动选择检索模式，配置面板以只读状态文本提示当前实际检索模式（如「当前：混合检索」或「当前：纯稠密检索」）。注意：RRF 融合参数 k 不在前端暴露，仅后端可配置 [Updated: 2026-02-26]
- **FR-UI-006**: 混合检索模式下额外显示 Reranker 参数配置（top_n 候选集大小、top_k 最大返回数）
- **FR-UI-007**: 提供搜索历史侧边栏，显示最近的搜索记录（最多50条）
- **FR-UI-008**: 搜索过程中显示加载状态，搜索完成后显示结果数量和耗时
- **FR-UI-009**: 界面样式与现有模块（文档处理、向量化、向量索引）保持一致，使用 TDesign Vue Next 组件库

#### 核心搜索功能

- **FR-001**: 系统必须支持接收自然语言查询文本，调用 Embedding 服务转换为稠密查询向量
- **FR-002**: 系统必须调用向量索引服务执行相似度检索（Milvus），返回 TopK 最相关结果
- **FR-003**: 系统必须支持配置返回结果数量（TopK），范围1-100，默认值10
- **FR-004**: 系统必须支持配置相似度阈值，范围0-1，默认值0.5
- **FR-005**: 系统必须展示当前 Collection 使用的相似度计算方法（余弦相似度/欧氏距离/点积），该值在 Collection 创建时确定，运行时不可切换，仅作为只读信息在 CollectionInfo 中返回
- **FR-006**: 系统必须支持选择单个或多个目标 Milvus Collection 进行搜索
- **FR-007**: 搜索结果必须包含：文档片段ID、文本内容、相似度分数、来源文档信息、元数据

#### 混合检索与精排

- **FR-HYB-001**: 系统必须支持混合检索模式，同时使用稠密向量（FLOAT_VECTOR）和稀疏向量（SPARSE_FLOAT_VECTOR）进行双路召回
- **FR-HYB-002**: 查询时系统必须通过 BM25SparseService.encode_query() 自动为查询文本生成稀疏查询向量（jieba 分词 + 已持久化的 BM25 统计数据）。BM25 统计数据按 Collection/Index 粒度独立管理，采用懒加载策略：首次查询时从磁盘加载并缓存到内存，后续查询直接使用缓存
- **FR-HYB-003**: 系统必须使用 Milvus 原生 RRFRanker（Reciprocal Rank Fusion，默认 k=60）对稠密和稀疏两路检索结果进行粗排融合。RRF k 参数仅在后端配置文件中可调整（默认 k=60，业内标准值），前端不暴露此参数
- **FR-HYB-004**: 系统必须通过远程 Reranker API（OpenAI-compatible `/rerank` 端点）对 RRFRanker 融合后的候选集（Top-N）进行精排重排序，输出最终 Top-K 结果。使用 qwen3-reranker-4b 模型，通过配置项 `RERANKER_MODEL` 选择 [Updated: 2026-02-27]
- **FR-HYB-005**: 精排阶段的候选集大小（N）应可配置，默认为 20，配置范围 N ∈ [10, 100]。多 Collection 联合搜索时各 Collection 统一使用相同的 N 值
- **FR-HYB-006**: 当稀疏向量为空或不可用时，系统必须自动降级到纯稠密向量检索模式（跳过 RRF 融合），直接将稠密检索 Top-N 结果送入 Reranker 精排，确保检索服务不中断
- **FR-HYB-007**: 当 Reranker 服务不可用时，系统必须跳过精排步骤，直接返回 RRF 粗排结果（或纯稠密检索结果），并在响应中标注 reranker_available=false
- **FR-HYB-008**: 系统必须提供 Reranker 健康检查接口（GET /reranker/health）
- **FR-HYB-009**: Reranker 精排时，系统必须支持为查询文本添加 Task Instruction 前缀，格式为 `Instruct: {task_description}\nQuery: {actual_query}`。通过 `RERANKER_TASK_INSTRUCTION` 配置项设置（默认针对产品功能文档检索场景的英文 instruction），设为空字符串则不添加前缀。参考 Qwen3-Reranker 官方 HuggingFace Model Card [Added: 2026-03-04]
- **FR-HYB-010**: Reranker API 调用时，`top_n` 参数设为候选集全量大小（而非 top_k），返回所有候选的分数，供三层防御体系在完整分数分布上做出正确决策。最终的 top_k 截取由外层在防御过滤后统一执行 [Added: 2026-03-04]
- **FR-HYB-011**: 传给 Reranker 的候选文本必须添加文档来源前缀，格式为 `[文档: {doc_name}]\n{原始文本}`，帮助 Reranker 理解文档来源上下文以提升排序准确性 [Added: 2026-03-04]

#### 查询增强（Query Enhancement）[Added: 2026-03-04]

- **FR-QE-001**: 系统必须支持查询增强功能（Query Enhancement），通过一次 LLM 调用同时完成查询改写（Query Rewrite）和多查询生成（Multi-query）。查询改写补全用户问题的上下文使语义更清晰；多查询对复杂问题生成 2-3 个变体查询覆盖不同表述。参考 LangChain MultiQueryRetriever、LlamaIndex QueryTransformEngine、Cohere search_queries_only 设计
- **FR-QE-002**: 查询增强通过 `QUERY_ENHANCEMENT_ENABLED` 全局开关控制（默认开启），使用 `QUERY_ENHANCEMENT_MODEL`（默认 qwen3.5-35b-a3b）进行 LLM 推理。相关配置项包括 `QUERY_ENHANCEMENT_TEMPERATURE`（默认 0.3）、`QUERY_ENHANCEMENT_MAX_TOKENS`（默认 512）、`QUERY_ENHANCEMENT_TIMEOUT`（默认 30s）
- **FR-QE-003**: 当查询增强判定问题为复杂查询（is_complex=true）时，系统使用多查询策略：对改写后的查询和所有变体查询分别执行向量检索，合并去重后统一送入 Reranker 精排
- **FR-QE-004**: 当 LLM 调用失败时，查询增强必须降级为使用原始查询文本，不影响后续检索流程

#### 候选集噪声控制（三层防御体系）[Added: 2026-03-04]

- **FR-DEF-001**: 系统必须实现三层防御体系对检索候选集进行噪声控制，提升最终结果的精确率和多样性
- **FR-DEF-002**: **第 1 层 — 每文档候选配额控制**（Reranker 前）：通过 `MAX_CHUNKS_PER_DOC`（默认 10）限制每个文档（index）最多贡献的候选数量，防止单文档的大量低质 chunk 垄断候选集。参考 Cohere max_chunks_per_doc 设计
- **FR-DEF-003**: **第 1.5 层 — 近重复内容去重**（Reranker 前）：基于 N-gram Jaccard 相似度自动检测并去除跨文档间内容高度相似的 chunk（如导航栏、页脚、免责声明等共用组件）。通过 `NEAR_DUPLICATE_THRESHOLD`（默认 0.5）控制去重严格度，仅对跨文档 chunk 生效（cross_doc_only=True）。参考 Cohere Rerank 去重建议、Google 网页去重 SimHash、LangChain EnsembleRetriever unique_union
- **FR-DEF-004**: **第 2 层 — Reranker 动态阈值过滤**（Reranker 后）：使用静态阈值 `RERANKER_SCORE_THRESHOLD`（默认 0.4）和动态阈值（Top1 分数 × `RERANKER_DYNAMIC_THRESHOLD_RATIO` 默认 0.6，上限 `RERANKER_DYNAMIC_THRESHOLD_MAX` 默认 0.5）过滤低质结果，保底至少保留 `RERANKER_MIN_RESULTS`（默认 2）条结果。参考 Dify/Cohere 阈值过滤、Google Vertex AI Search 动态阈值、Pinecone 最佳实践
- **FR-DEF-005**: **第 3 层 — 文档来源多样性控制**（Reranker 后）：通过 `MAX_RESULTS_PER_DOC`（默认 2）限制每个文档在最终结果中最多占几条，促进结果来源多样性。设为 0 表示不限制

#### 多 Collection 联合搜索

- **FR-MULTI-001**: 系统必须支持跨多个 Milvus Collection 的联合搜索（最多 max_collections=5 个），并行在各 Collection 中执行检索。各 Collection 统一使用相同的 Top-N 候选集大小（默认 N=20），Reranker 输入上限为 max_collections × N（默认 5×20=100 条）
- **FR-MULTI-002**: 多 Collection 联合搜索时，各 Collection 各自完成检索和 RRF 粗排后，系统必须将所有 Collection 的粗排候选集合并，统一送入一次 Reranker 精排，用 reranker_score 做全局排序返回最终 Top-K 结果。当 Reranker 不可用时，降级为按 rrf_score 全局排序
- **FR-MULTI-003**: 联合搜索结果必须标注每条结果的来源 Collection 名称

#### 结果处理

- **FR-008**: 系统必须对搜索结果按 reranker_score（优先）或 rrf_score（Reranker 不可用时）或相似度分数（纯稠密模式）降序排列
- **FR-009**: [已合并至 FR-MULTI-002] ~~多 Collection 搜索排序规则见 FR-MULTI-002~~
- **FR-010**: 系统必须支持结果分页，每页默认10条，支持自定义每页数量
- **FR-011**: 系统必须对返回的文本内容进行摘要处理，默认最多显示200字符

#### 历史记录

- **FR-012**: 系统必须自动记录每次搜索的查询文本、时间戳、检索模式（dense/hybrid）、配置参数、结果数量
- **FR-013**: 系统必须支持查看搜索历史列表，按时间倒序排列
- **FR-014**: 系统必须支持点击历史记录快速重新执行搜索
- **FR-015**: 系统必须支持清除全部或单条搜索历史

#### 错误处理

- **FR-016**: 当查询文本为空时，系统必须返回明确的错误提示
- **FR-017**: 当 Embedding 服务调用失败时，系统必须返回友好的错误信息并记录日志
- **FR-018**: 当 Milvus Collection 不可用时，系统必须返回明确的错误状态
- **FR-019**: 搜索请求必须设置超时限制（默认30秒），超时后返回错误提示

### Key Entities

- **SearchQuery（搜索查询）**: 代表一次搜索请求，包含查询文本、目标 Collection 列表、TopK、相似度阈值、检索模式（dense/hybrid）、Reranker 参数（top_n、top_k）等
- **SearchResult（搜索结果）**: 代表单条搜索结果，包含文档片段ID、文本内容、相似度分数、rrf_score（混合检索）、reranker_score（精排后）、来源 Collection、来源文档、search_mode 标签、元数据
- **SearchHistory（搜索历史）**: 代表一条搜索历史记录，包含查询ID、查询文本、检索模式、搜索配置、结果数量、执行时间、创建时间
- **CollectionInfo（Collection 信息）**: 代表一个逻辑知识库（Collection）的聚合信息，包含知识库名称（collection_name）、文档数量（document_count）、总向量数量（vector_count）、向量维度、度量类型、是否含稀疏向量（has_sparse）等。系统按 VectorIndex.collection_name 字段聚合多条索引记录，对外暴露逻辑知识库粒度而非单个文档/索引记录粒度 [Updated: 2026-02-26]
- **SearchConfig（搜索配置）**: 代表搜索的配置参数，包含默认 Collection、默认 TopK、默认阈值、默认检索模式、Reranker 配置
- **QueryResult（查询结果）**: 代表单个查询的向量检索结果项，包含向量ID、相似度分数、元数据

### Non-Functional Considerations

- **性能（纯稠密检索）**: 对于10000条向量的 Milvus 索引，单次纯稠密 TopK 查询响应时间应在100ms以内（P95）
- **性能（混合检索）**: 混合检索 Top-K 查询（含 RRF 粗排 + Reranker 精排）总耗时应在200ms以内（P95）
- **性能（Reranker 精排）**: qwen3-reranker-4b 对 20 条候选集的精排推理耗时应在100ms以内（P95）
- **性能（BM25 查询向量生成）**: BM25 稀疏查询向量生成耗时应在10ms以内（P95）
- **性能（端到端）**: 用户输入查询到看到搜索结果的端到端响应时间在3秒以内（P95），含 Embedding 服务调用
- **可用性（降级）**: 当稀疏向量不可用或 Reranker 服务异常时，系统自动降级到纯稠密检索模式，确保检索服务不中断
- **并发性**: 系统支持至少20个并发搜索请求，总体吞吐量达到10 QPS
- **可观测性**: 完整的查询耗时、检索模式、Reranker 状态等指标追踪

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 用户输入查询到看到搜索结果的端到端响应时间在3秒以内（P95）
- **SC-002**: 纯稠密检索：对于10000条向量，单次 TopK 查询响应时间在100ms以内（P95）
- **SC-003**: 混合检索：Top-K 查询（含 RRF 粗排 + Reranker 精排，候选集 N=20）总耗时在200ms以内（P95）
- **SC-004**: Reranker 精排：qwen3-reranker-4b 对 20 条候选集精排推理耗时在100ms以内（P95）
- **SC-005**: 稀疏向量为空或 Reranker 不可用时，系统自动降级到纯稠密检索，降级响应时间不超过纯稠密检索的110%
- **SC-006**: 系统支持至少20个并发搜索请求，总体吞吐量达到10 QPS
- **SC-007**: 搜索功能可用性达到99.5%，Embedding 服务故障时有明确的降级提示
- **SC-008**: 搜索历史记录准确率100%，每次搜索都被正确记录
- **SC-009**: 多 Collection 联合搜索的结果合并正确率100%，排序基于统一 Reranker 精排的 reranker_score 全局排序
- **SC-010**: 系统在处理无效输入时100%返回明确的错误信息，不发生崩溃

## Assumptions

- 假设向量索引模块（004-vector-index-opt）已完成并可用，提供标准的相似度检索 API 和 Milvus Collection 管理能力
- 假设 Embedding 服务已完成并可用，提供文本到稠密向量的转换 API
- 假设稀疏向量由 BM25 算法在索引构建阶段独立生成并持久化统计数据，查询时通过 BM25SparseService.encode_query() 生成查询稀疏向量。BM25 统计数据按 Collection/Index 粒度独立管理，首次查询时懒加载到内存缓存（非服务启动时预加载），适应大 Collection 和多 Collection 场景的内存管理需求
- 假设 Milvus 运行在独立服务器或 Docker 容器中，通过网络 API 访问
- ~~假设 bge-reranker-v2-m3 通过 FlagEmbedding>=1.2.0 本地加载，用于混合检索的精排重排序~~
- ~~假设 Reranker 精排通过远程 API 服务调用，支持 qwen3-reranker-4b / bge-reranker-v2-m3 / bge-reranker-large 三种模型~~
- 假设 Reranker 精排通过远程 API 服务（OpenAI-compatible `/rerank` 端点）调用，使用 qwen3-reranker-4b 模型。API 地址通过 `RERANKER_API_BASE_URL` 配置 [Updated: 2026-02-27]
- 假设单次查询文本长度不超过2000字符
- 假设搜索历史存储在本地数据库（SQLite/PostgreSQL），不跨设备同步
- 假设系统默认使用混合检索（hybrid），运行时自动降级：当稀疏向量不可用时（Collection 无稀疏字段、BM25 统计数据缺失、稀疏向量生成失败等任一原因），自动降级为纯稠密检索（dense_only），确保检索服务不中断。用户无需手动选择检索模式。此策略与业内主流系统（Elasticsearch、Weaviate、Pinecone、LlamaIndex）的「乐观尝试 + 自动降级」设计一致
- 假设默认使用余弦相似度（COSINE）作为相似度计算方法
- 假设前端使用与现有模块一致的技术栈（Vue 3 + TDesign Vue Next）
- 假设搜索结果（SearchResult）为实时计算结果，不需要持久化存储；搜索历史（SearchHistory）会持久化以支持重复查询
- 假设采用「逻辑与物理分层」Collection 架构（对外暴露逻辑知识库名，底层按维度拆分为物理 Collection）

## Dependencies

- **向量索引模块（004-vector-index-opt）**: 提供 Milvus Collection 管理、向量相似度检索、混合检索（hybrid_search）能力
- **向量 Embedding 模块（003-vector-embedding）**: 提供查询文本的稠密向量化能力
- **文档处理模块（001-document-processing）**: 提供文档元数据信息
- **文档分块模块（002-doc-chunking）**: 提供文档片段的原始内容
- **核心依赖**: Milvus 向量数据库（2.x 版本）及其 Python SDK（pymilvus）
- **BM25 查询服务**: BM25SparseService（jieba 分词 + 已持久化的统计数据），用于生成稀疏查询向量
- **Reranker 服务**: 远程 Reranker API（OpenAI-compatible `/rerank` 端点），使用 qwen3-reranker-4b 模型，通过 `openai` Python SDK 调用 [Updated: 2026-02-27]

## Out of Scope

- 向量 Embedding 生成（由独立的 Embedding 模块负责）
- 向量索引的创建与管理（由 004-vector-index-opt 模块负责）
- BM25 稀疏向量的索引构建阶段生成（由 004-vector-index-opt 的 BM25SparseService 负责）
- 索引算法推荐引擎（由 004-vector-index-opt 模块负责）
- 分布式向量检索（单机 Milvus 版本优先）
- GPU 加速的向量检索
- 搜索结果的个性化推荐
- 搜索分析和统计报表
- 搜索结果的导出功能
- 多语言查询支持（当前仅支持中文和英文）
- ~~查询改写与意图识别~~ [Moved to In-Scope: 2026-03-04, 见 FR-QE-001~004]
- 细粒度的权限控制和多租户隔离

## Change Log

| 日期 | 类型 | 变更内容 | 影响需求 |
|------|------|----------|----------|
| 2026-02-26 | BEHAVIOR_CHANGE [VIBE] | Collection 选择器从展示文档级别的索引记录（VectorIndex）改为按 collection_name 聚合的逻辑知识库级别。后端 `get_available_collections()` 按 collection_name 聚合，`CollectionInfo` 新增 document_count 字段，id 从索引 ID 改为 collection_name。前端混合检索请求中 collection_ids 参数从索引 ID 改为 collection_name，后端新增 `_resolve_collection_names_to_index_ids()` 做映射转换并向后兼容旧数据。 | FR-UI-005, US4, US6 |
| 2026-02-26 | BEHAVIOR_CHANGE [VIBE] | Reranker 精排从本地 FlagEmbedding 模型推理改为远程 API 调用（OpenAI-compatible `/rerank` 端点）。移除 `FlagEmbedding>=1.2.0` 本地依赖，改用 `openai` SDK 调用远程服务。新增配置项 `RERANKER_API_KEY`、`RERANKER_API_BASE_URL`、`RERANKER_TIMEOUT`，移除 `RERANKER_USE_FP16`、`RERANKER_BATCH_SIZE`。健康检查改为 API 连通性测试。 | FR-HYB-004, FR-HYB-008, US2 |
| 2026-02-27 | BEHAVIOR_CHANGE [VIBE] | Reranker 模型从支持 3 种（qwen3-reranker-4b / bge-reranker-v2-m3 / bge-reranker-large）精简为仅支持 qwen3-reranker-4b。移除 bge-reranker-v2-m3 和 bge-reranker-large 相关配置和代码，默认模型改为 qwen3-reranker-4b。 | FR-HYB-004, US2 |
| 2026-02-27 | BUG_FIX [VIBE] | 统一 Top-K 参数描述：从"最终返回数/最终返回结果数量"修改为"最大返回数/最多返回结果数量"，明确 Top-K 为上限语义（at most K），实际返回数量取决于召回结果。前端 UI 标签、提示文字、后端 Schema description、API 契约、Spec 数据模型同步更新。 | FR-UI-006, FR-003, US4 |
| 2026-02-27 | BEHAVIOR_CHANGE [VIBE] | **一个知识库对应一种 Embedding 模型**：重构 Collection 命名策略，不同嵌入模型自动对应不同逻辑 Collection。1）`vector_config.py` 新增 `get_default_collection_name_for_model()` 函数，按 `default_kb_{model_name}` 格式生成逻辑 Collection 名。2）`create_index_from_embedding()` 当 collection_name 为空时根据嵌入模型自动路由到对应知识库。3）`SearchService` 新增 `_get_embedding_service_for_model()` 和 `_resolve_embedding_model_for_collections()` 方法，搜索时自动使用知识库绑定的模型嵌入查询文本。4）`get_available_collections()` 返回新增 `embedding_model` 字段。5）前端 Collection 选择器展示绑定的嵌入模型信息。 | FR-UI-005, US6 |
| 2026-02-27 | BEHAVIOR_CHANGE [VIBE] | **跨模型联合搜索**：多 Collection 联合搜索现在支持跨不同 Embedding 模型的 Collection。1）新增 `_group_collections_by_embedding_model()` 方法，按 Embedding 模型对 Collection 进行分组。2）新增 `_embed_query_per_model_group()` 方法，使用 `asyncio.gather()` 并行为每种模型嵌入查询文本。3）`_multi_collection_search()` 从接收单一 `query_vector` 改为接收 `collection_vectors: Dict[str, np.ndarray]`（collection_id → query_vector 映射），每个 Collection 使用各自绑定模型生成的查询向量进行检索。4）合并候选集后统一 Reranker 精排（Reranker 基于文本，天然支持跨模型）。5）`_resolve_embedding_model_for_collections()` 保持向后兼容，单 Collection 场景不受影响。参考业界实践：LlamaIndex MultiIndex 各 Index 独立 embed + 检索，LangChain EnsembleRetriever 各 retriever 独立运行后 RRF/Reranker 融合。 | US6, FR-HYB-004 |
| 2026-03-04 | BEHAVIOR_CHANGE [VIBE] | **查询增强（Query Enhancement）**：新增 `QueryEnhancementService`，通过一次 LLM 调用（qwen3.5-35b-a3b）同时完成查询改写（Query Rewrite）和多查询生成（Multi-query）。1）查询改写补全用户问题上下文，使语义更清晰。2）多查询对复杂问题生成 2-3 个变体查询，覆盖不同表述。3）SearchService 集成查询增强流程：增强后的改写查询和变体查询分别执行向量检索，合并去重后统一 Reranker 精排。4）降级策略：LLM 失败时使用原始查询。5）新增配置项 `QUERY_ENHANCEMENT_ENABLED`、`QUERY_ENHANCEMENT_MODEL`、`QUERY_ENHANCEMENT_TEMPERATURE`、`QUERY_ENHANCEMENT_MAX_TOKENS`、`QUERY_ENHANCEMENT_TIMEOUT`。6）SearchTiming 新增 `query_enhancement_ms` 字段。此功能从 Out of Scope 移入。参考 LangChain MultiQueryRetriever、LlamaIndex QueryTransformEngine、Cohere search_queries_only。 | FR-QE-001~004, US2 |
| 2026-03-04 | BEHAVIOR_CHANGE [VIBE] | **三层防御体系（候选集噪声控制）**：新增完整的候选集噪声控制机制，提升检索精确率和结果多样性。1）第 1 层：每文档候选配额控制（`MAX_CHUNKS_PER_DOC=10`，Reranker 前），参考 Cohere max_chunks_per_doc。2）第 1.5 层：近重复内容去重（`NEAR_DUPLICATE_THRESHOLD=0.5`，N-gram Jaccard 跨文档去重），参考 Google 网页去重 SimHash。3）第 2 层：Reranker 动态阈值过滤（静态阈值 0.4 + 动态阈值 Top1×0.6，保底 2 条），参考 Dify/Cohere/Google Vertex AI Search。4）第 3 层：文档来源多样性控制（`MAX_RESULTS_PER_DOC=2`，Reranker 后）。 | FR-DEF-001~005, US2 |
| 2026-03-04 | BEHAVIOR_CHANGE [VIBE] | **Reranker Task Instruction**：为 qwen3-reranker-4b 添加 Task Instruction 前缀（`Instruct: {task}\nQuery: {query}` 格式），新增配置项 `RERANKER_TASK_INSTRUCTION`。Reranker API 调用 `top_n` 改为返回全量候选分数（供三层防御体系使用），最终截取由外层统一执行。参考 Qwen3-Reranker 官方 Model Card。 | FR-HYB-009~010, US2 |
| 2026-03-04 | BEHAVIOR_CHANGE [VIBE] | **Reranker 候选文本上下文前缀**：传给 Reranker 的候选文本添加 `[文档: {doc_name}]` 前缀，帮助 Reranker 理解文档来源上下文。 | FR-HYB-011, US2 |
| 2026-03-04 | BUG_FIX [VIBE] | **修复 embedding_storage chunk_metadata 遗漏**：`save_batch_result()` 序列化 vectors 到 JSON 文件时遗漏了 `chunk_metadata` 字段，导致 heading_path 等元数据在 chunker → embedding JSON → Milvus 的数据链路中断裂。新增 `"chunk_metadata": getattr(v, 'chunk_metadata', None)` 字段。 | FR-HYB-011, US2 |
| 2026-03-04 | DATA_STRUCTURE [VIBE] | **Spec 数据模型与 API 契约同步**：将代码中已实现的数据结构变更同步到 spec 文件。1）`HybridSearchRequest` 新增 `enable_query_enhancement`(bool, 默认 true)、`page`(int, 默认 1)、`page_size`(int, 默认 10) 字段。2）`HybridSearchResponseData` 新增 `query_enhancement`(QueryEnhancementInfo) 字段，返回查询增强的改写查询、变体查询、耗时等信息。3）`SearchTiming` 新增 `query_enhancement_ms` 字段。4）`CollectionInfo` 新增 `document_count`(int) 和 `embedding_model`(string) 字段。5）新增 `QueryEnhancementInfo` 实体定义（enabled、original_query、rewritten_query、is_complex、sub_queries、all_queries、enhancement_time_ms、error）。6）`RerankerHealthResponse.data` schema 从旧的本地模型字段（use_fp16、flag_embedding_installed、model_loaded）更新为远程 API 字段（api_base_url、api_connected、supported_models）。同步更新 data-model.md 和 contracts/search-api.yaml。 | FR-QE-001~004, FR-UI-005, US2, US4 |
