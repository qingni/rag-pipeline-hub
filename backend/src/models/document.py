"""Document model."""
from sqlalchemy import Column, String, Integer, DateTime, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from ..storage.database import Base


class Document(Base):
    """Document entity representing uploaded files."""
    
    __tablename__ = "documents"
    
    # Primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # File information
    filename = Column(String(255), nullable=False)
    format = Column(String(50), nullable=False)  # pdf, doc, docx, txt
    size_bytes = Column(Integer, nullable=False)
    upload_time = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    storage_path = Column(String, nullable=False)
    content_hash = Column(String(64), nullable=True)  # SHA256 hash
    
    # Status
    status = Column(String(20), nullable=False, default="uploaded")  # uploaded, processing, ready, error
    
    # Relationships - use string references to avoid circular imports
    processing_results = relationship(
        "ProcessingResult",
        back_populates="document",
        cascade="all, delete-orphan",
        lazy="select"
    )
    
    # Indexes
    __table_args__ = (
        Index('idx_upload_time', 'upload_time'),
        Index('idx_status', 'status'),
    )
    
    def __repr__(self):
        return f"<Document(id={self.id}, filename={self.filename}, status={self.status})>"
