"""Chunk metadata models for multimodal chunking support."""
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from enum import Enum


class ChunkTypeEnum(str, Enum):
    """Chunk type enumeration."""
    TEXT = "text"
    TABLE = "table"
    IMAGE = "image"
    CODE = "code"


@dataclass
class BaseChunkMetadata:
    """Base metadata for all chunk types."""
    chunk_id: str
    chunk_index: int
    char_count: int
    word_count: int
    start_position: int
    end_position: int
    chunk_type: str = "text"
    parent_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class TextChunkMetadata(BaseChunkMetadata):
    """Metadata for text chunks."""
    chunk_type: str = "text"
    page_number: Optional[int] = None
    heading_path: List[str] = field(default_factory=list)
    paragraph_index: Optional[int] = None
    is_title: bool = False
    language: Optional[str] = None


@dataclass
class TableChunkMetadata(BaseChunkMetadata):
    """Metadata for table chunks."""
    chunk_type: str = "table"
    table_index: int = 0
    page_number: Optional[int] = None
    sheet_name: Optional[str] = None  # Sheet name for Excel files
    bbox: Optional[List[float]] = None  # [x1, y1, x2, y2]
    row_count: int = 0
    column_count: int = 0
    headers: Optional[List[str]] = None  # Table column headers
    table_title: Optional[str] = None
    has_header: bool = True
    table_markdown: Optional[str] = None  # Full Markdown representation
    context_before: Optional[str] = None  # Text context before table
    context_after: Optional[str] = None  # Text context after table
    section_title: Optional[str] = None  # Section/heading title the table belongs to


@dataclass
class ImageChunkMetadata(BaseChunkMetadata):
    """Metadata for image chunks."""
    chunk_type: str = "image"
    image_index: int = 0
    page_number: Optional[int] = None
    bbox: Optional[List[float]] = None  # [x1, y1, x2, y2]
    image_path: Optional[str] = None
    image_base64: Optional[str] = None  # Base64 encoded image for vector embedding
    thumbnail_base64: Optional[str] = None  # Thumbnail for quick preview
    caption: Optional[str] = None
    alt_text: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    original_size: Optional[int] = None  # Original file size in bytes
    format: Optional[str] = None  # png, jpg, etc.
    mime_type: Optional[str] = None  # MIME type like image/png
    context_before: Optional[str] = None  # Text context before image
    context_after: Optional[str] = None  # Text context after image


@dataclass
class CodeChunkMetadata(BaseChunkMetadata):
    """Metadata for code chunks."""
    chunk_type: str = "code"
    language: Optional[str] = None
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    file_reference: Optional[str] = None
    function_name: Optional[str] = None
    class_name: Optional[str] = None
    is_complete_block: bool = True
    context_before: Optional[str] = None  # Text context before code block
    context_after: Optional[str] = None  # Text context after code block
    section_title: Optional[str] = None  # Section/heading title the code belongs to


def create_chunk_metadata(
    chunk_type: str,
    chunk_id: str,
    chunk_index: int,
    content: str,
    start_position: int,
    end_position: int,
    **kwargs
) -> Dict[str, Any]:
    """
    Factory function to create appropriate chunk metadata based on type.
    
    Args:
        chunk_type: Type of chunk (text, table, image, code)
        chunk_id: Unique chunk identifier
        chunk_index: Chunk sequence number
        content: Chunk content
        start_position: Start position in source
        end_position: End position in source
        **kwargs: Additional type-specific metadata
    
    Returns:
        Dictionary containing chunk metadata
    """
    base_params = {
        "chunk_id": chunk_id,
        "chunk_index": chunk_index,
        "char_count": len(content),
        "word_count": len(content.split()),
        "start_position": start_position,
        "end_position": end_position,
    }
    
    if chunk_type == ChunkTypeEnum.TABLE.value:
        metadata = TableChunkMetadata(**base_params, **kwargs)
    elif chunk_type == ChunkTypeEnum.IMAGE.value:
        metadata = ImageChunkMetadata(**base_params, **kwargs)
    elif chunk_type == ChunkTypeEnum.CODE.value:
        metadata = CodeChunkMetadata(**base_params, **kwargs)
    else:
        metadata = TextChunkMetadata(**base_params, **kwargs)
    
    return metadata.to_dict()


def validate_multimodal_metadata(chunk_type: str, metadata: Dict[str, Any]) -> List[str]:
    """
    Validate that multimodal chunk metadata contains required fields.
    
    Args:
        chunk_type: Type of chunk
        metadata: Metadata dictionary to validate
    
    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []
    
    # Common required fields
    required_common = ["chunk_id", "chunk_index", "start_position", "end_position"]
    for field in required_common:
        if field not in metadata:
            errors.append(f"Missing required field: {field}")
    
    # Type-specific validation
    if chunk_type == ChunkTypeEnum.TABLE.value:
        if "row_count" not in metadata:
            errors.append("Table chunk missing row_count")
        if "column_count" not in metadata:
            errors.append("Table chunk missing column_count")
    
    elif chunk_type == ChunkTypeEnum.IMAGE.value:
        # Image chunks should have either image_path or image_base64 for vectorization
        if not metadata.get("image_path") and not metadata.get("image_base64"):
            errors.append("Image chunk should have image_path or image_base64")
    
    elif chunk_type == ChunkTypeEnum.CODE.value:
        if "language" not in metadata:
            errors.append("Code chunk missing language")
    
    return errors


# JSON Schema definitions for API documentation
TEXT_CHUNK_SCHEMA = {
    "type": "object",
    "properties": {
        "chunk_id": {"type": "string", "format": "uuid"},
        "chunk_index": {"type": "integer"},
        "char_count": {"type": "integer"},
        "word_count": {"type": "integer"},
        "start_position": {"type": "integer"},
        "end_position": {"type": "integer"},
        "chunk_type": {"type": "string", "enum": ["text"]},
        "page_number": {"type": "integer"},
        "heading_path": {"type": "array", "items": {"type": "string"}},
        "parent_id": {"type": "string", "format": "uuid"}
    },
    "required": ["chunk_id", "chunk_index", "start_position", "end_position"]
}

TABLE_CHUNK_SCHEMA = {
    "type": "object",
    "properties": {
        "chunk_id": {"type": "string", "format": "uuid"},
        "chunk_index": {"type": "integer"},
        "char_count": {"type": "integer"},
        "word_count": {"type": "integer"},
        "start_position": {"type": "integer"},
        "end_position": {"type": "integer"},
        "chunk_type": {"type": "string", "enum": ["table"]},
        "table_index": {"type": "integer"},
        "page_number": {"type": "integer"},
        "sheet_name": {"type": "string"},  # Sheet name for Excel files
        "bbox": {"type": "array", "items": {"type": "number"}, "minItems": 4, "maxItems": 4},
        "row_count": {"type": "integer"},
        "column_count": {"type": "integer"},
        "headers": {"type": "array", "items": {"type": "string"}},  # Table column headers
        "table_title": {"type": "string"},
        "has_header": {"type": "boolean"},
        "table_markdown": {"type": "string"}
    },
    "required": ["chunk_id", "chunk_index", "row_count", "column_count"]
}

IMAGE_CHUNK_SCHEMA = {
    "type": "object",
    "properties": {
        "chunk_id": {"type": "string", "format": "uuid"},
        "chunk_index": {"type": "integer"},
        "char_count": {"type": "integer"},
        "word_count": {"type": "integer"},
        "start_position": {"type": "integer"},
        "end_position": {"type": "integer"},
        "chunk_type": {"type": "string", "enum": ["image"]},
        "image_index": {"type": "integer"},
        "page_number": {"type": "integer"},
        "bbox": {"type": "array", "items": {"type": "number"}, "minItems": 4, "maxItems": 4},
        "image_path": {"type": "string"},
        "image_base64": {"type": "string"},
        "thumbnail_base64": {"type": "string"},
        "caption": {"type": "string"},
        "alt_text": {"type": "string"},
        "width": {"type": "integer"},
        "height": {"type": "integer"},
        "original_size": {"type": "integer"},
        "format": {"type": "string"},
        "mime_type": {"type": "string"},
        "context_before": {"type": "string"},
        "context_after": {"type": "string"}
    },
    "required": ["chunk_id", "chunk_index"]
}

CODE_CHUNK_SCHEMA = {
    "type": "object",
    "properties": {
        "chunk_id": {"type": "string", "format": "uuid"},
        "chunk_index": {"type": "integer"},
        "char_count": {"type": "integer"},
        "word_count": {"type": "integer"},
        "start_position": {"type": "integer"},
        "end_position": {"type": "integer"},
        "chunk_type": {"type": "string", "enum": ["code"]},
        "language": {"type": "string"},
        "start_line": {"type": "integer"},
        "end_line": {"type": "integer"},
        "file_reference": {"type": "string"},
        "function_name": {"type": "string"},
        "class_name": {"type": "string"},
        "is_complete_block": {"type": "boolean"}
    },
    "required": ["chunk_id", "chunk_index", "language"]
}
