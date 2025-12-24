"""
Query History Data Models

This module defines the SQLAlchemy model for query history and audit logs.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
import json

from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from pydantic import BaseModel, Field

from ..storage.database import Base


# ==================== SQLAlchemy Model ====================

class QueryHistory(Base):
    """SQLAlchemy model for query history"""
    
    __tablename__ = "query_history"
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign key to vector_indexes
    index_id = Column(Integer, ForeignKey("vector_indexes.id"), nullable=False)
    
    # Query information
    query_vector = Column(Text, nullable=True)  # JSON serialized vector
    top_k = Column(Integer, nullable=False)
    filters = Column(Text, nullable=True)  # JSON serialized filters
    
    # Results
    results_count = Column(Integer, default=0, nullable=False)
    search_time_ms = Column(Float, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    def __repr__(self):
        return f"<QueryHistory(id={self.id}, index_id={self.index_id}, results={self.results_count})>"
    
    def set_query_vector(self, vector: List[float]):
        """Set query vector from list"""
        self.query_vector = json.dumps(vector)
    
    def get_query_vector(self) -> Optional[List[float]]:
        """Get query vector as list"""
        if self.query_vector:
            return json.loads(self.query_vector)
        return None
    
    def set_filters(self, filters: Dict[str, Any]):
        """Set filters from dict"""
        self.filters = json.dumps(filters) if filters else None
    
    def get_filters(self) -> Optional[Dict[str, Any]]:
        """Get filters as dict"""
        if self.filters:
            return json.loads(self.filters)
        return None


# ==================== Pydantic Schemas ====================

class QueryHistorySchema(BaseModel):
    """Pydantic schema for query history"""
    
    id: Optional[int] = None
    index_id: int = Field(..., description="Index ID")
    query_vector: Optional[List[float]] = Field(None, description="Query vector")
    top_k: int = Field(..., gt=0, description="Number of results requested")
    filters: Optional[Dict[str, Any]] = Field(None, description="Filter expression")
    results_count: int = Field(default=0, ge=0, description="Actual results returned")
    search_time_ms: float = Field(..., ge=0, description="Search time in milliseconds")
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }
    
    def is_slow(self, threshold_ms: float = 100.0) -> bool:
        """Check if query was slow"""
        return self.search_time_ms > threshold_ms


class QueryHistoryListResponse(BaseModel):
    """Response model for listing query history"""
    
    queries: List[QueryHistorySchema]
    total: int
    limit: int
    offset: int
