# Feature Specification: 文本生成功能

**Feature Branch**: `006-text-generation`  
**Created**: 2025-12-26  
**Status**: Draft  
**Input**: 用户描述: "实现文本生成功能，基于RAG检索结果和用户输入，使用deepseek-v3、deepseek-r1、kimi-k2-instruct模型生成回答"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - RAG问答生成 (Priority: P1)

用户在搜索查询模块完成向量检索后，希望基于检索到的相关文档片段和自己的问题，让大模型生成一个综合性的回答。用户可以选择不同的生成模型（deepseek-v3、deepseek-r1、kimi-k2-instruct），系统将检索结果作为上下文，结合用户问题生成高质量的回答。

**Why this priority**: 这是RAG系统的核心价值所在，将检索与生成结合，提供智能问答能力。

**Independent Test**: 用户在搜索页面输入问题，选择模型，点击生成按钮，即可获得基于检索结果的回答。

**Acceptance Scenarios**:

1. **Given** 用户已完成向量检索并获得相关文档片段, **When** 用户选择生成模型并点击"生成回答"按钮, **Then** 系统基于检索结果和用户问题生成回答并展示
2. **Given** 用户正在等待生成结果, **When** 生成过程进行中, **Then** 系统显示流式输出，逐字展示生成内容
3. **Given** 生成完成, **When** 用户查看结果, **Then** 回答内容清晰展示，并标注使用的模型和引用的文档来源

---

### User Story 2 - 模型选择与配置 (Priority: P2)

用户希望能够根据需求选择不同的生成模型，了解各模型的特点，并能配置生成参数（如温度、最大输出长度等）。

**Why this priority**: 不同模型有不同特点，用户需要根据场景选择最合适的模型。

**Independent Test**: 用户在生成配置面板中选择模型、调整参数，系统保存配置并在生成时使用。

**Acceptance Scenarios**:

1. **Given** 用户进入文本生成配置, **When** 查看模型列表, **Then** 显示三个可用模型（deepseek-v3、deepseek-r1、kimi-k2-instruct）及其描述
2. **Given** 用户选择某个模型, **When** 调整生成参数（温度、最大长度）, **Then** 参数设置被保存并应用于后续生成
3. **Given** 用户未选择模型, **When** 点击生成, **Then** 系统使用默认模型（deepseek-v3）进行生成

---

### User Story 3 - 生成历史管理 (Priority: P3)

用户希望能够查看历史生成记录，包括问题、使用的检索结果、选择的模型和生成的回答，方便回顾和对比。

**Why this priority**: 历史记录帮助用户追踪和对比不同模型的生成效果。

**Independent Test**: 用户在历史记录页面查看过往的生成记录，可以重新查看详情。

**Acceptance Scenarios**:

1. **Given** 用户完成一次文本生成, **When** 生成成功, **Then** 系统自动保存生成记录（问题、模型、回答、时间）
2. **Given** 用户查看生成历史, **When** 点击某条记录, **Then** 展示完整的问题、检索上下文、模型配置和生成回答
3. **Given** 用户管理历史记录, **When** 删除某条记录, **Then** 记录被移除且不可恢复

---

### Edge Cases

- 检索结果为空时，系统应提示用户先进行有效检索，或允许用户直接提问（无上下文模式）
- 生成过程中网络中断，系统应保存已生成的部分内容并提示用户
- 用户输入的问题过长超过模型上下文限制，系统应提示并建议缩短问题
- API调用失败（认证错误、限流等），系统应显示友好错误信息并支持重试

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: 系统必须支持三种生成模型：deepseek-v3、deepseek-r1、kimi-k2-instruct
- **FR-002**: 系统必须能够将RAG检索结果作为上下文传递给生成模型
- **FR-003**: 系统必须支持流式输出（Streaming），实时展示生成内容
- **FR-004**: 系统必须允许用户配置生成参数：温度(temperature)、最大输出长度(max_tokens)
- **FR-005**: 系统必须保存生成历史记录，包括问题、模型、参数、回答、时间戳
- **FR-006**: 系统必须在生成回答中标注引用的文档来源
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
- **SC-002**: 系统支持128K上下文长度的检索结果输入
- **SC-003**: 流式输出时，首 token 响应后，后续 token 平均间隔不超过 200ms（受模型服务影响）
- **SC-004**: 生成历史记录支持存储至少100条记录，超出时自动清理最旧记录
- **SC-005**: 95%的生成请求能够成功完成（排除网络问题）
- **SC-006**: 用户能够在5秒内完成模型选择和参数配置

## Assumptions

- API服务（base_url）与现有embedding模型相同，已配置且可用
- 三个模型（deepseek-v3、deepseek-r1、kimi-k2-instruct）均支持OpenAI兼容的API格式
- 用户已完成向量检索，有可用的检索结果作为上下文
- 系统运行环境具备稳定的网络连接
- 默认温度参数为0.7，默认最大输出长度为4096 tokens
