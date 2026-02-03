"""
Multimodal content processor for embedding.

Handles:
- Image chunks: Generate captions, prepare for multimodal embedding
- Table chunks: Convert to structured text
- Mixed content: Split and process separately
"""
import base64
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


class ChunkType(str, Enum):
    """Content chunk types."""
    TEXT = "text"
    IMAGE = "image"
    TABLE = "table"
    CODE = "code"
    MIXED = "mixed"


@dataclass
class ProcessedChunk:
    """Processed chunk ready for embedding."""
    chunk_id: str
    original_content: str
    processed_content: str  # Text representation for embedding
    chunk_type: ChunkType
    requires_multimodal: bool = False
    image_data: Optional[str] = None  # Base64 encoded image
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "chunk_id": self.chunk_id,
            "original_content": self.original_content[:100] + "..." if len(self.original_content) > 100 else self.original_content,
            "processed_content": self.processed_content[:100] + "..." if len(self.processed_content) > 100 else self.processed_content,
            "chunk_type": self.chunk_type.value,
            "requires_multimodal": self.requires_multimodal,
            "has_image_data": self.image_data is not None,
            "metadata": self.metadata,
        }


@dataclass
class MultimodalProcessingResult:
    """Result of multimodal processing."""
    text_chunks: List[ProcessedChunk] = field(default_factory=list)
    multimodal_chunks: List[ProcessedChunk] = field(default_factory=list)
    total_chunks: int = 0
    multimodal_ratio: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "text_chunk_count": len(self.text_chunks),
            "multimodal_chunk_count": len(self.multimodal_chunks),
            "total_chunks": self.total_chunks,
            "multimodal_ratio": self.multimodal_ratio,
        }


class MultimodalProcessor:
    """
    Processor for multimodal content.
    
    Prepares chunks for embedding by:
    - Converting images to text descriptions (for text-only models)
    - Preparing image data for multimodal models
    - Converting tables to structured text
    """
    
    def __init__(self, use_multimodal_model: bool = False):
        """
        Initialize processor.
        
        Args:
            use_multimodal_model: Whether to prepare for multimodal model
        """
        self.use_multimodal_model = use_multimodal_model
    
    def process_chunks(
        self,
        chunks: List[Dict[str, Any]],
    ) -> MultimodalProcessingResult:
        """
        Process all chunks for embedding.
        
        Args:
            chunks: List of chunk dicts with 'id', 'content', 'chunk_type', 'metadata'
            
        Returns:
            MultimodalProcessingResult with processed chunks
        """
        text_chunks = []
        multimodal_chunks = []
        
        for chunk in chunks:
            processed = self.process_chunk(chunk)
            
            if processed.requires_multimodal:
                multimodal_chunks.append(processed)
            else:
                text_chunks.append(processed)
        
        total = len(chunks)
        multimodal_ratio = len(multimodal_chunks) / total if total > 0 else 0.0
        
        return MultimodalProcessingResult(
            text_chunks=text_chunks,
            multimodal_chunks=multimodal_chunks,
            total_chunks=total,
            multimodal_ratio=multimodal_ratio,
        )
    
    def process_chunk(self, chunk: Dict[str, Any]) -> ProcessedChunk:
        """
        Process a single chunk.
        
        Args:
            chunk: Chunk dict with 'id', 'content', 'chunk_type', 'metadata'
            
        Returns:
            ProcessedChunk ready for embedding
        """
        chunk_id = chunk.get('id', chunk.get('chunk_id', ''))
        content = chunk.get('content', '')
        chunk_type_str = chunk.get('chunk_type', 'text')
        metadata = chunk.get('metadata', {})
        
        try:
            chunk_type = ChunkType(chunk_type_str)
        except ValueError:
            chunk_type = ChunkType.TEXT
        
        # Process based on type
        if chunk_type == ChunkType.IMAGE:
            return self._process_image_chunk(chunk_id, content, metadata)
        elif chunk_type == ChunkType.TABLE:
            return self._process_table_chunk(chunk_id, content, metadata)
        elif chunk_type == ChunkType.CODE:
            return self._process_code_chunk(chunk_id, content, metadata)
        else:
            return self._process_text_chunk(chunk_id, content, metadata)
    
    def _process_text_chunk(
        self,
        chunk_id: str,
        content: str,
        metadata: Dict[str, Any],
    ) -> ProcessedChunk:
        """Process plain text chunk."""
        return ProcessedChunk(
            chunk_id=chunk_id,
            original_content=content,
            processed_content=content,
            chunk_type=ChunkType.TEXT,
            requires_multimodal=False,
            metadata=metadata,
        )
    
    def _process_image_chunk(
        self,
        chunk_id: str,
        content: str,
        metadata: Dict[str, Any],
    ) -> ProcessedChunk:
        """
        Process image chunk.
        
        For text-only models: Use caption as content
        For multimodal models: Keep image data for direct embedding
        """
        # Extract caption if available
        caption = metadata.get('caption', '')
        alt_text = metadata.get('alt_text', '')
        ocr_text = metadata.get('ocr_text', '')
        
        # Build text representation
        text_parts = []
        if caption:
            text_parts.append(f"图片描述: {caption}")
        if alt_text and alt_text != caption:
            text_parts.append(f"图片说明: {alt_text}")
        if ocr_text:
            text_parts.append(f"图片文字: {ocr_text}")
        
        if not text_parts:
            text_parts.append("[图片内容]")
        
        processed_content = "\n".join(text_parts)
        
        # Prepare image data for multimodal model
        image_data = None
        requires_multimodal = False
        
        if self.use_multimodal_model:
            # Check if content is base64 image data
            if self._is_base64_image(content):
                image_data = content
                requires_multimodal = True
            elif metadata.get('image_base64'):
                image_data = metadata.get('image_base64')
                requires_multimodal = True
            elif metadata.get('image_path'):
                # Could load from path, but we'll just use text
                pass
        
        return ProcessedChunk(
            chunk_id=chunk_id,
            original_content=content,
            processed_content=processed_content,
            chunk_type=ChunkType.IMAGE,
            requires_multimodal=requires_multimodal,
            image_data=image_data,
            metadata=metadata,
        )
    
    def _process_table_chunk(
        self,
        chunk_id: str,
        content: str,
        metadata: Dict[str, Any],
    ) -> ProcessedChunk:
        """
        Process table chunk.
        
        Converts table to structured text representation.
        """
        # Check if content is already text representation
        if isinstance(content, str) and content.strip():
            processed_content = content
        else:
            # Try to extract structured data
            table_data = metadata.get('table_data', [])
            if table_data:
                processed_content = self._table_to_text(table_data)
            else:
                processed_content = "[表格内容]"
        
        # Add table summary if available
        summary = metadata.get('summary', '')
        if summary:
            processed_content = f"表格摘要: {summary}\n\n{processed_content}"
        
        return ProcessedChunk(
            chunk_id=chunk_id,
            original_content=content,
            processed_content=processed_content,
            chunk_type=ChunkType.TABLE,
            requires_multimodal=False,
            metadata=metadata,
        )
    
    def _process_code_chunk(
        self,
        chunk_id: str,
        content: str,
        metadata: Dict[str, Any],
    ) -> ProcessedChunk:
        """
        Process code chunk.
        
        Adds language context and optional description.
        """
        language = metadata.get('language', 'unknown')
        description = metadata.get('description', '')
        
        # Build processed content
        parts = []
        if description:
            parts.append(f"代码说明: {description}")
        parts.append(f"编程语言: {language}")
        parts.append(f"代码:\n{content}")
        
        processed_content = "\n".join(parts)
        
        return ProcessedChunk(
            chunk_id=chunk_id,
            original_content=content,
            processed_content=processed_content,
            chunk_type=ChunkType.CODE,
            requires_multimodal=False,
            metadata=metadata,
        )
    
    def _is_base64_image(self, content: str) -> bool:
        """Check if content looks like base64 image data."""
        if not content:
            return False
        
        # Check for common base64 image prefixes
        prefixes = [
            'data:image/',
            '/9j/',  # JPEG
            'iVBORw',  # PNG
            'R0lGOD',  # GIF
        ]
        
        return any(content.startswith(p) for p in prefixes)
    
    def _table_to_text(self, table_data: List[List[Any]]) -> str:
        """Convert table data to text representation."""
        if not table_data:
            return ""
        
        lines = []
        for row in table_data:
            row_text = " | ".join(str(cell) for cell in row)
            lines.append(row_text)
        
        return "\n".join(lines)
    
    def get_embedding_inputs(
        self,
        result: MultimodalProcessingResult,
    ) -> Tuple[List[str], List[Dict[str, Any]]]:
        """
        Get inputs ready for embedding API.
        
        Args:
            result: MultimodalProcessingResult
            
        Returns:
            Tuple of (text_inputs, multimodal_inputs)
        """
        # Text inputs - just the processed content
        text_inputs = [
            chunk.processed_content
            for chunk in result.text_chunks
        ]
        
        # Multimodal inputs - include image data
        multimodal_inputs = []
        for chunk in result.multimodal_chunks:
            input_data = {
                "chunk_id": chunk.chunk_id,
                "text": chunk.processed_content,
            }
            if chunk.image_data:
                input_data["image"] = chunk.image_data
            multimodal_inputs.append(input_data)
        
        return text_inputs, multimodal_inputs


# Global instance
_default_processor = None


def get_multimodal_processor(use_multimodal_model: bool = False) -> MultimodalProcessor:
    """Get multimodal processor instance."""
    global _default_processor
    if _default_processor is None or _default_processor.use_multimodal_model != use_multimodal_model:
        _default_processor = MultimodalProcessor(use_multimodal_model)
    return _default_processor
