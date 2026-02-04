# Feature Specification: 文档分块功能优化

**Feature Branch**: `002-doc-chunking-opt`  
**Created**: 2026-01-20  
**Status**: Draft  
**Input**: User description: "参考001-document-processing-opt分支，新建doc-chunking-opt优化分支。需求：1）分析现有的分块功能，结合分块相关的优化技巧，出于提升RAG效果的目的，优化分块功能 2）在向量嵌入的模型中支持qwen3-embedding-8b多模态模型，分块时也需要考虑多模态 3）前端的分块功能同步需要变更下，更方便用户选择合适的方式进行分块"

## Clarifications

### Session 2026-01-20

- Q: 父子分块检索返回策略？ → A: 返回命中子块对应的父块内容
- Q: 图片分块的向量化方式？ → A: 优先使用图片 base64 直接向量化，失败时降级为文本描述
- Q: 语义分块的相似度算法？ → A: 升级为 Embedding 相似度，TF-IDF 作为 fallback
- Q: 大文档分块的性能策略？ → A: 流式分块处理，分段加载并渐进式输出结果
- Q: 分块结果的版本管理？ → A: 保留历史版本，支持版本对比和回滚

## Background

本优化基于现有 `002-doc-chunking` 分支的分块功能，结合 `001-document-processing-opt` 的文档处理优化成果，旨在通过引入高级分块技巧和多模态支持来提升 RAG 系统的检索效果。

### 现有分块功能分析

当前系统支持四种分块策略：
- **CHARACTER（按字数）**：固定字符数切分，支持重叠
- **PARAGRAPH（按段落）**：以自然段落为单位
- **HEADING（按标题）**：按 H1/H2/H3 层级切分
- **SEMANTIC（按语义）**：基于统一 EmbeddingService 的语义相似度算法识别语义边界，支持 bge-m3、qwen3-embedding-8b、hunyuan-embedding 模型，TF-IDF 作为 fallback 机制

### 优化方向

1. **分块策略增强**：引入父子文档分块、滑动窗口优化、混合分块策略
2. **多模态支持**：针对表格、图片等嵌入对象的独立分块处理
3. **向量模型扩展**：支持统一 EmbeddingService（bge-m3、qwen3-embedding-8b、hunyuan-embedding）用于语义分块，qwen3-vl-embedding-8b 用于多模态分块（未来扩展）
4. **前端体验优化**：智能策略推荐、分块预览增强、效果对比功能

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 智能分块策略推荐与选择 (Priority: P1)

用户希望根据文档类型和内容特征，获得系统推荐的最佳分块策略，并能够快速选择合适的分块方式，以提升后续检索效果。

**Why this priority**: 选择正确的分块策略是提升 RAG 效果的关键第一步。智能推荐可以帮助用户（尤其是新手）避免因策略选择不当导致的检索效果下降。

**Independent Test**: 可以通过上传不同类型的文档（技术文档、小说、研究论文、表格数据），验证系统推荐的策略是否合理，并对比推荐策略与其他策略的分块效果。

**Acceptance Scenarios**:

1. **Given** 用户上传了一份包含多级标题的技术文档，**When** 系统分析文档结构后，**Then** 系统推荐"按标题分块"策略，并显示推荐理由："检测到清晰的标题层级结构（H1: 3个, H2: 12个, H3: 25个）"
2. **Given** 用户上传了一份连续叙事的小说文档，**When** 系统分析文档内容后，**Then** 系统推荐"语义分块"策略，并显示推荐理由："检测到连续叙事文本，无明显标题结构"
3. **Given** 用户上传了包含大量表格的文档，**When** 系统检测到表格内容后，**Then** 系统推荐"多模态分块"策略，并提示"文档包含 15 个表格，建议启用表格独立分块"
4. **Given** 系统已给出策略推荐，**When** 用户点击"查看所有策略对比"，**Then** 系统展示所有可用策略的特点、适用场景、预估块数量的对比表格

---

### User Story 2 - 父子文档分块处理 (Priority: P1)

用户需要使用父子文档分块策略，将文档切分为小块用于精确检索，同时保留大块用于上下文获取，以提升检索的精确度和上下文完整性。

**Why this priority**: 父子文档分块是提升 RAG 效果的核心技术之一，可以同时满足精确检索（小块）和上下文完整性（大块）的需求，显著提升生成质量。

**Independent Test**: 可以通过对同一文档分别使用普通分块和父子分块，对比检索结果的精确度和上下文完整性，验证父子分块的效果提升。

**Acceptance Scenarios**:

1. **Given** 用户选择"父子文档分块"策略，**When** 用户配置父块大小为 2000 字符、子块大小为 400 字符、子块重叠度为 50 字符，**Then** 系统显示预计生成的父块数量和子块数量
2. **Given** 分块参数已配置，**When** 用户执行分块操作，**Then** 系统生成两层结构的分块结果：每个父块包含完整的上下文内容，每个子块包含对应父块的引用 ID
3. **Given** 分块完成，**When** 用户查看分块结果，**Then** 系统以树形结构展示父子关系：父块可展开查看其包含的所有子块
4. **Given** 用户点击某个子块，**When** 系统显示子块详情，**Then** 详情中包含子块内容、子块元数据、以及父块内容预览（可快速跳转）

---

### User Story 3 - 多模态内容分块 (Priority: P2)

用户需要对文档中的表格、图片等非文本内容进行独立分块处理，以便后续使用多模态模型进行向量化，提升这类内容的检索效果。

**Why this priority**: 表格和图片是文档中重要的信息载体，传统文本分块无法有效处理这类内容。独立分块配合多模态向量化可以显著提升这类内容的检索准确性。

**Independent Test**: 可以通过上传包含表格和图片的文档，验证系统是否正确识别并独立分块这些多模态内容，并检查生成的分块元数据是否包含正确的类型标识。

**Acceptance Scenarios**:

1. **Given** 用户上传了包含表格的文档，**When** 系统完成文档加载后，**Then** 系统在分块配置界面显示"检测到 N 个表格，建议启用表格独立分块"
2. **Given** 用户启用"表格独立分块"选项，**When** 用户执行分块操作，**Then** 每个表格生成独立的分块，包含表格内容（Markdown 格式）、表格位置（页码、区域）、表格标题（如有）
3. **Given** 用户上传了包含图片的文档，**When** 系统完成文档加载且用户启用"图片独立分块"选项，**Then** 每个图片生成独立的分块，包含图片引用路径、图片描述（如有 OCR 或 caption）、图片位置
4. **Given** 分块结果包含多模态内容，**When** 用户查看分块列表，**Then** 系统用不同图标或标签区分文本块、表格块、图片块

---

### User Story 4 - 混合分块策略配置 (Priority: P2)

用户需要针对同一文档的不同部分应用不同的分块策略，例如对正文使用语义分块、对代码块使用固定大小分块、对表格使用独立分块。

**Why this priority**: 复杂文档通常包含多种类型的内容，单一策略无法满足所有内容的最优分块需求。混合策略可以针对不同内容类型应用最合适的分块方法。

**Independent Test**: 可以通过上传包含正文、代码块、表格的技术文档，配置混合策略，验证各类内容是否按预期策略分块。

**Acceptance Scenarios**:

1. **Given** 用户在分块配置界面，**When** 用户选择"混合分块策略"，**Then** 系统显示内容类型列表（正文、代码块、表格、图片）及各类型的策略选择下拉框
2. **Given** 用户配置正文使用"语义分块"、代码块使用"按行数分块"、表格使用"独立分块"，**When** 用户执行分块操作，**Then** 系统按配置对各类内容分别应用对应策略
3. **Given** 混合分块完成，**When** 用户查看分块统计，**Then** 系统显示各类型内容的分块数量统计：正文块 N 个、代码块 M 个、表格块 K 个

---

### User Story 5 - 分块效果预览与对比 (Priority: P3)

用户需要在正式执行分块前预览分块效果，并能对比不同策略和参数的分块结果，以选择最优配置。

**Why this priority**: 分块是一个需要调优的过程，预览和对比功能可以帮助用户快速找到最佳配置，避免反复试错浪费时间。

**Independent Test**: 可以通过选择不同的分块策略和参数，验证预览功能是否正确显示预计结果，以及对比功能是否清晰展示差异。

**Acceptance Scenarios**:

1. **Given** 用户已选择文档和分块策略，**When** 用户调整分块参数时，**Then** 系统实时更新预估分块数量、平均块大小、预计处理时间
2. **Given** 用户点击"预览分块"按钮，**When** 系统完成预览计算（取文档前 10% 内容进行试分块），**Then** 系统显示前 10 个分块的内容预览和统计信息
3. **Given** 用户想对比不同策略，**When** 用户选择两种策略并点击"策略对比"，**Then** 系统并排显示两种策略的分块预览、统计对比（块数量、平均大小、块大小分布图）

---

### User Story 6 - 为多模态向量化准备数据 (Priority: P2)

用户需要系统在分块时为多模态内容（表格、图片）保存向量化所需的完整数据，以便后续使用 qwen3-embedding-8b 等多模态模型进行向量化。

**Why this priority**: 多模态向量化是实现表格、图片等内容有效检索的关键技术。本阶段为数据准备，确保分块结果包含向量化所需的完整信息（图片 base64、表格 Markdown）。

**Scope Clarification**: 本分支（002-doc-chunking-opt）仅负责**数据准备**，实际向量化操作在 003-vector-embedding 分支实现。

**Independent Test**: 可以通过检查多模态分块结果，验证图片分块是否包含 base64 数据，表格分块是否包含完整 Markdown 格式。

**Acceptance Scenarios**:

1. **Given** 用户对包含图片的文档执行多模态分块，**When** 分块完成，**Then** 图片分块的元数据中包含 `image_base64` 字段（图片 base64 编码数据）
2. **Given** 用户对包含表格的文档执行多模态分块，**When** 分块完成，**Then** 表格分块的 `content` 字段包含完整的 Markdown 格式表格内容
3. **Given** 分块结果包含多模态内容，**When** 用户通过 API 获取分块详情，**Then** 响应中包含 `chunk_type` 字段（text/table/image）用于后续向量化策略选择

---

### Edge Cases

- 当文档不包含任何可识别的结构（标题、段落、表格）时，系统应默认使用滑动窗口分块策略
- 当父块大小设置小于子块大小时，系统应提示参数错误并阻止执行
- 当文档中的表格格式损坏无法解析时，系统应将表格内容作为普通文本处理并记录警告
- 当图片无法提取或路径无效时，系统应跳过该图片并在结果中记录跳过原因
- 当混合策略配置中某类内容数量为 0 时，系统应自动跳过该类型的分块处理
- 当 qwen3-embedding-8b 模型对某个多模态块处理失败时，系统应尝试降级为纯文本向量化
- 当用户请求对比超过 3 种策略时，系统应提示"最多支持同时对比 3 种策略"

## Requirements *(mandatory)*

### Functional Requirements

#### 分块策略增强

- **FR-001**: 系统必须支持"父子文档分块"策略，生成两层结构的分块结果（父块用于上下文、子块用于检索）
- **FR-002**: 父子分块参数必须包含：父块大小（500-5000字符）、子块大小（100-1000字符）、子块重叠度（0-200字符）
- **FR-003**: 每个子块元数据必须包含对应父块的引用 ID，支持从子块快速定位父块
- **FR-004**: 系统必须支持"混合分块策略"，允许用户对不同内容类型（正文、代码块、表格、图片）配置不同的分块方法
- **FR-005**: 系统必须实现滑动窗口分块优化，支持配置窗口大小和步进大小，确保块之间有合理重叠避免语义截断
- **FR-005a**: 对于大文档（>50MB 或 >5000万字符），系统必须采用流式分块处理，分段加载并渐进式输出结果，避免内存溢出

#### 多模态分块支持

- **FR-006**: 系统必须支持表格独立分块，从文档加载结果中提取表格内容并生成独立的分块
- **FR-007**: 表格分块元数据必须包含：表格内容（Markdown 格式）、页码、区域坐标、表格标题（如有）、行数、列数
- **FR-008**: 系统必须支持图片独立分块，提取图片引用信息并生成独立的分块
- **FR-009**: 图片分块元数据必须包含：图片路径、页码、区域坐标、图片描述/caption（如有）、图片尺寸
- **FR-009a**: 图片分块必须采用"占位符+结构化元数据"方案：
  - **文档加载阶段**：
    - 文本中保留占位符 `[IMAGE_N: 描述]`，其中 **N 统一从 1 开始**（人类可读友好）
    - images 数组包含完整图片数据（file_path 用于展示，base64_data 用于多模态嵌入），其中 `image_index` **从 0 开始**
    - **重要约定**：所有文档加载器（docling_serve_client、unstructured_loader、docx_loader、html_loader 等）必须遵循此规范，占位符索引 = image_index + 1
  - **分块阶段**：
    - 多模态分块器根据占位符正则匹配 `\[IMAGE_(\d+):\s*([^\]]*)\]`
    - **注意索引转换**：占位符索引（从1开始）与 images 数组的 image_index（从0开始）存在偏移，需将占位符索引减 1 后再关联 images 数组中的对应图片数据
  - 图片块元数据包含：image_path、image_base64、alt_text、caption、width、height、mime_type、context_before、context_after
- **FR-010**: 分块结果必须通过类型字段（type: text/table/image/code）区分不同类型的分块

#### 智能策略推荐

- **FR-011**: 系统必须在用户选择文档后，自动分析文档结构特征（标题层级、段落分布、表格数量、图片数量、代码块数量）
- **FR-012**: 系统必须基于文档结构特征推荐最适合的分块策略，并显示推荐理由
- **FR-013**: 推荐算法必须支持以下规则：
  - 标题层级清晰（H1/H2/H3数量>5）→ 推荐按标题分块
  - 包含表格/图片（数量>3）→ 推荐多模态分块
  - 连续长文本无明显结构 → 推荐语义分块
  - 代码为主的文档 → 推荐混合分块（代码按行数、文本按语义）

#### 分块预览与对比

- **FR-014**: 系统必须支持分块预览功能，使用文档前 10% 内容进行试分块并展示结果
- **FR-015**: 系统必须支持策略对比功能，并排展示最多 3 种策略的分块结果对比
- **FR-015a**: 系统必须保留同一文档的历史分块版本，支持版本对比和回滚到历史版本
- **FR-016**: 对比结果必须包含：块数量、平均块大小、最大/最小块大小、块大小分布图

#### 向量模型支持（数据准备）

**注意**: 以下需求为向量化**数据准备**，实际向量化操作在 003-vector-embedding 分支实现。

- **FR-017**: 语义分块必须支持统一 EmbeddingService，可选模型包括：bge-m3（推荐，1024维，8K上下文，快速）、qwen3-embedding-8b（4096维，32K上下文，高精度）、hunyuan-embedding（1024维）
- **FR-017a**: 语义分块采用三级降级机制：1) 首选 EmbeddingService 2) TF-IDF 相似度 3) 句子累加
- **FR-017b**: 分块结果必须包含支持后续向量化所需的数据结构（chunk_type、image_base64、table_markdown）
- **FR-018**: 系统必须为不同类型分块保存向量化所需的完整数据：
  - 文本块：content 字段包含完整文本
  - 表格块：content 字段包含 Markdown 格式表格
  - 图片块：metadata 包含 image_path（用于展示）和 image_base64（用于多模态嵌入），分块器从文档加载结果的 images 数组获取完整数据
- **FR-019**: 分块元数据必须包含 chunk_type 字段，用于后续向量化时选择合适的处理方式

#### 前端交互优化

- **FR-020**: 分块配置界面必须以卡片形式展示策略推荐，包含推荐策略、推荐理由、预估效果
- **FR-020a**: 语义分块和混合分块配置界面必须提供 Embedding 模型选择器，支持 bge-m3、qwen3-embedding-8b、hunyuan-embedding，并显示各模型的维度、上下文长度、特点说明
- **FR-021**: 分块结果展示必须支持树形视图（用于父子分块）和列表视图（用于普通分块）的切换
- **FR-022**: 分块结果列表必须使用图标区分不同类型的分块（文本/表格/图片/代码）
- **FR-023**: 前端必须支持实时参数预览，用户调整参数时即时更新预估结果

#### 分块结果可视化

- **FR-024**: 分块结果可视化必须支持三种视图模式：线性视图、树状视图、统计视图
  - 线性视图：以列表形式展示分块，适用于 character、paragraph、heading、semantic 策略
  - 树状视图：以树形结构展示父子/标题层级关系，适用于 parent_child、heading 策略
  - 统计视图：展示块大小分布图表和统计信息，适用于所有策略
- **FR-025**: 统计视图必须展示以下统计指标：
  - 块大小分布直方图
  - 平均块大小、最大块大小、最小块大小
  - 总块数、文本块数、表格块数、图片块数、代码块数
  - 块类型分布饼图
- **FR-026**: 可视化工具栏必须支持以下导出功能：
  - 导出为 Mermaid 图（树状结构的图表表示）
  - 导出为 JSON（完整分块数据）
  - 复制统计信息到剪贴板
- **FR-027**: 线性视图必须明确提示用户当前仅显示前 50 个分块（当分块总数超过 50 时），避免用户困惑

### Key Entities

#### 已实现的分块器 (Chunker Registry)

系统支持以下 6 种分块策略，由 `ChunkingService` 统一调度：

| 分块器 | 策略类型 | 描述 | 适用场景 |
|--------|----------|------|----------|
| `CharacterChunker` | character | 按固定字符数分块，支持重叠 | 通用文本、快速分块 |
| `ParagraphChunker` | paragraph | 以自然段落为单位，尊重段落边界 | 结构清晰的文档 |
| `HeadingChunker` | heading | 按 H1/H2/H3 标题层级分块 | 技术文档、有标题结构的文档 |
| `SemanticChunker` | semantic | 基于语义相似度智能分块 | 连续叙事文本、无明显结构 |
| `ParentChildChunker` | parent_child | 生成父子两层分块结构 | 需要精确检索+完整上下文 |
| `HybridChunker` | hybrid | 混合策略，针对不同内容类型应用不同策略 | 复杂文档（含代码、表格、图片） |

#### 分块器参数详解

**CharacterChunker 参数**：
```python
{
    "chunk_size": 500,     # 块大小（字符数），范围 50-5000
    "overlap": 50          # 重叠度（字符数），范围 0-500
}
```

**ParagraphChunker 参数**：
```python
{
    "min_chunk_size": 200,   # 最小块大小
    "max_chunk_size": 1000,  # 最大块大小
    "preserve_paragraphs": True  # 是否保留完整段落
}
```

**HeadingChunker 参数**：
```python
{
    "min_heading_level": 1,  # 最小标题级别（H1=1）
    "max_heading_level": 3,  # 最大标题级别（H3=3）
    "include_heading": True  # 块中是否包含标题文本
}
```

**SemanticChunker 参数**：
```python
{
    "similarity_threshold": 0.3,  # TF-IDF 相似度阈值
    "embedding_similarity_threshold": 0.7,  # Embedding 相似度阈值
    "min_chunk_size": 300,        # 最小块大小
    "max_chunk_size": 1200,       # 最大块大小
    "use_embedding": True,        # 是否使用 Embedding（否则用 TF-IDF）
    "embedding_model": "bge-m3"   # Embedding 模型选择
}
```

**ParentChildChunker 参数**：
```python
{
    "parent_chunk_size": 2000,   # 父块大小，范围 500-10000
    "child_chunk_size": 500,     # 子块大小，范围 100-2000
    "child_overlap": 50,         # 子块重叠度，范围 0-500
    "parent_overlap": 200        # 父块重叠度，范围 0-1000
}
```

**HybridChunker 参数**：
```python
{
    # 文本分块配置
    "text_strategy": "semantic",     # 正文策略: semantic|paragraph|character|heading|none
    "text_chunk_size": 500,          # 文本块大小
    "text_overlap": 50,              # 文本块重叠度
    "embedding_model": "bge-m3",     # 语义分块的 Embedding 模型
    "use_embedding": True,           # 是否启用 Embedding
    
    # 代码分块配置
    "code_strategy": "lines",        # 代码策略: lines|character|none
    "code_chunk_lines": 50,          # 按行数分块时的行数
    
    # 表格配置
    "table_strategy": "independent", # 表格策略: independent|merge_with_text
    "min_table_rows": 2,             # 最小表格行数阈值
    
    # 多模态内容提取
    "include_tables": True,          # 是否提取表格
    "include_images": True,          # 是否提取图片
    "include_code": True,            # 是否提取代码块
    "min_code_lines": 3,             # 最小代码行数阈值
    "image_base_path": None          # 图片路径基础目录
}
```

#### SemanticChunker 三级降级机制

语义分块采用三级降级策略确保稳定性：

```
1. 首选: EmbeddingService（支持 bge-m3、qwen3-embedding-8b、hunyuan-embedding）
   │
   ├─ 成功 → 使用 Embedding 向量计算句子间相似度
   │
   └─ 失败（API 不可用/超时）
       │
       ▼
2. 备选: TF-IDF 相似度
   │
   ├─ 成功 → 使用词频-逆文档频率计算相似度
   │
   └─ 失败（句子数不足/计算失败）
       │
       ▼
3. 兜底: 句子累加分块
   │
   └─ 按 min_chunk_size 累加句子，生成基础分块
```

**支持的 Embedding 模型**：
| 模型 | 维度 | 上下文长度 | 特点 |
|------|------|------------|------|
| bge-m3 | 1024 | 8K | 多语言、速度快（推荐） |
| qwen3-embedding-8b | 4096 | 32K | 高精度、长上下文 |
| hunyuan-embedding | 1024 | - | 腾讯混元 |

#### ImageExtractor 统一图片提取模块

为保持所有分块策略的图片处理一致性，系统实现了统一的 `ImageExtractor` 模块：

**核心功能**：
- 从文档加载结果的 `images` 数组获取图片数据
- 根据文本中的占位符 `[IMAGE_N: 描述]` 关联图片
- 生成标准化的图片分块，包含 base64 数据用于多模态嵌入

**图片分块元数据结构**：
```python
{
    "chunk_type": "image",
    "chunk_id": str,
    "image_index": int,           # 图片索引
    "image_path": str,            # 图片文件路径（展示用）
    "image_base64": str,          # Base64 编码（嵌入用）
    "alt_text": str,              # 替代文本
    "caption": str,               # 图片标题
    "width": int,                 # 宽度
    "height": int,                # 高度
    "mime_type": str,             # MIME 类型
    "page_number": int,           # 所在页码
    "context_before": str,        # 图片前上下文
    "context_after": str,         # 图片后上下文
    "section_title": str          # 所属章节标题
}
```

#### 分块类型枚举 (ChunkTypeEnum)

```python
class ChunkTypeEnum:
    TEXT = "text"      # 文本块
    TABLE = "table"    # 表格块
    IMAGE = "image"    # 图片块
    CODE = "code"      # 代码块
```

#### 分块结果数据结构

**标准分块结果 (ChunkingResult)**：
```python
{
    "task_id": str,
    "document_id": str,
    "strategy_type": str,          # character|paragraph|heading|semantic|parent_child|hybrid
    "parameters": Dict,            # 使用的分块参数
    "total_chunks": int,           # 总块数
    "statistics": {
        "avg_chunk_size": float,
        "max_chunk_size": int,
        "min_chunk_size": int,
        "char_count_distribution": List[int]
    },
    "chunks": [
        {
            "content": str,
            "chunk_type": str,     # text|table|image|code
            "parent_id": str,      # 父块 ID（parent_child 策略）
            "metadata": {
                "chunk_id": str,
                "chunk_index": int,
                "char_count": int,
                "word_count": int,
                "start_position": int,
                "end_position": int,
                "page_number": int,
                "sheet_name": str,
                # 表格特有字段
                "table_markdown": str,
                "row_count": int,
                "column_count": int,
                "headers": List[str],
                # 图片特有字段
                "image_base64": str,
                "image_path": str,
                "alt_text": str,
                # 代码特有字段
                "language": str,
                "function_name": str,
                "class_name": str,
                # 上下文字段
                "context_before": str,
                "context_after": str,
                "section_title": str
            }
        }
    ],
    "created_at": str              # ISO 格式时间戳
}
```

**父子分块结果扩展**：
```python
{
    # ... 基础字段 ...
    "total_parent_chunks": int,
    "parent_chunks": [
        {
            "content": str,
            "chunk_type": "parent",
            "metadata": {
                "chunk_id": str,
                "child_count": int,
                "child_ids": List[str]
            }
        }
    ],
    "chunks": [
        # 子块，包含 parent_id 引用
    ]
}
```

- **ParentChildChunk**: 父子分块结构，parent 包含完整上下文内容，children 为子块 ID 列表，每个子块包含 parent_id 引用
- **MultimodalChunk**: 多模态分块实体，包含 type 字段（text/table/image/code）和对应类型的专属元数据
- **ChunkingRecommendation**: 策略推荐实体，包含推荐策略、推荐理由、文档特征分析结果、预估效果指标
- **ChunkingComparison**: 策略对比结果实体，包含多个策略的分块统计对比数据


### Assumptions

- 文档加载结果（来自 001-document-processing-opt）已包含结构化的表格和图片信息，图片数据包含 file_path（展示用）和 base64_data（嵌入用）
- 文档加载阶段默认启用 `embed_images_base64=True`，确保图片 base64 数据可用于多模态嵌入
- qwen3-embedding-8b 模型已部署并可通过 API 访问，支持文本和图片的多模态输入
- 图片分块的向量化依赖图片 base64 编码（来自加载结果的 images 数组），通过占位符 `[IMAGE_N: 描述]` 进行关联
- 父子分块的检索策略为：使用子块进行初始检索，命中后返回对应父块内容作为上下文传递给 LLM
- 混合分块策略中，未配置策略的内容类型将使用默认策略（正文→语义分块、代码→按行数、表格/图片→独立分块）

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 用户能够在 1 分钟内完成分块策略选择和参数配置（包括查看推荐和对比预览）
- **SC-002**: 使用父子分块策略后，检索命中率提升 20% 以上（对比相同参数的普通分块）
- **SC-003**: 多模态分块功能正确识别并独立处理 95% 以上的表格内容
- **SC-004**: qwen3-embedding-8b 模型对多模态分块的向量化成功率达到 98% 以上
- **SC-005**: 策略推荐准确率达到 85% 以上（用户采纳推荐策略的比例）
- **SC-006**: 分块预览功能的响应时间在 3 秒内完成（针对 10000 字符以内的文档）
- **SC-007**: 80% 的用户在首次使用混合分块策略时能够成功完成配置
- **SC-008**: 前端分块界面的用户满意度评分达到 4 分以上（5 分制）

## Change Log

| 日期 | 类型 | 变更内容 | 影响需求 |
|------|------|----------|----------|
| 2026-01-20 | 初始版本 | 创建 002-doc-chunking-opt 功能规格文档 | - |
| 2026-01-30 | BugFix | 修复 `validate_hybrid_params` 验证器丢失 `embedding_model` 参数的问题，导致混合分块策略中语义分块始终使用默认的 bge-m3 模型而非用户选择的模型 | FR-017, FR-020a |
| 2026-02-02 | Feature | 新增分块结果可视化功能需求（FR-024 ~ FR-027），支持线性视图、树状视图、统计视图三种展示模式，以及 Mermaid 图导出功能 | FR-024, FR-025, FR-026, FR-027 |
| 2026-02-02 | BugFix | [VIBE] 修复父子分块统计视图中平均父块大小显示为0、块大小分布总数只统计前50个分块的问题，在后端添加 `avg_parent_size` 和 `size_distribution` 计算逻辑 | FR-026 |
| 2026-02-04 | BugFix | 修复 ImageExtractor 图片索引偏移问题：占位符 `[IMAGE_N]` 中 N 从 1 开始，而 images 数组的 `image_index` 从 0 开始，导致图片无法正确关联。修复方法：在 `_extract_placeholder_images` 中将占位符索引减 1 后再匹配 | FR-009a |
| 2026-02-04 | BugFix | 统一所有文档加载器的图片占位符索引从 1 开始：修复 unstructured_loader（2处）、docx_loader（1处）、docling_serve_client（1处）中占位符使用 0-based 索引的问题，确保与 ImageExtractor 的索引转换逻辑一致 | FR-009a |
