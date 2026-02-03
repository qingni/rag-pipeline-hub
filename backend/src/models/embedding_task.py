"""
EmbeddingTask model for tracking embedding operations.

Implements:
- Task lifecycle management
- Progress tracking
- Configuration storage
"""
import uuid
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from dataclasses import dataclass, field, asdict

from sqlalchemy import Column, String, DateTime, Text, Index
from sqlalchemy.sql import func

from ..storage.database import Base


class EmbeddingTaskStatus(str, Enum):
    """Status of an embedding task."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIAL = "partial"       # 部分成功
    FAILED = "failed"
    CANCELLED = "cancelled"   # 用户取消


@dataclass
class EmbeddingConfig:
    """Configuration for embedding task."""
    batch_size: int = 50           # 批量大小 (10-200)
    concurrency: int = 5           # 并发数 (1-20)
    enable_cache: bool = True      # 启用缓存
    incremental: bool = True       # 增量模式
    force_recompute: bool = False  # 强制重新计算
    multimodal_model: str = "qwen3-vl-embedding-8b"  # 多模态模型
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EmbeddingConfig":
        """Create from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
    
    def validate(self) -> None:
        """Validate configuration values."""
        if not 10 <= self.batch_size <= 200:
            raise ValueError("Batch size must be between 10 and 200")
        if not 1 <= self.concurrency <= 20:
            raise ValueError("Concurrency must be between 1 and 20")


@dataclass
class EmbeddingProgress:
    """Progress tracking for embedding task."""
    total_chunks: int = 0
    completed: int = 0
    failed: int = 0
    cached: int = 0
    current_batch: int = 0
    speed: float = 0.0                   # 块/秒
    eta_seconds: float = 0.0             # 预估剩余秒数
    
    @property
    def percentage(self) -> float:
        """Calculate completion percentage."""
        return (self.completed / self.total_chunks) * 100 if self.total_chunks > 0 else 0
    
    @property
    def cache_hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total_processed = self.completed + self.cached
        return (self.cached / total_processed) * 100 if total_processed > 0 else 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with computed properties."""
        result = asdict(self)
        result['percentage'] = self.percentage
        result['cache_hit_rate'] = self.cache_hit_rate
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EmbeddingProgress":
        """Create from dictionary."""
        # Filter out computed properties
        valid_fields = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**valid_fields)


class EmbeddingTask(Base):
    """
    Database model for tracking embedding tasks.
    
    Implements:
    - Task lifecycle (pending -> running -> completed/failed/cancelled)
    - Configuration persistence
    - Progress tracking
    """
    
    __tablename__ = "embedding_tasks"
    
    # Identity
    task_id = Column(
        String(36), 
        primary_key=True, 
        default=lambda: str(uuid.uuid4()),
        comment="Unique task identifier"
    )
    
    # Source references
    document_id = Column(
        String(36), 
        nullable=False,
        comment="Reference to source document"
    )
    chunking_result_id = Column(
        String(36), 
        nullable=False,
        comment="Reference to chunking result"
    )
    
    # Model configuration
    model = Column(
        String(50), 
        nullable=False,
        comment="Embedding model name"
    )
    
    # Status tracking
    status = Column(
        String(20), 
        nullable=False,
        default=EmbeddingTaskStatus.PENDING.value,
        comment="Task status"
    )
    
    # Configuration (JSON)
    config = Column(
        Text, 
        nullable=False,
        default="{}",
        comment="Task configuration JSON"
    )
    
    # Progress (JSON)
    progress = Column(
        Text, 
        nullable=True,
        comment="Progress tracking JSON"
    )
    
    # Timestamps
    created_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        nullable=False,
        comment="Task creation time"
    )
    updated_at = Column(
        DateTime(timezone=True), 
        nullable=True,
        comment="Last update time"
    )
    completed_at = Column(
        DateTime(timezone=True), 
        nullable=True,
        comment="Task completion time"
    )
    
    # Error tracking
    error_message = Column(
        Text, 
        nullable=True,
        comment="Error message if failed"
    )
    
    # Indexes
    __table_args__ = (
        Index('idx_task_document', 'document_id'),
        Index('idx_task_status', 'status'),
        Index('idx_task_created', 'created_at'),
    )
    
    def __repr__(self):
        return (
            f"<EmbeddingTask("
            f"id={self.task_id[:8]}..., "
            f"doc={self.document_id[:8]}..., "
            f"model={self.model}, "
            f"status={self.status}"
            f")>"
        )
    
    def get_config(self) -> EmbeddingConfig:
        """Get configuration as EmbeddingConfig object."""
        import json
        try:
            data = json.loads(self.config) if self.config else {}
            return EmbeddingConfig.from_dict(data)
        except (json.JSONDecodeError, TypeError):
            return EmbeddingConfig()
    
    def set_config(self, config: EmbeddingConfig) -> None:
        """Set configuration from EmbeddingConfig object."""
        import json
        self.config = json.dumps(config.to_dict())
    
    def get_progress(self) -> Optional[EmbeddingProgress]:
        """Get progress as EmbeddingProgress object."""
        import json
        if not self.progress:
            return None
        try:
            data = json.loads(self.progress)
            return EmbeddingProgress.from_dict(data)
        except (json.JSONDecodeError, TypeError):
            return None
    
    def set_progress(self, progress: EmbeddingProgress) -> None:
        """Set progress from EmbeddingProgress object."""
        import json
        self.progress = json.dumps(progress.to_dict())
    
    def update_status(self, status: EmbeddingTaskStatus, error_message: Optional[str] = None) -> None:
        """Update task status with timestamp."""
        self.status = status.value
        self.updated_at = datetime.utcnow()
        
        if status in (EmbeddingTaskStatus.COMPLETED, EmbeddingTaskStatus.FAILED, 
                      EmbeddingTaskStatus.PARTIAL, EmbeddingTaskStatus.CANCELLED):
            self.completed_at = datetime.utcnow()
        
        if error_message:
            self.error_message = error_message
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "task_id": self.task_id,
            "document_id": self.document_id,
            "chunking_result_id": self.chunking_result_id,
            "model": self.model,
            "status": self.status,
            "config": self.get_config().to_dict(),
            "progress": self.get_progress().to_dict() if self.get_progress() else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
        }
