"""
VectorCache model for caching embedding vectors.

Implements:
- Content-based caching (SHA-256 hash)
- LRU eviction support
- Access tracking
"""
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from sqlalchemy import Column, String, Integer, Float, DateTime, LargeBinary, Index
from sqlalchemy.sql import func

from ..storage.database import Base


class VectorCache(Base):
    """
    Database model for caching embedding vectors.
    
    Cache key format: {content_hash[:16]}:{model}
    
    Implements:
    - Content-based caching to avoid duplicate computation
    - LRU tracking via last_accessed_at and access_count
    - Model-specific caching (same content, different models = different cache entries)
    """
    
    __tablename__ = "vector_cache"
    
    # Primary key: combination of content hash prefix and model
    cache_key = Column(
        String(100), 
        primary_key=True,
        comment="Cache key: {content_hash[:16]}:{model}"
    )
    
    # Full content hash for collision detection
    content_hash = Column(
        String(64), 
        nullable=False,
        comment="Full SHA-256 hash of content"
    )
    
    # Model identifier
    model = Column(
        String(50), 
        nullable=False,
        comment="Embedding model name"
    )
    
    # Vector data (stored as binary for efficiency)
    vector = Column(
        LargeBinary, 
        nullable=False,
        comment="Vector data as binary"
    )
    
    # Vector dimension for validation
    dimension = Column(
        Integer, 
        nullable=False,
        comment="Vector dimension"
    )
    
    # Timestamps for LRU
    created_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        nullable=False,
        comment="Cache entry creation time"
    )
    last_accessed_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        nullable=False,
        comment="Last access time for LRU"
    )
    
    # Access count for statistics
    access_count = Column(
        Integer, 
        default=1,
        comment="Number of cache hits"
    )
    
    # Indexes
    __table_args__ = (
        Index('idx_cache_model', 'model'),
        Index('idx_cache_last_accessed', 'last_accessed_at'),
    )
    
    def __repr__(self):
        return (
            f"<VectorCache("
            f"key={self.cache_key}, "
            f"model={self.model}, "
            f"dim={self.dimension}, "
            f"hits={self.access_count}"
            f")>"
        )
    
    @staticmethod
    def make_cache_key(content_hash: str, model: str) -> str:
        """Generate cache key from content hash and model."""
        return f"{content_hash[:16]}:{model}"
    
    def get_vector(self) -> List[float]:
        """Deserialize vector from binary."""
        import struct
        # Unpack as array of doubles
        return list(struct.unpack(f'{self.dimension}d', self.vector))
    
    def set_vector(self, vector: List[float]) -> None:
        """Serialize vector to binary."""
        import struct
        self.vector = struct.pack(f'{len(vector)}d', *vector)
        self.dimension = len(vector)
    
    def touch(self) -> None:
        """Update access time and count."""
        self.last_accessed_at = datetime.utcnow()
        self.access_count += 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (without vector data)."""
        return {
            "cache_key": self.cache_key,
            "content_hash": self.content_hash,
            "model": self.model,
            "dimension": self.dimension,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_accessed_at": self.last_accessed_at.isoformat() if self.last_accessed_at else None,
            "access_count": self.access_count,
        }


@dataclass
class CachedVector:
    """Cached vector data for service layer."""
    vector: List[float]
    dimension: int
    content_hash: str
    model: str
    created_at: Optional[datetime] = None
    
    def validate_dimension(self, expected_dimension: int) -> bool:
        """Validate vector dimension matches expected."""
        return self.dimension == expected_dimension


@dataclass
class CacheStats:
    """Cache statistics for monitoring."""
    total_entries: int = 0
    total_size_bytes: int = 0
    hit_count: int = 0
    miss_count: int = 0
    eviction_count: int = 0
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.hit_count + self.miss_count
        return (self.hit_count / total) * 100 if total > 0 else 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_entries": self.total_entries,
            "total_size_bytes": self.total_size_bytes,
            "hit_count": self.hit_count,
            "miss_count": self.miss_count,
            "eviction_count": self.eviction_count,
            "hit_rate": self.hit_rate,
        }
