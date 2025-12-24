"""
Index Statistics Data Models

This module defines the SQLAlchemy model for index statistics and performance metrics.
"""

from datetime import datetime
from typing import Optional
import uuid

from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey
from sqlalchemy.sql import func
from pydantic import BaseModel, Field

from ..storage.database import Base


# ==================== SQLAlchemy Model ====================

class IndexStatistics(Base):
    """SQLAlchemy model for index statistics"""
    
    __tablename__ = "index_statistics"
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign key to vector_indexes
    index_id = Column(Integer, ForeignKey("vector_indexes.id"), nullable=False)
    
    # Statistics
    vector_count = Column(Integer, default=0, nullable=False)
    total_queries = Column(Integer, default=0, nullable=False)
    avg_search_time_ms = Column(Float, default=0.0, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    def __repr__(self):
        return f"<IndexStatistics(id={self.id}, index_id={self.index_id}, vector_count={self.vector_count})>"


# ==================== Pydantic Schemas ====================

class IndexStatisticsSchema(BaseModel):
    """Pydantic schema for index statistics"""
    
    id: Optional[int] = None
    index_id: int = Field(..., description="Associated index ID")
    vector_count: int = Field(default=0, ge=0, description="Total vectors")
    total_queries: int = Field(default=0, ge=0, description="Total queries")
    avg_search_time_ms: float = Field(default=0.0, ge=0, description="Average search time (ms)")
    created_at: Optional[datetime] = None
    last_updated: Optional[datetime] = None
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }
    
    def is_healthy(self) -> bool:
        """Check if index statistics indicate healthy state"""
        # High latency indicates problem (>100ms threshold)
        if self.avg_search_time_ms > 100:
            return False
        return True


class StatisticsResponse(BaseModel):
    """Response model for statistics queries"""
    
    index_id: int
    index_name: str
    vector_count: int
    dimension: int
    index_type: str
    metric_type: str
    total_queries: int
    avg_search_time_ms: float
    memory_usage_bytes: int
    created_at: str
    last_updated: str
