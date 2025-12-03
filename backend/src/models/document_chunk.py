"""Document chunk model."""
from sqlalchemy import Column, String, Integer, DateTime, Text, JSON, Index, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from ..storage.database import Base


class DocumentChunk(Base):
    """Document chunk entity representing text segments."""
    
    __tablename__ = "document_chunks"
    
    # Primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Foreign key to document
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    
    # Chunk information
    chunk_index = Column(Integer, nullable=False)  # Sequential index within document
    content = Column(Text, nullable=False)  # Chunk text content
    char_count = Column(Integer, nullable=False)  # Number of characters
    
    # Source information
    source_pages = Column(JSON, nullable=True)  # List of source page numbers
    
    # Additional metadata (renamed from 'metadata' to avoid SQLAlchemy conflict)
    chunk_metadata = Column(JSON, nullable=True)  # Additional metadata
    created_time = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Embedding information (will be used later)
    embedding_status = Column(String(20), nullable=False, default="pending")  # pending, completed, failed
    
    # Relationships
    document = relationship("Document", back_populates="chunks")
    
    # Indexes
    __table_args__ = (
        Index('idx_chunk_document_id', 'document_id'),
        Index('idx_chunk_index', 'document_id', 'chunk_index'),
        Index('idx_chunk_embedding_status', 'embedding_status'),
    )
    
    def __repr__(self):
        return f"<DocumentChunk(id={self.id}, document_id={self.document_id}, chunk_index={self.chunk_index})>"
