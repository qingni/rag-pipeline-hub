"""ChunkingTask model."""
from sqlalchemy import Column, String, Integer, DateTime, JSON, Enum as SQLEnum, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
import enum
from ..storage.database import Base


class TaskStatus(enum.Enum):
    """Task status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StrategyType(enum.Enum):
    """Chunking strategy type enumeration."""
    CHARACTER = "character"
    PARAGRAPH = "paragraph"
    HEADING = "heading"
    SEMANTIC = "semantic"
    PARENT_CHILD = "parent_child"  # 父子文档分块
    HYBRID = "hybrid"              # 混合分块策略


class ChunkingTask(Base):
    """ChunkingTask entity representing a chunking operation."""
    
    __tablename__ = "chunking_tasks"
    
    # Primary key
    task_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Source document information
    source_document_id = Column(String(255), nullable=False, index=True)
    source_file_path = Column(String(500), nullable=False)
    
    # Chunking configuration
    chunking_strategy = Column(SQLEnum(StrategyType), nullable=False)
    chunking_params = Column(JSON, nullable=False)
    
    # Status and queue management
    status = Column(SQLEnum(TaskStatus), nullable=False, default=TaskStatus.PENDING)
    queue_position = Column(Integer, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Error tracking
    error_message = Column(String(1000), nullable=True)
    
    # Relationships
    result = relationship(
        "ChunkingResult",
        back_populates="task",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="select"
    )
    
    # Indexes
    __table_args__ = (
        Index('idx_status_created', 'status', 'created_at'),
    )
    
    def __repr__(self):
        return f"<ChunkingTask(task_id={self.task_id}, status={self.status.value}, strategy={self.chunking_strategy.value})>"
