"""Chunk model for chunking results."""
from sqlalchemy import Column, String, Integer, Text, JSON, ForeignKey, Index
from sqlalchemy.orm import relationship
import uuid
from ..storage.database import Base


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
    
    # Indexes
    __table_args__ = (
        Index('idx_result_sequence', 'result_id', 'sequence_number', unique=True),
    )
    
    def __repr__(self):
        return f"<Chunk(id={self.id}, result_id={self.result_id}, sequence={self.sequence_number})>"
