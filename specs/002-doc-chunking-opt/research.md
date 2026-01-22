# Research: 文档分块功能优化

**Branch**: `002-doc-chunking-opt` | **Date**: 2026-01-20

## 1. 父子文档分块 (Parent-Child Chunking)

### Decision
采用 LangChain 的 `ParentDocumentRetriever` 模式实现父子分块，子块用于检索，父块用于上下文传递。

### Rationale
- 子块（小块）提供精确的语义匹配，提升检索准确率
- 父块（大块）保持上下文完整性，提升 LLM 生成质量
- 业界 RAG 最佳实践，已在 LlamaIndex、LangChain 中广泛应用

### Alternatives Considered
| 方案 | 优点 | 缺点 | 结论 |
|------|------|------|------|
| 仅小块检索 | 实现简单 | 上下文丢失，生成质量差 | ❌ 拒绝 |
| 仅大块检索 | 上下文完整 | 检索精度低，噪声大 | ❌ 拒绝 |
| 父子分块 | 兼顾精度和上下文 | 存储增加，逻辑复杂 | ✅ 采用 |
| 滑动窗口扩展 | 实现较简单 | 块边界不自然，冗余大 | ❌ 备选 |

### Implementation Approach
```python
# 父块：使用 RecursiveCharacterTextSplitter (chunk_size=2000)
# 子块：从父块中再切分 (chunk_size=400, overlap=50)
# 存储：子块 metadata 中包含 parent_id 引用
# 检索：子块向量检索 → 命中后返回 parent.content
```

---

## 2. 语义分块算法升级 (Embedding-based Semantic Chunking)

### Decision
升级为基于 Embedding 相似度的语义分块（LangChain SemanticChunker），TF-IDF 作为 fallback。

### Rationale
- Embedding 模型能捕捉深层语义关系，优于 TF-IDF 的词频统计
- LangChain 的 `SemanticChunker` 已封装完善，开箱即用
- TF-IDF 作为 fallback 确保 Embedding 服务不可用时系统仍能工作

### Alternatives Considered
| 方案 | 优点 | 缺点 | 结论 |
|------|------|------|------|
| 保持 TF-IDF | 无需外部依赖 | 语义理解能力弱 | ❌ 拒绝 |
| 完全替换 Embedding | 效果最佳 | 依赖外部服务，单点故障 | ❌ 拒绝 |
| Embedding + TF-IDF fallback | 效果好+高可用 | 实现稍复杂 | ✅ 采用 |

### Implementation Approach
```python
from langchain_experimental.text_splitter import SemanticChunker
from langchain_openai.embeddings import OpenAIEmbeddings

# 主策略：Embedding 相似度
chunker = SemanticChunker(
    embeddings=OpenAIEmbeddings(),
    breakpoint_threshold_type="percentile",
    breakpoint_threshold_amount=95
)

# Fallback：TF-IDF（现有实现）
if embedding_service_unavailable:
    chunker = TFIDFSemanticChunker(...)
```

---

## 3. 多模态内容分块 (Multimodal Chunking)

### Decision
表格和图片从文档加载结果中提取，生成独立分块，通过 `type` 字段区分。

### Rationale
- 表格/图片是重要信息载体，需独立向量化才能有效检索
- 001-document-processing-opt 已提供结构化的表格/图片提取结果
- 独立分块便于后续使用多模态模型向量化

### Implementation Approach
```python
# 文档加载结果结构（来自 001-document-processing-opt）
{
    "content": {
        "full_text": "...",
        "tables": [{"markdown": "...", "page": 1, "bbox": [...]}],
        "images": [{"path": "...", "caption": "...", "page": 2}]
    }
}

# 多模态分块器处理
class MultimodalChunker(BaseChunker):
    def chunk(self, document_result):
        chunks = []
        # 文本分块
        text_chunks = self.text_chunker.chunk(document_result["content"]["full_text"])
        chunks.extend([{**c, "type": "text"} for c in text_chunks])
        # 表格独立分块
        for table in document_result["content"]["tables"]:
            chunks.append({"content": table["markdown"], "type": "table", ...})
        # 图片独立分块
        for image in document_result["content"]["images"]:
            chunks.append({"content": image["caption"], "type": "image", ...})
        return chunks
```

---

## 4. qwen3-embedding-8b 多模态向量化

### Decision
扩展现有 EmbeddingService，新增 qwen3-embedding-8b 模型支持，图片优先使用 base64 直接向量化。

### Rationale
- qwen3-embedding-8b 是高质量多模态 Embedding 模型，支持文本+图片
- 现有 embedding_service.py 已有 qwen3-vl-embedding-8b 配置，架构兼容
- 图片 base64 向量化比文本描述能保留更多视觉信息

### Model Comparison
| 模型 | 维度 | 多模态 | 适用场景 |
|------|------|--------|----------|
| bge-m3 | 1024 | ❌ | 纯文本检索 |
| qwen3-embedding-8b | 4096 | ✅ | 文本+表格+图片 |
| qwen3-vl-embedding-8b | 64-4096 | ✅ | 视频场景 |

### Implementation Approach
```python
# 扩展 EmbeddingService
def embed_multimodal_chunk(self, chunk):
    if chunk["type"] == "text":
        return self.embed_text(chunk["content"])
    elif chunk["type"] == "table":
        return self.embed_text(chunk["content"])  # Markdown 格式
    elif chunk["type"] == "image":
        try:
            # 优先使用图片 base64 向量化
            image_base64 = self._load_image_base64(chunk["image_path"])
            return self.embed_image(image_base64)
        except:
            # 降级为文本描述向量化
            return self.embed_text(chunk["caption"])
```

---

## 5. 智能策略推荐算法

### Decision
基于文档结构特征（标题/段落/表格/代码）的规则引擎推荐，支持多策略组合推荐。

### Rationale
- 规则引擎可解释性强，推荐理由清晰
- 基于文档结构分析，不依赖外部服务
- 可逐步迭代为机器学习模型

### Recommendation Rules
| 文档特征 | 推荐策略 | 推荐理由 |
|----------|----------|----------|
| H1/H2/H3 数量 > 5 | 按标题分块 | 检测到清晰的标题层级结构 |
| 表格/图片数量 > 3 | 多模态分块 | 包含大量非文本内容 |
| 代码块占比 > 30% | 混合分块 | 代码为主的技术文档 |
| 无明显结构 | 语义分块 | 连续叙事文本 |

### Implementation Approach
```python
class ChunkingRecommendService:
    def analyze_document(self, document_result) -> DocumentFeatures:
        return DocumentFeatures(
            heading_count=self._count_headings(text),
            table_count=len(document_result["content"]["tables"]),
            image_count=len(document_result["content"]["images"]),
            code_block_ratio=self._calculate_code_ratio(text),
            avg_paragraph_length=self._avg_paragraph_length(text)
        )
    
    def recommend(self, features: DocumentFeatures) -> ChunkingRecommendation:
        if features.heading_count > 5:
            return ChunkingRecommendation("heading", "检测到清晰的标题层级结构")
        elif features.table_count + features.image_count > 3:
            return ChunkingRecommendation("multimodal", "包含大量非文本内容")
        ...
```

---

## 6. 大文档流式处理

### Decision
采用生成器模式实现流式分块，分段加载文档，渐进式输出结果。

### Rationale
- 避免大文档一次性加载导致内存溢出
- 用户可实时看到分块进度，提升体验
- 适配 FastAPI 的 StreamingResponse

### Implementation Approach
```python
class StreamingChunker:
    def chunk_stream(self, text: str, chunk_size: int = 100000):
        """流式分块，每次处理 chunk_size 字符"""
        for i in range(0, len(text), chunk_size):
            segment = text[i:i + chunk_size]
            for chunk in self._chunk_segment(segment, offset=i):
                yield chunk

# API 端点
@router.post("/chunking/stream")
async def stream_chunk(request: ChunkingRequest):
    async def generate():
        async for chunk in chunking_service.chunk_stream(request.text):
            yield f"data: {chunk.json()}\n\n"
    return StreamingResponse(generate(), media_type="text/event-stream")
```

---

## 7. 分块版本管理

### Decision
保留历史版本，支持版本对比和回滚，已有数据模型支持（ChunkingResult.version, previous_version_id）。

### Rationale
- 用户可对比不同参数的分块效果
- 误操作后可回滚到历史版本
- 现有 ChunkingResult 模型已支持版本字段

### Implementation Approach
```python
# 现有模型已支持
class ChunkingResult(Base):
    version = Column(Integer, default=1)
    previous_version_id = Column(String(36))
    is_active = Column(Boolean, default=True)
    replacement_reason = Column(String(200))

# 新增服务方法
def create_new_version(self, document_id, strategy, params):
    previous = self._get_active_version(document_id)
    if previous:
        previous.is_active = False
    new_result = ChunkingResult(
        version=previous.version + 1 if previous else 1,
        previous_version_id=previous.result_id if previous else None,
        ...
    )
```

---

## 8. 前端策略推荐卡片 UI

### Decision
使用 TDesign Card 组件展示策略推荐，包含推荐理由、预估效果、一键应用按钮。

### UI Layout
```
┌─────────────────────────────────────────┐
│ 🎯 推荐策略                              │
├─────────────────────────────────────────┤
│ ┌─────────────────────────────────────┐ │
│ │ 📊 按标题分块           [推荐] ✨  │ │
│ │ 检测到清晰的标题层级结构            │ │
│ │ H1: 3个  H2: 12个  H3: 25个        │ │
│ │ 预估：约 40 个文本块                │ │
│ │              [应用此策略]           │ │
│ └─────────────────────────────────────┘ │
│                                         │
│ [查看所有策略对比]                       │
└─────────────────────────────────────────┘
```

### Component Structure
```vue
<template>
  <t-card title="🎯 推荐策略" :bordered="true">
    <t-card 
      v-for="rec in recommendations" 
      :key="rec.strategy"
      :class="{ 'recommended': rec.isTop }"
    >
      <template #title>
        <ChunkTypeIcon :type="rec.strategy" />
        {{ rec.strategyName }}
        <t-tag v-if="rec.isTop" theme="primary">推荐</t-tag>
      </template>
      <p>{{ rec.reason }}</p>
      <p>预估：约 {{ rec.estimatedChunks }} 个文本块</p>
      <t-button @click="applyStrategy(rec.strategy)">应用此策略</t-button>
    </t-card>
  </t-card>
</template>
```
