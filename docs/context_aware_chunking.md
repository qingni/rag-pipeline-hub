# 上下文感知分块（Context-Aware Chunking）功能说明

## 功能概述

为混合分块策略（Hybrid Chunker）添加了**上下文保留**功能，确保表格、图片、代码块等非文本元素在分块时保留其周围的上下文信息，从而提高 RAG 系统的检索和生成质量。

## 问题背景

在使用混合分块策略时，遇到以下问题：

1. **表格与标题分离**：表格前的标题（如 `## 2023 年度富豪榜`）与表格内容被分开到不同的块中，导致表格块缺少必要的上下文
2. **图片与文本分离**：图片占位符（如 `[IMAGE_12: Image]`可能被切分到不同的块中，无法知道图片所属的章节
3. **代码块与上下文分离**：代码块可能独立存在，无法知道代码所在的上下文

## 解决方案

采用**方案 A：上下文保留策略（Context-Aware Chunking）**，这是业界主流框架（LlamaIndex、LangChain、Unstructured）采用的标准做法。

### 核心思想

- **不改变分块边界**：表格、图片、代码块仍然作为独立块存在
- **在 metadata 中保留上下文关系**：将前文、后文、所属章节标题等信息存储在 metadata 中
- **检索时利用上下文扩展**：在生成答案时，可以利用这些上下文信息提供更准确的回答

### 实现细节

#### 1. 数据模型扩展

为 `TableChunkMetadata` 和 `CodeChunkMetadata` 添加了以下字段：

```python
@dataclass
class TableChunkMetadata(BaseChunkMetadata):
    """Metadata for table chunks."""
    chunk_type: str = "table"
    # ... 原有字段 ...
    # ✨ 新增字段
    context_before: Optional[str] = None  # 文本上下文
    context_after: Optional[str] = None   # 文本上下文
    section_title: Optional[str] = None    # 所属章节标题
```

#### 2. 上下文提取方法

在 `HybridChunker` 中实现了 `_extract_context()` 方法：

```python
def _extract_context(
    self,
    text: str,
    start_pos: int,
    end_pos: int,
    context_chars: int = 300
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    提取元素前后的上下文文本和所属章节标题。

    Returns:
        Tuple of (section_title, context_before, context_after)
        - section_title: 最近的章节标题（## xxx）
        - context_before: 元素前的文本摘要（最多300字符）
        - context_after: 元素后的文本摘要（最多300字符）
    """
```

**功能特性：**
- 自动查找最近的 Markdown 标题（`## xxx`）
- 提取元素前后的文本（最多 300 字符）
- 智能在句号处断开，保持句子完整

#### 3. 表格分块增强

修改 `_extract_tables_from_page()` 方法：

```python
# 提取表格
section_title, context_before, context_after = self._extract_context(
    text=text,
    start_pos=start_pos,
    end_pos=end_pos,
    context_chars=300
)

# 创建 metadata
table_metadata = create_chunk_metadata(
    chunk_type=ChunkTypeEnum.TABLE.value,
    # ... 其他参数 ...
    # ✨ 添加上下文
    context_before=context_before,
    context_after=context_after,
    section_title=section_title
)
```

#### 4. 图片分块增强

修改 `ImageExtractor._create_image_chunk()` 方法：

```python
# 提取上下文
context_before = None
context_after = None
section_title = None

# 从页面文本中提取上下文
text_before = page_text[:local_pos]
heading_pattern = r'^(#{1,6})\s+(.+)$'
# ... 提取逻辑 ...

# 创建 metadata
image_metadata = create_chunk_metadata(
    chunk_type=ChunkTypeEnum.IMAGE.value,
    # ... 其他参数 ...
    # ✨ 添加上下文
    context_before=context_before,
    context_after=context_after,
    section_title=section_title
)
```

#### 5. 代码块分块增强

修改 `_extract_code_from_page()` 方法：

```python
# 提取上下文
section_title, context_before, context_after = self._extract_context(
    text=text,
    start_pos=start_pos,
    end_pos=end_pos,
    context_chars=300
)

# 创建 metadata
code_metadata = create_chunk_metadata(
    chunk_type=ChunkTypeEnum.CODE.value,
    # ... 其他参数 ...
    # ✨ 添加上下文
    context_before=context_before,
    context_after=context_after,
    section_title=section_title
)
```

## 使用示例

### 输入文本

```markdown
## 2023 年度富豪榜

在2023年的福布斯全球亿万富豪榜中，共有2640位亿万富翁，总财富达到12.2万亿美元。

| No. | Name | Net worth (USD) | Age | Nationality |
|------|-------|------------------|-----|-------------|
| 1 | Bernard Arnault | $211 billion | 74 | France |
| 2 | Elon Musk | $180 billion | 51 | United States |

这是世界富豪排行榜的最新数据。
```

### 输出示例

#### 表格块

```json
{
  "content": "| No. | Name | Net worth (USD) | ...",
  "chunk_type": "table",
  "metadata": {
    "section_title": "## 2023 年度富豪榜",
    "context_before": "在2023年的福布斯全球亿万富豪榜中，共有2640位亿万富翁，总财富达到12.2万亿美元。",
    "context_after": "这是世界富豪排行榜的最新数据。",
    "row_count": 2,
    "column_count": 4
  }
}
```

#### 图片块

```json
{
  "content": "[Image: 财富排行榜图表]",
  "chunk_type": "image",
  "metadata": {
    "section_title": "## 2023 年度富豪榜",
    "context_before": "共有2640位亿万富翁，总财富达到12.2万亿美元。",
    "context_after": "这是世界富豪排行榜的最新数据。",
    "image_path": "/path/to/image.png"
  }
}
```

#### 代码块

```json
{
  "content": "def get_billionaire(name):\n    return f\"Billionaire: {name}\"",
  "chunk_type": "code",
  "metadata": {
    "section_title": "## 数据处理函数",
    "context_before": "在富豪榜中，我们需要处理富豪数据。",
    "context_after": "这个函数用于格式化输出。",
    "language": "python"
  }
}
```

## 在 RAG 检索和生成中的使用

### 检索阶段

1. 找到相关的表格/图片/代码块
2. 从 metadata 中提取 `section_title`、`context_before`、`context_after`
3. 可以利用这些信息计算相关性得分

### 生成阶段

```python
def build_context_for_generation(chunk):
    """构建生成上下文"""
    context_parts = []

    # 1. 添加章节标题
    if chunk.metadata.get("section_title"):
        context_parts.append(chunk.metadata["section_title"])

    # 2. 添加前文摘要
    if chunk.metadata.get("context_before"):
        context_parts.append(chunk.metadata["context_before"])

    # 3. 添加块内容
    context_parts.append(chunk.content)

    # 4. 添加后文摘要
    if chunk.metadata.get("context_after"):
        context_parts.append(chunk.metadata["context_after"])

    return "\n\n".join(context_parts)

# 使用示例
context = build_context_for_generation(table_chunk)
prompt = f"""
请根据以下信息回答问题：

{context}

问题：{question}
"""
```

## 优势

### 1. 精确检索
- 表格/图片/代码块仍然作为独立的、小的块存在
- 检索时可以精确匹配这些块的内容

### 2. 上下文完整
- 在生成答案时，可以利用 metadata 中的上下文信息
- 避免因为缺少上下文而产生的幻觉或不准确答案

### 3. 灵活扩展
- 可以根据需要决定使用多少上下文
- 可以使用章节标题进行导航

### 4. 业界标准
- 符合 LlamaIndex、LangChain、Unstructured 等主流框架的设计
- 便于与其他系统集成

## 与其他方案的对比

| 方案 | 业界采用度 | 复杂度 | 灵活性 | 推荐度 |
|------|-----------|--------|--------|--------|
| **A. 上下文保留** | ⭐⭐⭐⭐⭐⭐ (LlamaIndex, LangChain) | 中等 | 高 | ✅ **推荐** |
| B. 标题绑定 | ⭐⭐⭐ (Azure, AWS) | 低 | 中 | 适合简单场景 |
| C. 多级索引 | ⭐⭐⭐⭐⭐ (Pinecone, Weaviate) | 高 | 很高 | 适合大规模系统 |

## 测试验证

运行测试脚本验证功能：

```bash
python test_context_aware.py
```

预期输出：
- ✅ 表格块包含章节标题
- ✅ 表格块包含前文
- ✅ 表格块包含后文
- ✅ 代码块包含上下文（如果有）

## 相关文件

### 修改的文件

1. `backend/src/models/chunk_metadata.py`
   - 为 `TableChunkMetadata` 添加 `context_before`、`context_after`、`section_title`
   - 为 `CodeChunkMetadata` 添加 `context_before`、`context_after`、`section_title`

2. `backend/src/providers/chunkers/hybrid_chunker.py`
   - 添加 `_extract_context()` 方法
   - 修改 `_extract_tables_from_page()` 调用上下文提取
   - 修改 `_extract_code_from_page()` 调用上下文提取

3. `backend/src/providers/chunkers/image_extractor.py`
   - 修改 `_create_image_chunk()` 方法，为 Markdown/HTML 格式的图片添加上下文提取

### 测试文件

4. `test_context_aware.py`
   - 完整的上下文感知分块测试脚本

## 未来改进方向

1. **上下文长度可配置**
   - 允许用户通过参数调整上下文提取的字符数（当前默认为 300）

2. **智能上下文选择**
   - 根据元素类型选择不同的上下文策略
   - 例如：表格可能需要标题，代码块可能需要更多前文

3. **块间关系**
   - 添加 `previous_chunk_id`、`next_chunk_id` 等关系字段
   - 支持 LlamaIndex 风格的层级索引

4. **多语言支持**
   - 改进标题提取逻辑，支持中文、英文、日文等多语言

## 总结

上下文感知分块功能已经成功实现并测试通过。这个功能显著提升了混合分块策略在处理复杂文档（包含表格、图片、代码块）时的检索质量，是构建高质量 RAG 系统的重要一步。
