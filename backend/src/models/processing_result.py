"""Processing result model."""
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from ..storage.database import Base


class ProcessingResult(Base):
    """Processing result entity for tracking document processing operations."""
    
    __tablename__ = "processing_results"
    
    # Primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Foreign key
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    
    # Processing information
    processing_type = Column(String(50), nullable=False)  # load, parse, chunk, embed, index, generate
    provider = Column(String(50), nullable=True)  # pymupdf, openai, milvus, etc.
    result_path = Column(String, nullable=False)  # Path to JSON result file
    extra_metadata = Column(JSON, nullable=True)  # Additional metadata
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Status
    status = Column(String(20), nullable=False, default="pending")  # pending, running, completed, failed
    error_message = Column(String, nullable=True)
    
    # Relationships
    document = relationship("Document", back_populates="processing_results")
    chunks = relationship("DocumentChunk", back_populates="processing_result")
    embeddings = relationship("VectorEmbedding", back_populates="processing_result")
    
    # Indexes
    __table_args__ = (
        Index('idx_document_id', 'document_id'),
        Index('idx_document_type_time', 'document_id', 'processing_type', 'created_at'),
    )
    
    def __repr__(self):
        return f"<ProcessingResult(id={self.id}, type={self.processing_type}, status={self.status})>"
