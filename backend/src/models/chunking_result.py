"""ChunkingResult model."""
from sqlalchemy import Column, String, Integer, Float, DateTime, JSON, Enum as SQLEnum, ForeignKey, Index
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
    
    # Indexes
    __table_args__ = (
        Index('idx_doc_strategy_time', 'document_name', 'chunking_strategy', 'created_at'),
    )
    
    def __repr__(self):
        return f"<ChunkingResult(result_id={self.result_id}, document_name={self.document_name}, status={self.status.value}, chunks={self.total_chunks})>"
