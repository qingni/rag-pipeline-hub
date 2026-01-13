# Data Model: 文档处理模块优化

**Feature**: 001-document-processing-opt  
**Date**: 2025-01-13

## 1. 核心实体

### 1.1 StandardDocumentResult (统一文档解析结果)

**描述**: 所有解析器输出的统一数据结构，确保下游处理模块的兼容性。

```python
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class ExtractionQuality(Enum):
    """解析质量等级"""
    HIGH = "high"       # 0.9-1.0 - Docling 成功解析
    MEDIUM = "medium"   # 0.7-0.9 - 标准解析器
    LOW = "low"         # 0.5-0.7 - 降级解析器
    MINIMAL = "minimal" # < 0.5 - 仅提取基础文本


@dataclass
class PageContent:
    """单页内容"""
    page_number: int
    text: str
    char_count: int
    
    # 可选的结构化内容
    paragraphs: List[str] = field(default_factory=list)
    headings: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class TableContent:
    """表格内容 (Docling 特有)"""
    page_number: int
    table_index: int
    headers: List[str]
    rows: List[List[str]]
    caption: Optional[str] = None
    
    # 表格元数据
    row_count: int = 0
    col_count: int = 0


@dataclass
class ImageContent:
    """图像内容 (Docling 特有)"""
    page_number: int
    image_index: int
    caption: Optional[str] = None
    alt_text: Optional[str] = None
    
    # 图像位置 (可选)
    bbox: Optional[Dict[str, float]] = None


@dataclass
class FormulaContent:
    """公式内容 (Docling 特有)"""
    page_number: int
    formula_index: int
    latex: str
    text_representation: Optional[str] = None


@dataclass
class DocumentMetadata:
    """文档元数据"""
    title: Optional[str] = None
    author: Optional[str] = None
    page_count: int = 0
    file_size: int = 0
    format: str = ""
    created_time: Optional[datetime] = None
    modified_time: Optional[datetime] = None
    
    # 解析质量指标
    extraction_quality: float = 0.0  # 0.0-1.0
    quality_level: ExtractionQuality = ExtractionQuality.MEDIUM


@dataclass
class DocumentContent:
    """文档内容"""
    full_text: str
    pages: List[PageContent] = field(default_factory=list)
    
    # Docling 特有的结构化内容
    tables: List[TableContent] = field(default_factory=list)
    images: List[ImageContent] = field(default_factory=list)
    formulas: List[FormulaContent] = field(default_factory=list)


@dataclass
class ProcessingStatistics:
    """处理统计信息"""
    total_pages: int = 0
    total_chars: int = 0
    processing_time: float = 0.0  # 秒
    
    # 降级信息
    fallback_used: bool = False
    fallback_reason: Optional[str] = None
    original_parser: Optional[str] = None
    
    # 详细统计
    table_count: int = 0
    image_count: int = 0
    formula_count: int = 0


@dataclass
class StandardDocumentResult:
    """统一文档解析结果"""
    success: bool
    loader: str  # 实际使用的解析器名称
    
    metadata: DocumentMetadata
    content: DocumentContent
    statistics: ProcessingStatistics
    
    # 错误信息 (仅在 success=False 时)
    error: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
```

### 1.2 LoaderConfig (加载器配置)

**描述**: 加载器的配置信息，用于智能选择和降级策略。

```python
@dataclass
class LoaderConfig:
    """加载器配置"""
    name: str
    display_name: str
    supported_formats: List[str]
    priority: int  # 优先级，数字越小优先级越高
    
    # 性能特征
    avg_speed: str  # "fast", "medium", "slow"
    quality_level: ExtractionQuality
    
    # 依赖信息
    requires_installation: bool = False
    installation_command: Optional[str] = None
    
    # 能力标记
    supports_tables: bool = False
    supports_images: bool = False
    supports_formulas: bool = False
    supports_ocr: bool = False
```

### 1.3 FormatStrategy (格式策略)

**描述**: 每种文件格式的解析策略配置。

```python
@dataclass
class FormatStrategy:
    """格式解析策略"""
    format: str
    primary_loader: str
    fallback_loaders: List[str]
    
    # 智能选择阈值
    size_threshold_mb: float = 20.0  # 超过此大小使用快速解析器
    fast_loader: Optional[str] = None  # 大文件使用的快速解析器
```

---

## 2. 配置数据

### 2.1 加载器注册表

```python
LOADER_REGISTRY: Dict[str, LoaderConfig] = {
    "docling": LoaderConfig(
        name="docling",
        display_name="Docling (IBM)",
        supported_formats=["pdf", "docx", "xlsx", "pptx", "html"],
        priority=1,
        avg_speed="slow",
        quality_level=ExtractionQuality.HIGH,
        requires_installation=True,
        installation_command="pip install docling",
        supports_tables=True,
        supports_images=True,
        supports_formulas=True,
        supports_ocr=True,
    ),
    "pymupdf": LoaderConfig(
        name="pymupdf",
        display_name="PyMuPDF",
        supported_formats=["pdf"],
        priority=2,
        avg_speed="fast",
        quality_level=ExtractionQuality.MEDIUM,
        supports_images=True,
    ),
    "docx": LoaderConfig(
        name="docx",
        display_name="python-docx",
        supported_formats=["docx"],
        priority=2,
        avg_speed="fast",
        quality_level=ExtractionQuality.MEDIUM,
    ),
    "xlsx": LoaderConfig(
        name="xlsx",
        display_name="openpyxl",
        supported_formats=["xlsx"],
        priority=2,
        avg_speed="fast",
        quality_level=ExtractionQuality.MEDIUM,
        supports_tables=True,
    ),
    "pptx": LoaderConfig(
        name="pptx",
        display_name="python-pptx",
        supported_formats=["pptx"],
        priority=2,
        avg_speed="fast",
        quality_level=ExtractionQuality.MEDIUM,
    ),
    "unstructured": LoaderConfig(
        name="unstructured",
        display_name="Unstructured",
        supported_formats=["pdf", "docx", "xlsx", "pptx", "html", "epub", "eml", "msg"],
        priority=10,  # 作为通用降级
        avg_speed="slow",
        quality_level=ExtractionQuality.MEDIUM,
        requires_installation=True,
        installation_command='pip install "unstructured[all-docs]"',
    ),
    # ... 其他加载器
}
```

### 2.2 格式策略映射

```python
FORMAT_STRATEGIES: Dict[str, FormatStrategy] = {
    "pdf": FormatStrategy(
        format="pdf",
        primary_loader="docling",
        fallback_loaders=["pymupdf", "unstructured"],
        size_threshold_mb=20.0,
        fast_loader="pymupdf",
    ),
    "docx": FormatStrategy(
        format="docx",
        primary_loader="docling",
        fallback_loaders=["docx", "unstructured"],
    ),
    "xlsx": FormatStrategy(
        format="xlsx",
        primary_loader="docling",
        fallback_loaders=["xlsx", "pandas", "unstructured"],
    ),
    "pptx": FormatStrategy(
        format="pptx",
        primary_loader="docling",
        fallback_loaders=["pptx", "unstructured"],
    ),
    "html": FormatStrategy(
        format="html",
        primary_loader="html",
        fallback_loaders=["unstructured"],
    ),
    "csv": FormatStrategy(
        format="csv",
        primary_loader="csv",
        fallback_loaders=["pandas"],
    ),
    "txt": FormatStrategy(
        format="txt",
        primary_loader="text",
        fallback_loaders=[],
    ),
    "md": FormatStrategy(
        format="md",
        primary_loader="text",
        fallback_loaders=[],
    ),
    # ... 其他格式
}
```

---

## 3. 关系图

```
┌─────────────────────────────────────────────────────────────────┐
│                    StandardDocumentResult                        │
├─────────────────────────────────────────────────────────────────┤
│  success: bool                                                   │
│  loader: str                                                     │
│  error: Optional[str]                                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────────┐ │
│  │ DocumentMetadata │  │ DocumentContent │  │ProcessingStats   │ │
│  ├─────────────────┤  ├─────────────────┤  ├──────────────────┤ │
│  │ title           │  │ full_text       │  │ total_pages      │ │
│  │ author          │  │ pages[]         │  │ total_chars      │ │
│  │ page_count      │  │ tables[]        │  │ processing_time  │ │
│  │ file_size       │  │ images[]        │  │ fallback_used    │ │
│  │ format          │  │ formulas[]      │  │ fallback_reason  │ │
│  │ extraction_quality│ │                 │  │                  │ │
│  └─────────────────┘  └─────────────────┘  └──────────────────┘ │
│                              │                                   │
│              ┌───────────────┼───────────────┐                  │
│              ▼               ▼               ▼                  │
│     ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│     │ PageContent │  │TableContent │  │ImageContent │          │
│     ├─────────────┤  ├─────────────┤  ├─────────────┤          │
│     │ page_number │  │ headers[]   │  │ page_number │          │
│     │ text        │  │ rows[][]    │  │ caption     │          │
│     │ char_count  │  │ caption     │  │ alt_text    │          │
│     │ paragraphs[]│  │ row_count   │  │ bbox        │          │
│     │ headings[]  │  │ col_count   │  │             │          │
│     └─────────────┘  └─────────────┘  └─────────────┘          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. 验证规则

### 4.1 StandardDocumentResult 验证

| 字段 | 验证规则 |
|------|----------|
| `success` | 必填，布尔值 |
| `loader` | 必填，必须是已注册的加载器名称 |
| `metadata.page_count` | >= 0 |
| `metadata.file_size` | >= 0 |
| `metadata.extraction_quality` | 0.0 - 1.0 |
| `content.full_text` | success=True 时必须非空 |
| `statistics.total_pages` | >= 0，与 pages 列表长度一致 |
| `statistics.processing_time` | >= 0 |

### 4.2 PageContent 验证

| 字段 | 验证规则 |
|------|----------|
| `page_number` | >= 1 |
| `text` | 可为空字符串 |
| `char_count` | >= 0，与 text 长度一致 |

### 4.3 TableContent 验证

| 字段 | 验证规则 |
|------|----------|
| `page_number` | >= 1 |
| `table_index` | >= 0 |
| `headers` | 列表，可为空 |
| `rows` | 二维列表，每行列数应与 headers 一致 |
| `row_count` | 与 rows 长度一致 |
| `col_count` | 与 headers 长度一致 |

---

## 5. 状态转换

### 5.1 文档处理状态

```
┌──────────┐     上传成功      ┌──────────┐
│ uploaded │ ─────────────────▶│  ready   │
└──────────┘                   └──────────┘
                                    │
                               开始加载
                                    ▼
                              ┌──────────┐
                              │processing│
                              └──────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
              ┌──────────┐                    ┌──────────┐
              │ completed│                    │  error   │
              └──────────┘                    └──────────┘
                    │                               │
                    │         重试                  │
                    │◀──────────────────────────────┘
```

### 5.2 解析器降级流程

```
┌─────────────────┐
│ 选择主解析器    │
│ (e.g., docling) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     成功     ┌─────────────────┐
│   执行解析      │─────────────▶│   返回结果      │
└────────┬────────┘              │ fallback=false  │
         │                       └─────────────────┘
         │ 失败
         ▼
┌─────────────────┐
│ 选择下一个      │
│ 降级解析器      │
└────────┬────────┘
         │
         ▼
    ┌────────────┐     是      ┌─────────────────┐
    │ 还有降级?  │────────────▶│   执行解析      │──┐
    └────────────┘             └─────────────────┘  │
         │ 否                          │            │
         ▼                             │ 成功       │ 失败
┌─────────────────┐              ┌─────▼─────┐     │
│   返回错误      │              │ 返回结果  │     │
│ success=false   │              │fallback=  │◀────┘
└─────────────────┘              │  true     │
                                 └───────────┘
```

---

## 6. JSON 序列化示例

### 6.1 成功响应 (无降级)

```json
{
  "success": true,
  "loader": "docling",
  "metadata": {
    "title": "技术文档",
    "author": "张三",
    "page_count": 10,
    "file_size": 1048576,
    "format": "pdf",
    "created_time": "2025-01-13T10:00:00Z",
    "extraction_quality": 0.95,
    "quality_level": "high"
  },
  "content": {
    "full_text": "文档全文内容...",
    "pages": [
      {
        "page_number": 1,
        "text": "第一页内容...",
        "char_count": 500,
        "paragraphs": ["段落1", "段落2"],
        "headings": [{"level": 1, "text": "标题"}]
      }
    ],
    "tables": [
      {
        "page_number": 2,
        "table_index": 0,
        "headers": ["列1", "列2", "列3"],
        "rows": [["A", "B", "C"], ["D", "E", "F"]],
        "caption": "表格1",
        "row_count": 2,
        "col_count": 3
      }
    ],
    "images": [],
    "formulas": []
  },
  "statistics": {
    "total_pages": 10,
    "total_chars": 5000,
    "processing_time": 3.5,
    "fallback_used": false,
    "fallback_reason": null,
    "original_parser": null,
    "table_count": 1,
    "image_count": 0,
    "formula_count": 0
  },
  "error": null,
  "error_details": null
}
```

### 6.2 成功响应 (有降级)

```json
{
  "success": true,
  "loader": "pymupdf",
  "metadata": {
    "extraction_quality": 0.75,
    "quality_level": "medium"
  },
  "statistics": {
    "fallback_used": true,
    "fallback_reason": "Docling 解析失败: OCR 模块不可用",
    "original_parser": "docling"
  }
}
```

### 6.3 失败响应

```json
{
  "success": false,
  "loader": "unstructured",
  "error": "所有解析器均失败",
  "error_details": {
    "attempted_parsers": ["docling", "pymupdf", "unstructured"],
    "errors": {
      "docling": "OCR 模块不可用",
      "pymupdf": "文件损坏",
      "unstructured": "不支持的文件格式"
    }
  }
}
```
