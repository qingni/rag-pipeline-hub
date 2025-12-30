"""Generation history database model."""
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text, JSON
from sqlalchemy.sql import func

from ..storage.database import Base


class GenerationStatus(str, Enum):
    """Generation request status."""
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class GenerationHistory(Base):
    """Generation history model for storing text generation records."""
    
    __tablename__ = "generation_history"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    request_id = Column(String(36), unique=True, nullable=False, index=True)
    question = Column(Text, nullable=False)
    model = Column(String(50), nullable=False)
    temperature = Column(Float, default=0.7)
    max_tokens = Column(Integer, default=4096)
    context_summary = Column(Text, nullable=True)
    context_sources = Column(JSON, nullable=True)
    answer = Column(Text, nullable=True)
    token_usage = Column(JSON, nullable=True)
    processing_time_ms = Column(Float, nullable=True)
    status = Column(String(20), nullable=False, default=GenerationStatus.PENDING.value, index=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=func.now(), index=True)
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    is_deleted = Column(Boolean, default=False, index=True)
    
    def __repr__(self) -> str:
        return f"<GenerationHistory(id={self.id}, request_id={self.request_id}, status={self.status})>"
    
    def to_dict(self) -> dict:
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "request_id": self.request_id,
            "question": self.question,
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "context_summary": self.context_summary,
            "context_sources": self.context_sources,
            "answer": self.answer,
            "token_usage": self.token_usage,
            "processing_time_ms": self.processing_time_ms,
            "status": self.status,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "is_deleted": self.is_deleted
        }
    
    def get_answer_preview(self, max_length: int = 200) -> str:
        """Get truncated answer preview."""
        if not self.answer:
            return ""
        if len(self.answer) <= max_length:
            return self.answer
        return self.answer[:max_length] + "..."
