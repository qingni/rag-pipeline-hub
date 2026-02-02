"""ParentChunk model for parent-child chunking."""
from sqlalchemy import Column, String, Integer, Text, JSON, ForeignKey, Index, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from ..storage.database import Base


class ParentChunk(Base):
    """ParentChunk entity for parent-child chunking strategy.
    
    Stores parent chunks that contain complete context content.
    Child chunks reference parent chunks via parent_id in the Chunk model.
    """
    
    __tablename__ = "parent_chunks"
    
    # Primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Foreign key to chunking result
    result_id = Column(String(36), ForeignKey('chunking_results.result_id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Parent chunk information
    sequence_number = Column(Integer, nullable=False, comment="Parent chunk sequence number starting from 0")
    content = Column(Text, nullable=False, comment="Parent chunk complete content")
    
    # Position information
    start_position = Column(Integer, nullable=True, comment="Start character position in source text")
    end_position = Column(Integer, nullable=True, comment="End character position in source text")
    
    # Child count for quick reference
    child_count = Column(Integer, default=0, comment="Number of child chunks")
    
    # Metadata (using chunk_metadata to avoid SQLAlchemy reserved name)
    chunk_metadata = Column(JSON, nullable=True, comment="Additional metadata")
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationship to chunking result
    result = relationship(
        "ChunkingResult",
        back_populates="parent_chunks",
        lazy="select"
    )
    
    # Relationship to child chunks
    children = relationship(
        "Chunk",
        back_populates="parent",
        lazy="select",
        foreign_keys="Chunk.parent_id"
    )
    
    # Indexes
    __table_args__ = (
        Index('idx_parent_chunk_result', 'result_id'),
        Index('idx_parent_chunk_sequence', 'result_id', 'sequence_number', unique=True),
    )
    
    def __repr__(self):
        return f"<ParentChunk(id={self.id}, result_id={self.result_id}, sequence={self.sequence_number}, children={self.child_count})>"
    
    def to_dict(self, include_children: bool = False) -> dict:
        """Convert to dictionary representation."""
        data = {
            "id": self.id,
            "result_id": self.result_id,
            "sequence_number": self.sequence_number,
            "content": self.content,
            "content_preview": self.content[:100] + "..." if len(self.content) > 100 else self.content,
            "start_position": self.start_position,
            "end_position": self.end_position,
            "child_count": self.child_count,
            "metadata": self.chunk_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
        
        if include_children and self.children:
            data["children"] = [
                {
                    "id": child.id,
                    "parent_id": self.id,  # 添加parent_id方便前端映射
                    "sequence_number": child.sequence_number,
                    "content": child.content,  # 完整内容
                    "content_preview": child.content[:100] + "..." if len(child.content) > 100 else child.content,
                    "chunk_type": child.chunk_type.value if child.chunk_type else "text",
                    "metadata": {
                        **({"char_count": len(child.content)} if child.content else {}),
                        **(child.chunk_metadata or {})
                    }
                }
                for child in self.children
            ]
        
        return data
