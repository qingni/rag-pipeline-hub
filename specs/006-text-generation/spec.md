# Feature Specification: 文本生成功能

**Feature Branch**: `006-text-generation-opt`  
**Created**: 2025-12-26  
**Status**: Draft  
**Input**: 用户描述: "实现文本生成功能，基于RAG检索结果和用户输入，使用deepseek-v3.2、deepseek-v3.1模型生成回答"

## 版本变更说明

本版本基于 `006-text-generation` **现有实现**进行优化。现有实现已包含：
- 后端：`backend/src/services/generation_service.py`（LLM 调用、流式输出、历史记录）
- 后端：`backend/src/api/generation.py`（API 路由）
- 前端：`frontend/src/views/Generation.vue`（独立页面、配置面板、结果展示）
- 前端：`frontend/src/stores/generationStore.js`（状态管理、检索集成）

**本次优化变更**：

- **修复知识库索引选择器 [BUG]**：知识库索引下拉框当前展示文档级索引（VectorIndex，如 `idx_股票_APP_...`），应改为展示 Collection（逻辑知识库），复用搜索查询模块的 `get_available_collections()` 接口
- **优化上下文组装策略**：当前实现直接使用检索结果，需增加 Token 截断策略以防止超出模型上下文限制
- **标准化引用格式**：确保生成回答采用内联编号引用 + 末尾参考列表格式
- **增强结果渲染体验**：生成结果支持 Markdown 富文本展示，并在前端进行安全清洗后渲染
- **补齐交互闭环**：失败状态支持一键重试，历史记录支持单条删除与全部清空

## Clarifications

### Session 2026-03-05

- Q: 知识库索引下拉框应该展示的选项单位是什么？ → A: 以 Collection（逻辑知识库）为单位显示，复用搜索查询模块的 CollectionInfo 数据结构和 get_available_collections() 接口。每个选项显示知识库名称、文档数量、向量数量，而非展示单个文档级别的索引记录（如 idx_股票_APP_股票详情页功能介绍_md_...）。参考 005-search-query-opt 的 FR-UI-005 和 Change Log 2026-02-26
- Q: 文本生成功能与搜索查询模块如何集成？ → A: 独立页面模式。文本生成是独立页面，用户在该页面选择 Collection、输入问题，系统自动执行搜索获取上下文后生成回答。理由：①搜索查询模块聚焦召回率优化，文本生成模块聚焦 LLM 生成质量，职责分离；②符合 RAG 项目分模块实现的架构原则；③各模块可独立开发、测试和迭代
- Q: 文本生成功能是否需要支持多轮对话？ → A: 首版仅支持单轮问答，每次生成独立，不保留对话历史。理由：①降低首版开发复杂度；②先验证 RAG 生成质量；③多轮对话可作为后续迭代功能
- Q: 检索上下文的组装策略是什么？ → A: 相似度过滤 + Token 截断策略。复用搜索模块已有的 Reranker 精排 + 三层防御体系（去重、阈值过滤、多样性控制），生成模块按 reranker_score 排序，从高到低累加 chunk 直到接近 token 预算上限（模型最大上下文 - 系统 prompt - 用户问题 - 回答预留空间）。首版不引入额外 LLM 压缩调用，后续可迭代升级到 LangChain LLMChainExtractor 方案。参考 LangChain EmbeddingsFilter
- Q: 生成回答中的引用标注格式是什么？ → A: 内联编号引用 + 末尾参考列表。正文中使用 [1][2] 等编号标注引用来源，回答末尾附上参考来源列表（[1] 文档名.md, [2] 文档名.md）。这是学术/专业文档的标准格式，便于用户追溯来源

### Session 2026-03-06

- Q: 流式生成在前端如何接入？ → A: 后端仍使用 SSE 格式返回数据，但前端通过 `fetch + ReadableStream` 解析 `/api/v1/generation/stream` 的 POST 响应，而不是使用原生 EventSource（因为生成请求需要 POST body）
- Q: 生成结果的展示格式是什么？ → A: 支持 Markdown 富文本展示（标题、列表、表格、代码块、引用等），前端在渲染前做安全清洗，防止不可信 HTML 注入
- Q: 生成历史支持哪些管理操作？ → A: 支持分页查看、查看详情、单条删除以及“清空全部历史记录”软删除

## User Scenarios & Testing *(mandatory)*

### User Story 1 - RAG问答生成 (Priority: P1)

用户在文本生成页面选择目标知识库（Collection），输入问题，系统自动调用搜索查询模块执行向量检索获取相关文档片段，然后将检索结果作为上下文传递给 LLM 生成综合性回答。用户可以选择不同的生成模型（deepseek-v3.2、deepseek-v3.1）。[Updated: 2026-03-05]

**Why this priority**: 这是RAG系统的核心价值所在，将检索与生成结合，提供智能问答能力。

**Independent Test**: 用户在文本生成页面选择 Collection、输入问题、选择模型，点击生成按钮，即可获得基于检索结果的回答。[Updated: 2026-03-05]

**Acceptance Scenarios**:

1. **Given** 用户在文本生成页面选择了目标 Collection 并输入问题, **When** 用户选择生成模型并点击"生成回答"按钮, **Then** 系统自动执行搜索、获取上下文、生成回答并展示 [Updated: 2026-03-05]
2. **Given** 用户正在等待生成结果, **When** 生成过程进行中, **Then** 系统显示流式输出，逐字展示生成内容
3. **Given** 生成完成, **When** 用户查看结果, **Then** 回答内容清晰展示，并标注使用的模型和引用的文档来源
4. **Given** 生成结果包含 Markdown 结构（如标题、列表、代码块、表格）, **When** 前端展示回答, **Then** 系统以安全清洗后的富文本形式渲染，而不是纯文本直出

---

### User Story 2 - 模型选择与配置 (Priority: P2)

用户希望能够根据需求选择不同的生成模型，了解各模型的特点，并能配置生成参数（如温度、最大输出长度等）。

**Why this priority**: 不同模型有不同特点，用户需要根据场景选择最合适的模型。

**Independent Test**: 用户在生成配置面板中选择模型、调整参数，系统保存配置并在生成时使用。

**Acceptance Scenarios**:

1. **Given** 用户进入文本生成配置, **When** 查看模型列表, **Then** 显示两个可用模型（deepseek-v3.2、deepseek-v3.1）及其描述
2. **Given** 用户选择某个模型, **When** 调整生成参数（温度、最大长度）, **Then** 参数设置被保存并应用于后续生成
3. **Given** 用户未选择模型, **When** 点击生成, **Then** 系统使用默认模型（deepseek-v3.2）进行生成

---

### User Story 3 - 生成历史管理 (Priority: P3)

用户希望能够查看历史生成记录，包括问题、使用的检索结果、选择的模型和生成的回答，方便回顾和对比。

**Why this priority**: 历史记录帮助用户追踪和对比不同模型的生成效果。

**Independent Test**: 用户在历史记录页面查看过往的生成记录，可以重新查看详情。

**Acceptance Scenarios**:

1. **Given** 用户完成一次文本生成, **When** 生成成功, **Then** 系统自动保存生成记录（问题、模型、回答、时间）
2. **Given** 用户查看生成历史, **When** 点击某条记录, **Then** 展示完整的问题、检索上下文、模型配置和生成回答
3. **Given** 用户管理历史记录, **When** 删除某条记录, **Then** 记录被移除且不可恢复
4. **Given** 用户需要批量清理历史记录, **When** 点击“清空”并确认, **Then** 系统软删除全部历史记录并刷新列表

---

### Edge Cases

- 检索结果为空时，系统应提示用户先进行有效检索，或允许用户直接提问（无上下文模式）
- 生成过程中网络中断，系统应保存已生成的部分内容并提示用户
- 用户输入的问题过长超过模型上下文限制，系统应提示并建议缩短问题
- API调用失败（认证错误、限流等），系统应显示友好错误信息并支持重试
- 生成结果包含 Markdown/链接/表格等富文本结构时，前端应正确渲染并防止不可信 HTML 注入

## Requirements *(mandatory)*

### Functional Requirements

#### 前端界面需求

- **FR-UI-001**: 知识库索引选择器必须以 Collection（逻辑知识库）为单位展示，每个选项显示知识库名称、文档数量、向量数量，复用搜索查询模块的 `CollectionInfo` 数据结构和 `get_available_collections()` 接口 [Added: 2026-03-05]
- **FR-UI-002**: 知识库索引选择器支持多选（可选择多个 Collection 作为检索范围）
- **FR-UI-003**: 生成结果区域必须支持 Markdown 富文本渲染（标题、列表、引用、代码块、表格、链接等）
- **FR-UI-004**: 前端在渲染生成结果前必须进行安全清洗，防止不可信 HTML 注入
- **FR-UI-005**: 当生成失败时，前端必须提供重试入口，允许用户使用当前问题和配置重新发起生成

#### 核心生成功能

- **FR-001**: 系统必须支持两种生成模型：deepseek-v3.2、deepseek-v3.1
- **FR-002**: 系统必须能够将RAG检索结果作为上下文传递给生成模型
- **FR-002a**: 上下文组装采用 Token 截断策略：按 reranker_score 从高到低累加 chunk，直到接近 token 预算上限（模型最大上下文 - 系统 prompt - 用户问题 - 回答预留空间，默认预留 4096 tokens 给回答）[Added: 2026-03-05]
- **FR-003**: 系统必须支持流式输出（Streaming），实时展示生成内容
- **FR-004**: 系统必须允许用户配置生成参数：温度(temperature)、最大输出长度(max_tokens)
- **FR-005**: 系统必须保存生成历史记录，包括问题、模型、参数、回答、时间戳
- **FR-005a**: 系统必须支持清空全部生成历史记录，采用软删除方式处理
- **FR-006**: 系统必须在生成回答中标注引用的文档来源，采用内联编号引用 + 末尾参考列表格式（如：正文内容[1]...[2]，末尾附 [1] 文档名, [2] 文档名）[Updated: 2026-03-05]
- **FR-007**: 系统必须处理API调用错误并提供友好的错误提示
- **FR-008**: 系统必须支持重试机制，当API调用失败时允许用户重试
- **FR-009**: 系统必须在无检索结果时提供无上下文生成模式
- **FR-010**: 系统必须支持取消正在进行的生成请求

### Key Entities

- **GenerationModel**: 生成模型配置，包含模型名称、描述、上下文长度限制、默认参数
- **GenerationRequest**: 生成请求，包含用户问题、检索上下文、模型选择、参数配置
- **GenerationResult**: 生成结果，包含生成的回答、使用的token数、耗时、引用来源
- **GenerationHistory**: 生成历史记录，关联用户、问题、模型、结果、时间戳

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 用户从发起生成请求到看到第一个字符输出的时间不超过3秒
- **SC-002**: 系统支持128K上下文长度的检索结果输入（模型能力上限，实际通过 FR-002a Token 截断策略确保不超限）[Updated: 2026-03-05]
- **SC-003**: 流式输出时，首 token 响应后，后续 token 平均间隔不超过 200ms（受模型服务影响）
- **SC-004**: 生成历史记录支持存储至少100条记录，超出时自动清理最旧记录
- **SC-005**: 95%的生成请求能够成功完成（排除网络问题）
- **SC-006**: 用户能够在5秒内完成模型选择和参数配置
- **SC-007**: Markdown 富文本回答在前端渲染后应保持结构完整且无脚本执行风险

## Assumptions

- API服务（base_url）与现有embedding模型相同，已配置且可用
- 两个模型（deepseek-v3.2、deepseek-v3.1）均支持OpenAI兼容的API格式
- 文本生成模块作为独立页面，内部调用搜索查询模块执行检索 [Updated: 2026-03-05]
- 系统运行环境具备稳定的网络连接
- 默认温度参数为0.7，默认最大输出长度为4096 tokens
- 首版仅支持单轮问答，不保留对话历史 [Added: 2026-03-05]

## Dependencies

- **搜索查询模块（005-search-query-opt）**: 提供 Collection 列表查询（get_available_collections）、混合检索（hybrid_search）、Reranker 精排能力
- **向量索引模块（004-vector-index-opt）**: 提供 Milvus Collection 管理
- **向量 Embedding 模块（003-vector-embedding）**: 提供查询文本向量化能力（由搜索模块内部调用）
- **LLM API 服务**: 提供 deepseek-v3.2、deepseek-v3.1 模型的 OpenAI 兼容 API

## Out of Scope

- 多轮对话（带上下文记忆的连续问答）— 后续迭代
- LLM 上下文压缩（LangChain LLMChainExtractor 方案）— 后续迭代
- 个性化推荐和用户画像
- 多语言翻译输出
- 语音输入/输出
- 导出功能（PDF、Word 等）
