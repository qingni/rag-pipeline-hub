"""Chunk model for chunking results."""
from sqlalchemy import Column, String, Integer, Text, JSON, ForeignKey, Index, Enum as SQLEnum
from sqlalchemy.orm import relationship
import uuid
import enum
from ..storage.database import Base


class ChunkType(enum.Enum):
    """Chunk type enumeration for multimodal support."""
    TEXT = "text"
    TABLE = "table"
    IMAGE = "image"
    CODE = "code"


class Chunk(Base):
    """Chunk entity representing a single text chunk from chunking operation."""
    
    __tablename__ = "chunks"
    
    # Primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Foreign key to chunking result
    result_id = Column(String(36), ForeignKey('chunking_results.result_id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Chunk information
    sequence_number = Column(Integer, nullable=False, comment="Chunk sequence number starting from 0")
    content = Column(Text, nullable=False, comment="Chunk text content")
    
    # Chunk type for multimodal support (NEW)
    chunk_type = Column(SQLEnum(ChunkType, values_callable=lambda x: [e.value for e in x]), nullable=False, default=ChunkType.TEXT, comment="Chunk type: text/table/image/code")
    
    # Parent chunk reference for parent-child chunking (NEW)
    parent_id = Column(String(36), ForeignKey('parent_chunks.id', ondelete='SET NULL'), nullable=True, comment="Parent chunk ID for parent-child chunking")
    
    # Chunk metadata (using different name to avoid SQLAlchemy reserved keyword)
    chunk_metadata = Column(JSON, nullable=False, comment="Chunk metadata including positions, token count, etc.")
    
    # Position information (denormalized for queries)
    start_position = Column(Integer, nullable=True, comment="Start character position in source text")
    end_position = Column(Integer, nullable=True, comment="End character position in source text")
    token_count = Column(Integer, nullable=True, comment="Token/character count for this chunk")
    
    # Relationship
    result = relationship(
        "ChunkingResult",
        back_populates="chunks",
        lazy="select"
    )
    
    # Relationship to parent chunk
    parent = relationship(
        "ParentChunk",
        back_populates="children",
        lazy="select",
        foreign_keys=[parent_id]
    )
    
    # Indexes
    __table_args__ = (
        Index('idx_result_sequence', 'result_id', 'sequence_number', unique=True),
        Index('idx_chunk_parent', 'parent_id'),
        Index('idx_chunk_type', 'chunk_type'),
    )
    
    def __repr__(self):
        return f"<Chunk(id={self.id}, result_id={self.result_id}, sequence={self.sequence_number}, type={self.chunk_type.value})>"
