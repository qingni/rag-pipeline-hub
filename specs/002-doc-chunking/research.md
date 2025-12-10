# Research Document: 文档分块功能

**Feature**: 002-doc-chunking  
**Date**: 2025-12-05  
**Purpose**: 研究和评估文档分块技术、算法和最佳实践

## Research Tasks

### 1. 文档分块库和算法评估

#### Decision: 使用 LangChain TextSplitters 作为核心分块引擎

#### Rationale:
- **成熟稳定**: LangChain 是行业标准的文档处理框架，已在生产环境广泛使用
- **开箱即用**: 提供 RecursiveCharacterTextSplitter, ParagraphTextSplitter, SemanticChunker 等多种分块器
- **已集成**: 项目已安装 `langchain-text-splitters==0.3.4`，无需额外依赖
- **可扩展**: 支持自定义分块策略，便于实现按标题分块等特殊需求
- **性能优异**: 经过优化，处理大文档效率高

#### Alternatives Considered:
- **NLTK + 自定义算法**: 需要更多开发工作，且 NLTK 主要用于英文，中文支持较弱
- **spaCy 分句**: 依赖大型语言模型，性能开销大，不适合实时处理
- **纯正则表达式**: 灵活性差，难以处理复杂文档结构
- **Hugging Face Tokenizers**: 更适合模型输入，不适合语义完整性保持

#### Implementation Details:
```python
# 1. 按字数分块: RecursiveCharacterTextSplitter
from langchain_text_splitters import RecursiveCharacterTextSplitter
splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=100,
    length_function=len,
    separators=["\n\n", "\n", " ", ""]
)

# 2. 按段落分块: Custom based on paragraph detection
# 使用 \n\n 作为段落分隔符，手动实现以支持中文段落

# 3. 按标题分块: MarkdownHeaderTextSplitter (for structured docs)
from langchain_text_splitters import MarkdownHeaderTextSplitter
# 或自定义实现以支持 HTML heading tags

# 4. 按语义分块: SemanticChunker (experimental)
# 使用基础的句子边界检测，降级为段落分块
```

---

### 2. 并发任务队列管理

#### Decision: 使用 Python asyncio Queue + 内存队列管理器

#### Rationale:
- **轻量级**: 无需外部依赖（如 Celery, RQ），适合单机部署
- **FastAPI 原生支持**: asyncio 与 FastAPI 完美集成
- **可控性强**: 可精确控制并发数量和队列行为
- **即时反馈**: 用户可实时查看队列状态

#### Alternatives Considered:
- **Celery + Redis**: 功能强大但过于复杂，需要额外的 Redis 依赖和运维成本
- **Python multiprocessing**: 进程间通信复杂，不适合需要频繁状态更新的场景
- **Background Tasks (FastAPI)**: 无法限制并发数量，不满足需求

#### Implementation Strategy:
```python
import asyncio
from typing import Dict, List
from enum import Enum

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class ChunkingQueueManager:
    def __init__(self, max_concurrent=3):
        self.max_concurrent = max_concurrent
        self.queue = asyncio.Queue()
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.task_status: Dict[str, TaskStatus] = {}
    
    async def add_task(self, task_id: str, task_data: dict):
        """Add task to queue"""
        await self.queue.put((task_id, task_data))
        self.task_status[task_id] = TaskStatus.PENDING
    
    async def process_queue(self):
        """Process tasks with concurrency limit"""
        while True:
            if len(self.running_tasks) < self.max_concurrent:
                task_id, task_data = await self.queue.get()
                task = asyncio.create_task(self._process_chunking(task_id, task_data))
                self.running_tasks[task_id] = task
```

---

### 3. 语义分块算法选择

#### Decision: 使用句子边界检测 + 余弦相似度的简单语义分块

#### Rationale:
- **符合假设**: Spec 中明确"使用基础的句子边界检测和语义相似度算法，不依赖复杂的NLP模型"
- **性能优先**: 避免大模型推理的时间开销，满足 5秒处理标准文档的目标
- **降级机制**: 当语义边界不明显时，自动降级为按段落分块，保证健壮性

#### Alternatives Considered:
- **Transformer 模型 (BERT/RoBERTa)**: 准确但慢，10k字符文档需要 10-30秒
- **LLM API 调用**: 依赖外部服务，成本高且不可控
- **主题模型 (LDA)**: 适合长文档，但对短文档效果差

#### Implementation Approach:
```python
# 1. 句子边界检测
import re
def split_sentences(text: str) -> List[str]:
    # 中英文句子分隔符
    sentences = re.split(r'[。！？.!?]\s*', text)
    return [s.strip() for s in sentences if s.strip()]

# 2. 简单相似度计算 (使用 TF-IDF + 余弦相似度)
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

def calculate_similarity(sentences: List[str]) -> np.ndarray:
    vectorizer = TfidfVectorizer()
    vectors = vectorizer.fit_transform(sentences)
    similarity_matrix = cosine_similarity(vectors)
    return similarity_matrix

# 3. 语义边界识别
def find_semantic_boundaries(similarity_matrix, threshold=0.3):
    boundaries = []
    for i in range(len(similarity_matrix) - 1):
        if similarity_matrix[i][i+1] < threshold:
            boundaries.append(i+1)
    return boundaries

# 4. 降级条件
def should_fallback_to_paragraph(boundaries, total_sentences):
    # 如果边界过少（< 10%）或过多（> 90%），降级
    boundary_ratio = len(boundaries) / total_sentences
    return boundary_ratio < 0.1 or boundary_ratio > 0.9
```

---

### 4. JSON 数据结构最佳实践

#### Decision: 使用扁平化元信息 + 嵌套 chunks 列表的混合结构

#### Rationale:
- **可读性**: 文档级元信息一目了然
- **可扩展性**: chunks 列表支持任意数量的块
- **向量化友好**: 每个 chunk 包含 content + metadata，直接对应向量嵌入的输入格式
- **符合规范**: 与澄清会话中用户确认的结构完全一致

#### JSON Schema:
```json
{
  "document_id": "string (UUID)",
  "document_name": "string",
  "source_file": "string (path to original load/parse JSON)",
  "total_chunks": "integer",
  "chunking_strategy": "string (character/paragraph/heading/semantic)",
  "chunking_params": {
    "chunk_size": "integer",
    "chunk_overlap": "integer",
    "additional_params": "object"
  },
  "status": "string (completed/partial/failed)",
  "created_at": "string (ISO 8601)",
  "processing_time": "float (seconds)",
  "error_info": {
    "error_position": "integer (character position)",
    "error_message": "string",
    "affected_chunks": "integer"
  },
  "statistics": {
    "avg_chunk_size": "float",
    "max_chunk_size": "integer",
    "min_chunk_size": "integer",
    "total_characters": "integer"
  },
  "chunks": [
    {
      "content": "string",
      "metadata": {
        "chunk_id": "string (UUID)",
        "chunk_index": "integer",
        "char_count": "integer",
        "word_count": "integer",
        "page_number": "integer (optional)",
        "start_position": "integer",
        "end_position": "integer",
        "headings": ["string"] (optional),
        "paragraph_count": "integer",
        "is_fallback": "boolean (for semantic chunking)"
      }
    }
  ]
}
```

---

### 5. 分页和过滤的数据库查询优化

#### Decision: 使用 SQLAlchemy 索引 + LIMIT/OFFSET 分页 + 复合过滤条件

#### Rationale:
- **性能**: 索引加速查询，满足 500 条记录 1 秒响应的目标
- **灵活性**: 支持按多个维度过滤和排序
- **已有基础**: 项目已使用 SQLAlchemy，无需额外学习成本

#### Database Schema:
```python
from sqlalchemy import Column, String, Integer, DateTime, Float, Index
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class ChunkingResultRecord(Base):
    __tablename__ = "chunking_results"
    
    id = Column(String, primary_key=True)  # UUID
    document_id = Column(String, nullable=False, index=True)
    document_name = Column(String, nullable=False, index=True)
    chunking_strategy = Column(String, nullable=False, index=True)
    total_chunks = Column(Integer, nullable=False)
    status = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, index=True)
    processing_time = Column(Float)
    file_path = Column(String, nullable=False)
    file_size = Column(Integer)
    
    # Composite index for common queries
    __table_args__ = (
        Index('idx_doc_strategy_time', 'document_name', 'chunking_strategy', 'created_at'),
    )
```

#### Query Patterns:
```python
from sqlalchemy import desc, asc
from sqlalchemy.orm import Session

def get_chunking_history(
    db: Session,
    page: int = 1,
    per_page: int = 20,
    document_name: str = None,
    strategy: str = None,
    sort_by: str = "created_at",
    sort_order: str = "desc"
):
    query = db.query(ChunkingResultRecord)
    
    # Filters
    if document_name:
        query = query.filter(ChunkingResultRecord.document_name.like(f"%{document_name}%"))
    if strategy:
        query = query.filter(ChunkingResultRecord.chunking_strategy == strategy)
    
    # Sorting
    order_func = desc if sort_order == "desc" else asc
    query = query.order_by(order_func(getattr(ChunkingResultRecord, sort_by)))
    
    # Pagination
    total = query.count()
    results = query.offset((page - 1) * per_page).limit(per_page).all()
    
    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "results": results
    }
```

---

### 6. CSV 导出的大文件处理

#### Decision: 使用流式写入 + 生成器模式

#### Rationale:
- **内存高效**: 避免一次性加载所有数据到内存
- **支持大文件**: 可处理数千个块的导出
- **用户体验**: 支持下载进度显示

#### Implementation:
```python
import csv
from io import StringIO
from fastapi.responses import StreamingResponse

def generate_csv_rows(chunks: List[dict]):
    """Generator for CSV rows"""
    # Header
    yield ["chunk_id", "chunk_index", "document_name", "strategy", 
           "char_count", "word_count", "page_number", "chunk_content"]
    
    # Data rows
    for chunk in chunks:
        yield [
            chunk["metadata"]["chunk_id"],
            chunk["metadata"]["chunk_index"],
            chunk["document_name"],
            chunk["strategy"],
            chunk["metadata"]["char_count"],
            chunk["metadata"]["word_count"],
            chunk["metadata"].get("page_number", ""),
            chunk["content"].replace("\n", "\\n")  # Escape newlines
        ]

async def export_csv(chunking_result_id: str):
    result = load_chunking_result(chunking_result_id)
    
    def iter_csv():
        output = StringIO()
        writer = csv.writer(output)
        for row in generate_csv_rows(result["chunks"]):
            writer.writerow(row)
            yield output.getvalue()
            output.seek(0)
            output.truncate(0)
    
    return StreamingResponse(
        iter_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=chunks_{chunking_result_id}.csv"}
    )
```

---

### 7. 按标题分块的标题检测策略

#### Decision: 支持 Markdown 和 HTML 标题格式，使用正则表达式检测

#### Rationale:
- **通用性**: 覆盖大多数结构化文档格式
- **轻量级**: 无需解析器依赖
- **可扩展**: 可根据需要添加更多格式支持

#### Detection Patterns:
```python
import re
from typing import List, Tuple

class HeadingDetector:
    """Detect headings in text"""
    
    # Markdown headings: # H1, ## H2, ### H3, etc.
    MD_HEADING_PATTERN = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)
    
    # HTML headings: <h1>, <h2>, etc.
    HTML_HEADING_PATTERN = re.compile(r'<h([1-6])>(.*?)</h\1>', re.IGNORECASE)
    
    @staticmethod
    def detect_headings(text: str) -> List[Tuple[int, int, str, int]]:
        """
        Detect headings in text
        Returns: List of (start_pos, end_pos, heading_text, level)
        """
        headings = []
        
        # Markdown headings
        for match in HeadingDetector.MD_HEADING_PATTERN.finditer(text):
            level = len(match.group(1))  # Number of #
            heading_text = match.group(2).strip()
            headings.append((match.start(), match.end(), heading_text, level))
        
        # HTML headings
        for match in HeadingDetector.HTML_HEADING_PATTERN.finditer(text):
            level = int(match.group(1))
            heading_text = match.group(2).strip()
            headings.append((match.start(), match.end(), heading_text, level))
        
        return sorted(headings, key=lambda x: x[0])  # Sort by position
    
    @staticmethod
    def has_heading_structure(text: str, min_headings: int = 2) -> bool:
        """Check if document has sufficient heading structure"""
        headings = HeadingDetector.detect_headings(text)
        return len(headings) >= min_headings
```

---

## Summary

所有关键技术决策已完成研究和评估：

1. ✅ **分块引擎**: LangChain TextSplitters (已安装，成熟稳定)
2. ✅ **并发管理**: asyncio Queue + 自定义队列管理器 (轻量级，可控性强)
3. ✅ **语义分块**: 句子边界 + TF-IDF 余弦相似度 (符合性能要求)
4. ✅ **数据结构**: 混合结构 JSON (符合规范，向量化友好)
5. ✅ **分页查询**: SQLAlchemy 索引 + 复合过滤 (满足性能目标)
6. ✅ **CSV 导出**: 流式写入 + 生成器模式 (内存高效)
7. ✅ **标题检测**: 正则表达式检测 Markdown/HTML (通用，轻量级)

所有技术选型符合 Constitution 原则，无额外依赖需求，可直接进入 Phase 1 设计阶段。
