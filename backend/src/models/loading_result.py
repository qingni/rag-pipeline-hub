"""Unified document loading result models.

This module defines the standardized data structures for document parsing results,
ensuring compatibility across all loaders and downstream processing modules.
"""
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
import json


class ExtractionQuality(str, Enum):
    """Extraction quality levels."""
    HIGH = "high"       # 0.9-1.0 - Docling successful parsing
    MEDIUM = "medium"   # 0.7-0.9 - Standard parsers
    LOW = "low"         # 0.5-0.7 - Fallback parsers
    MINIMAL = "minimal" # < 0.5 - Basic text extraction only


@dataclass
class PageContent:
    """Single page content."""
    page_number: int
    text: str
    char_count: int
    
    # Optional structured content
    paragraphs: List[str] = field(default_factory=list)
    headings: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class TableContent:
    """Table content (Docling specific)."""
    page_number: int
    table_index: int
    headers: List[str]
    rows: List[List[str]]
    caption: Optional[str] = None
    
    # Table metadata
    row_count: int = 0
    col_count: int = 0
    
    def __post_init__(self):
        """Calculate row and column counts."""
        if not self.row_count:
            self.row_count = len(self.rows)
        if not self.col_count:
            self.col_count = len(self.headers) if self.headers else 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class ImageContent:
    """Image content for multimodal processing.
    
    支持多模态嵌入模型 (如 qwen3-vl-embedding-8b) 的图片数据结构。
    可以存储图片的多种表示形式：文件路径、Base64 数据、描述文本等。
    """
    page_number: int
    image_index: int
    caption: Optional[str] = None
    alt_text: Optional[str] = None
    
    # Image position (optional)
    bbox: Optional[Dict[str, float]] = None
    
    # ========== 多模态支持字段 ==========
    
    # 图片文件路径 (相对于项目根目录)
    file_path: Optional[str] = None
    
    # 图片 Base64 编码 (用于直接传递给多模态模型)
    base64_data: Optional[str] = None
    
    # 图片 MIME 类型 (image/png, image/jpeg 等)
    mime_type: Optional[str] = None
    
    # 图片尺寸
    width: Optional[int] = None
    height: Optional[int] = None
    
    # 图片在文档中的上下文位置 (前后文本片段)
    context_before: Optional[str] = None  # 图片前的文本 (用于关联)
    context_after: Optional[str] = None   # 图片后的文本 (用于关联)
    
    # 图片类型标签
    image_type: Optional[str] = None  # figure, chart, diagram, photo, screenshot 等
    
    # OCR 识别的图片内文字
    ocr_text: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    def has_visual_data(self) -> bool:
        """检查是否有可用于多模态处理的视觉数据"""
        return bool(self.file_path or self.base64_data)
    
    def get_text_representation(self) -> str:
        """获取图片的纯文本表示 (用于传统文本嵌入)"""
        parts = []
        if self.caption:
            parts.append(f"[图片标题: {self.caption}]")
        if self.alt_text:
            parts.append(f"[图片描述: {self.alt_text}]")
        if self.ocr_text:
            parts.append(f"[图片文字: {self.ocr_text}]")
        if self.image_type:
            parts.append(f"[图片类型: {self.image_type}]")
        
        return " ".join(parts) if parts else "[图片]"


@dataclass
class FormulaContent:
    """Formula content (Docling specific)."""
    page_number: int
    formula_index: int
    latex: str
    text_representation: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class DocumentMetadata:
    """Document metadata."""
    title: Optional[str] = None
    author: Optional[str] = None
    page_count: int = 0
    file_size: int = 0
    format: str = ""
    created_time: Optional[str] = None
    modified_time: Optional[str] = None
    
    # Extraction quality metrics
    extraction_quality: float = 0.0  # 0.0-1.0
    quality_level: ExtractionQuality = ExtractionQuality.MEDIUM
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = asdict(self)
        result['quality_level'] = self.quality_level.value
        return result


@dataclass
class DocumentContent:
    """Document content."""
    full_text: str
    pages: List[PageContent] = field(default_factory=list)
    
    # Docling-specific structured content
    tables: List[TableContent] = field(default_factory=list)
    images: List[ImageContent] = field(default_factory=list)
    formulas: List[FormulaContent] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'full_text': self.full_text,
            'pages': [p.to_dict() for p in self.pages],
            'tables': [t.to_dict() for t in self.tables],
            'images': [i.to_dict() for i in self.images],
            'formulas': [f.to_dict() for f in self.formulas]
        }


@dataclass
class ProcessingStatistics:
    """Processing statistics."""
    total_pages: int = 0
    total_chars: int = 0
    processing_time: float = 0.0  # seconds
    
    # Fallback information
    fallback_used: bool = False
    fallback_reason: Optional[str] = None
    original_parser: Optional[str] = None
    
    # Detailed statistics
    table_count: int = 0
    image_count: int = 0
    formula_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class StandardDocumentResult:
    """Unified document parsing result."""
    success: bool
    loader: str  # Actual parser name used
    
    metadata: DocumentMetadata = field(default_factory=DocumentMetadata)
    content: DocumentContent = field(default_factory=lambda: DocumentContent(full_text=""))
    statistics: ProcessingStatistics = field(default_factory=ProcessingStatistics)
    
    # Error information (only when success=False)
    error: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'success': self.success,
            'loader': self.loader,
            'metadata': self.metadata.to_dict(),
            'content': self.content.to_dict(),
            'statistics': self.statistics.to_dict(),
            'error': self.error,
            'error_details': self.error_details
        }
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StandardDocumentResult':
        """Create instance from dictionary."""
        # Parse metadata
        metadata_data = data.get('metadata', {})
        quality_level = metadata_data.get('quality_level', 'medium')
        if isinstance(quality_level, str):
            quality_level = ExtractionQuality(quality_level)
        metadata = DocumentMetadata(
            title=metadata_data.get('title'),
            author=metadata_data.get('author'),
            page_count=metadata_data.get('page_count', 0),
            file_size=metadata_data.get('file_size', 0),
            format=metadata_data.get('format', ''),
            created_time=metadata_data.get('created_time'),
            modified_time=metadata_data.get('modified_time'),
            extraction_quality=metadata_data.get('extraction_quality', 0.0),
            quality_level=quality_level
        )
        
        # Parse content
        content_data = data.get('content', {})
        pages = [
            PageContent(
                page_number=p.get('page_number', 0),
                text=p.get('text', ''),
                char_count=p.get('char_count', 0),
                paragraphs=p.get('paragraphs', []),
                headings=p.get('headings', [])
            )
            for p in content_data.get('pages', [])
        ]
        tables = [
            TableContent(
                page_number=t.get('page_number', 0),
                table_index=t.get('table_index', 0),
                headers=t.get('headers', []),
                rows=t.get('rows', []),
                caption=t.get('caption'),
                row_count=t.get('row_count', 0),
                col_count=t.get('col_count', 0)
            )
            for t in content_data.get('tables', [])
        ]
        images = [
            ImageContent(
                page_number=i.get('page_number', 0),
                image_index=i.get('image_index', 0),
                caption=i.get('caption'),
                alt_text=i.get('alt_text'),
                bbox=i.get('bbox'),
                # 多模态支持字段
                file_path=i.get('file_path'),
                base64_data=i.get('base64_data'),
                mime_type=i.get('mime_type'),
                width=i.get('width'),
                height=i.get('height'),
                context_before=i.get('context_before'),
                context_after=i.get('context_after'),
                image_type=i.get('image_type'),
                ocr_text=i.get('ocr_text')
            )
            for i in content_data.get('images', [])
        ]
        formulas = [
            FormulaContent(
                page_number=f.get('page_number', 0),
                formula_index=f.get('formula_index', 0),
                latex=f.get('latex', ''),
                text_representation=f.get('text_representation')
            )
            for f in content_data.get('formulas', [])
        ]
        content = DocumentContent(
            full_text=content_data.get('full_text', ''),
            pages=pages,
            tables=tables,
            images=images,
            formulas=formulas
        )
        
        # Parse statistics
        stats_data = data.get('statistics', {})
        statistics = ProcessingStatistics(
            total_pages=stats_data.get('total_pages', 0),
            total_chars=stats_data.get('total_chars', 0),
            processing_time=stats_data.get('processing_time', 0.0),
            fallback_used=stats_data.get('fallback_used', False),
            fallback_reason=stats_data.get('fallback_reason'),
            original_parser=stats_data.get('original_parser'),
            table_count=stats_data.get('table_count', 0),
            image_count=stats_data.get('image_count', 0),
            formula_count=stats_data.get('formula_count', 0)
        )
        
        return cls(
            success=data.get('success', False),
            loader=data.get('loader', ''),
            metadata=metadata,
            content=content,
            statistics=statistics,
            error=data.get('error'),
            error_details=data.get('error_details')
        )
    
    @classmethod
    def create_error(
        cls,
        loader: str,
        error: str,
        error_details: Optional[Dict[str, Any]] = None
    ) -> 'StandardDocumentResult':
        """Create an error result."""
        return cls(
            success=False,
            loader=loader,
            error=error,
            error_details=error_details
        )
