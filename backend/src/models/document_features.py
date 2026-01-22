"""DocumentFeatures data class for chunking recommendation."""
from dataclasses import dataclass, field, asdict
from typing import Dict, Any


@dataclass
class DocumentFeatures:
    """Document structure features for intelligent chunking recommendation.
    
    This class captures the structural characteristics of a document
    that are used to recommend the most suitable chunking strategy.
    """
    
    # Heading analysis
    heading_count: int = 0  # Total heading count
    heading_levels: Dict[int, int] = field(default_factory=dict)  # {1: 3, 2: 12, 3: 25}
    
    # Paragraph analysis
    paragraph_count: int = 0
    avg_paragraph_length: float = 0.0
    max_paragraph_length: int = 0
    min_paragraph_length: int = 0
    
    # Multimodal content
    table_count: int = 0
    image_count: int = 0
    
    # Code analysis
    code_block_count: int = 0
    code_block_ratio: float = 0.0  # Ratio of code content to total content
    
    # Document statistics
    total_char_count: int = 0
    total_word_count: int = 0
    
    # Additional features
    has_clear_structure: bool = False
    is_technical_document: bool = False
    is_narrative_document: bool = False
    is_structured_data: bool = False  # JSON/key-value structured data
    document_format: str = ""  # 原始文档格式（json, csv, etc.）
    estimated_complexity: str = "medium"  # low, medium, high
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DocumentFeatures":
        """Create from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
    
    def get_heading_summary(self) -> str:
        """Get a summary of heading structure."""
        if not self.heading_levels:
            return "无标题结构"
        
        parts = []
        for level, count in sorted(self.heading_levels.items()):
            parts.append(f"H{level}: {count}个")
        return ", ".join(parts)
    
    def get_multimodal_summary(self) -> str:
        """Get a summary of multimodal content."""
        parts = []
        if self.table_count > 0:
            parts.append(f"{self.table_count}个表格")
        if self.image_count > 0:
            parts.append(f"{self.image_count}个图片")
        if self.code_block_count > 0:
            parts.append(f"{self.code_block_count}个代码块")
        return ", ".join(parts) if parts else "无多模态内容"
