"""HybridChunkingConfig model for hybrid chunking strategy."""
from sqlalchemy import Column, String, JSON, ForeignKey, Index, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from ..storage.database import Base


class HybridChunkingConfig(Base):
    """HybridChunkingConfig entity for storing content-type specific chunking strategies.
    
    Stores the mapping between content types (text, table, image, code) and their
    respective chunking strategies for hybrid chunking.
    """
    
    __tablename__ = "hybrid_chunking_configs"
    
    # Primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Foreign key to chunking result
    result_id = Column(String(36), ForeignKey('chunking_results.result_id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Content type (text, table, image, code)
    content_type = Column(String(20), nullable=False, comment="Content type: text/table/image/code")
    
    # Strategy for this content type
    strategy_type = Column(String(20), nullable=False, comment="Chunking strategy type for this content")
    
    # Strategy parameters
    strategy_params = Column(JSON, nullable=True, comment="Strategy-specific parameters")
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationship to chunking result
    result = relationship(
        "ChunkingResult",
        back_populates="hybrid_configs",
        lazy="select"
    )
    
    # Indexes and constraints
    __table_args__ = (
        Index('idx_hybrid_config_result', 'result_id'),
        UniqueConstraint('result_id', 'content_type', name='uq_result_content_type'),
    )
    
    def __repr__(self):
        return f"<HybridChunkingConfig(id={self.id}, result_id={self.result_id}, content_type={self.content_type}, strategy={self.strategy_type})>"
    
    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "result_id": self.result_id,
            "content_type": self.content_type,
            "strategy_type": self.strategy_type,
            "strategy_params": self.strategy_params,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
