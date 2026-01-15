"""Loading Task model for async document processing.

Tracks the status of asynchronous document loading tasks,
particularly for Docling Serve which supports async API.
"""
from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from ..storage.database import Base


class LoadingTaskStatus:
    """Loading task status constants."""
    PENDING = "pending"      # Task submitted, waiting to start
    STARTED = "started"      # Task is being processed
    SUCCESS = "success"      # Task completed successfully
    FAILURE = "failure"      # Task failed
    CANCELLED = "cancelled"  # Task was cancelled


class LoadingTask(Base):
    """Loading task entity for tracking async document processing."""
    
    __tablename__ = "loading_tasks"
    
    # Primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Document reference
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    
    # External task ID (from Docling Serve)
    external_task_id = Column(String(100), nullable=True)
    
    # Loader information
    loader_type = Column(String(50), nullable=False, default="docling_serve")
    
    # Status tracking
    status = Column(String(20), nullable=False, default=LoadingTaskStatus.PENDING)
    progress = Column(Integer, default=0)  # 0-100
    
    # Timing
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Result
    result_path = Column(String(500), nullable=True)  # Path to saved result JSON
    error_message = Column(Text, nullable=True)
    
    # Processing metadata
    processing_time = Column(Float, nullable=True)  # In seconds
    
    # Relationships
    document = relationship("Document", backref="loading_tasks")
    
    def __repr__(self):
        return f"<LoadingTask(id={self.id}, document_id={self.document_id}, status={self.status})>"
    
    def to_dict(self):
        """Convert to dictionary for API response."""
        return {
            "id": self.id,
            "document_id": self.document_id,
            "external_task_id": self.external_task_id,
            "loader_type": self.loader_type,
            "status": self.status,
            "progress": self.progress,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result_path": self.result_path,
            "error_message": self.error_message,
            "processing_time": self.processing_time
        }
