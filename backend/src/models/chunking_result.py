"""ChunkingResult model."""
from sqlalchemy import Column, String, Integer, Float, DateTime, JSON, Enum as SQLEnum, ForeignKey, Index, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
import enum
from .chunking_task import StrategyType
from ..storage.database import Base


class ResultStatus(enum.Enum):
    """Result status enumeration."""
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"


class ChunkingResult(Base):
    """ChunkingResult entity containing chunking operation results."""
    
    __tablename__ = "chunking_results"
    
    # Primary key
    result_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Foreign key to task
    task_id = Column(String(36), ForeignKey('chunking_tasks.task_id'), nullable=False, unique=True)
    
    # Document information
    document_id = Column(String(255), nullable=False, index=True)
    document_name = Column(String(255), nullable=False, index=True)
    source_file = Column(String(500), nullable=False)
    
    # Result metadata
    total_chunks = Column(Integer, nullable=False)
    chunking_strategy = Column(SQLEnum(StrategyType), nullable=False, index=True)
    chunking_params = Column(JSON, nullable=False)
    status = Column(SQLEnum(ResultStatus), nullable=False)
    
    # Timestamps and performance
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    processing_time = Column(Float, nullable=False)
    
    # Error information
    error_info = Column(JSON, nullable=True)
    
    # Statistics
    statistics = Column(JSON, nullable=False)
    
    # File storage
    json_file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)
    
    # Version management (Phase 1 optimization)
    version = Column(Integer, default=1, nullable=False)
    previous_version_id = Column(String(36), nullable=True)  # Link to previous version
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    replacement_reason = Column(String(200), nullable=True)  # Why this replaced previous version
    
    # Relationships
    task = relationship(
        "ChunkingTask",
        back_populates="result",
        lazy="select"
    )
    
    chunks = relationship(
        "Chunk",
        back_populates="result",
        cascade="all, delete-orphan",
        lazy="select"
    )
    
    # Parent chunks relationship for parent-child chunking (NEW)
    parent_chunks = relationship(
        "ParentChunk",
        back_populates="result",
        cascade="all, delete-orphan",
        lazy="select"
    )
    
    # Hybrid chunking configs relationship (NEW)
    hybrid_configs = relationship(
        "HybridChunkingConfig",
        back_populates="result",
        cascade="all, delete-orphan",
        lazy="select"
    )
    
    # Indexes
    __table_args__ = (
        Index('idx_doc_strategy_time', 'document_name', 'chunking_strategy', 'created_at'),
        Index('idx_doc_strategy_active', 'document_id', 'chunking_strategy', 'is_active'),
    )
    
    def __repr__(self):
        return f"<ChunkingResult(result_id={self.result_id}, document_name={self.document_name}, status={self.status.value}, chunks={self.total_chunks})>"
