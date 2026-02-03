"""
Vector cache service with LRU eviction.

Provides:
- Content-based vector caching
- LRU eviction strategy
- Cache statistics
"""
import struct
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta

from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from ..models.vector_cache import VectorCache, CachedVector, CacheStats
from ..services.content_hash_service import ContentHashService, get_content_hash_service


class VectorCacheService:
    """
    LRU cache service for embedding vectors.
    
    Features:
    - Content-based caching (same content = same vector)
    - Model-specific caching
    - LRU eviction when cache is full
    - Access tracking for statistics
    """
    
    def __init__(
        self,
        max_entries: int = 10000,
        ttl_hours: int = 24 * 7,  # 7 days default
        hash_service: Optional[ContentHashService] = None,
    ):
        """
        Initialize cache service.
        
        Args:
            max_entries: Maximum cache entries before eviction
            ttl_hours: Time-to-live for cache entries (hours)
            hash_service: Content hash service
        """
        self.max_entries = max_entries
        self.ttl = timedelta(hours=ttl_hours)
        self.hash_service = hash_service or get_content_hash_service()
        
        # In-memory stats
        self._stats = CacheStats()
    
    def get(
        self,
        db: Session,
        content: str,
        model: str,
    ) -> Optional[CachedVector]:
        """
        Get cached vector for content.
        
        Args:
            db: Database session
            content: Text content
            model: Model name
            
        Returns:
            CachedVector if found, None otherwise
        """
        content_hash = self.hash_service.compute_hash_raw(content)
        cache_key = VectorCache.make_cache_key(content_hash, model)
        
        entry = db.query(VectorCache).filter(
            VectorCache.cache_key == cache_key
        ).first()
        
        if entry is None:
            self._stats.miss_count += 1
            return None
        
        # Verify full hash matches (collision check)
        if entry.content_hash != content_hash:
            self._stats.miss_count += 1
            return None
        
        # Check TTL
        if self._is_expired(entry):
            self._stats.miss_count += 1
            # Could delete expired entry here
            return None
        
        # Update access time and count
        entry.touch()
        db.commit()
        
        self._stats.hit_count += 1
        
        return CachedVector(
            vector=entry.get_vector(),
            dimension=entry.dimension,
            content_hash=entry.content_hash,
            model=entry.model,
            created_at=entry.created_at,
        )
    
    def get_batch(
        self,
        db: Session,
        contents: List[str],
        model: str,
    ) -> Tuple[List[CachedVector], List[int]]:
        """
        Get cached vectors for multiple contents.
        
        Args:
            db: Database session
            contents: List of text contents
            model: Model name
            
        Returns:
            Tuple of (cached_vectors, miss_indices)
        """
        cached = []
        miss_indices = []
        
        for i, content in enumerate(contents):
            result = self.get(db, content, model)
            if result:
                cached.append(result)
            else:
                miss_indices.append(i)
        
        return cached, miss_indices
    
    def put(
        self,
        db: Session,
        content: str,
        model: str,
        vector: List[float],
    ) -> VectorCache:
        """
        Store vector in cache.
        
        Args:
            db: Database session
            content: Text content
            model: Model name
            vector: Embedding vector
            
        Returns:
            VectorCache entry
        """
        content_hash = self.hash_service.compute_hash_raw(content)
        cache_key = VectorCache.make_cache_key(content_hash, model)
        
        # Check if entry already exists
        entry = db.query(VectorCache).filter(
            VectorCache.cache_key == cache_key
        ).first()
        
        if entry:
            # Update existing entry
            entry.set_vector(vector)
            entry.last_accessed_at = datetime.utcnow()
            entry.access_count += 1
        else:
            # Check cache size and evict if needed
            self._evict_if_needed(db)
            
            # Create new entry
            entry = VectorCache(
                cache_key=cache_key,
                content_hash=content_hash,
                model=model,
                dimension=len(vector),
            )
            entry.set_vector(vector)
            db.add(entry)
        
        db.commit()
        return entry
    
    def put_batch(
        self,
        db: Session,
        contents: List[str],
        model: str,
        vectors: List[List[float]],
    ) -> int:
        """
        Store multiple vectors in cache.
        
        Args:
            db: Database session
            contents: List of text contents
            model: Model name
            vectors: List of embedding vectors
            
        Returns:
            Number of entries stored
        """
        if len(contents) != len(vectors):
            raise ValueError("Contents and vectors must have same length")
        
        stored = 0
        for content, vector in zip(contents, vectors):
            self.put(db, content, model, vector)
            stored += 1
        
        return stored
    
    def delete(
        self,
        db: Session,
        content: str,
        model: str,
    ) -> bool:
        """
        Delete cached vector.
        
        Args:
            db: Database session
            content: Text content
            model: Model name
            
        Returns:
            True if deleted
        """
        content_hash = self.hash_service.compute_hash_raw(content)
        cache_key = VectorCache.make_cache_key(content_hash, model)
        
        result = db.query(VectorCache).filter(
            VectorCache.cache_key == cache_key
        ).delete()
        
        db.commit()
        return result > 0
    
    def clear_model(self, db: Session, model: str) -> int:
        """
        Clear all cache entries for a model.
        
        Args:
            db: Database session
            model: Model name
            
        Returns:
            Number of entries deleted
        """
        result = db.query(VectorCache).filter(
            VectorCache.model == model
        ).delete()
        
        db.commit()
        self._stats.eviction_count += result
        return result
    
    def clear_all(self, db: Session) -> int:
        """
        Clear all cache entries.
        
        Args:
            db: Database session
            
        Returns:
            Number of entries deleted
        """
        result = db.query(VectorCache).delete()
        db.commit()
        self._stats = CacheStats()
        return result
    
    def get_stats(self, db: Session) -> CacheStats:
        """
        Get cache statistics.
        
        Args:
            db: Database session
            
        Returns:
            CacheStats with current statistics
        """
        # Update total entries
        self._stats.total_entries = db.query(func.count(VectorCache.cache_key)).scalar() or 0
        
        # Calculate total size (approximate)
        total_size = db.query(func.sum(VectorCache.dimension * 8)).scalar() or 0  # 8 bytes per double
        self._stats.total_size_bytes = int(total_size)
        
        return self._stats
    
    def _evict_if_needed(self, db: Session) -> int:
        """
        Evict entries if cache is full.
        
        Uses LRU strategy based on last_accessed_at.
        
        Returns:
            Number of entries evicted
        """
        current_count = db.query(func.count(VectorCache.cache_key)).scalar() or 0
        
        if current_count < self.max_entries:
            return 0
        
        # Calculate how many to evict (10% buffer)
        to_evict = int(self.max_entries * 0.1)
        
        # Find oldest accessed entries
        oldest = db.query(VectorCache).order_by(
            VectorCache.last_accessed_at.asc()
        ).limit(to_evict).all()
        
        for entry in oldest:
            db.delete(entry)
        
        db.commit()
        
        self._stats.eviction_count += len(oldest)
        return len(oldest)
    
    def _is_expired(self, entry: VectorCache) -> bool:
        """Check if cache entry is expired."""
        if not entry.created_at:
            return False
        
        age = datetime.utcnow() - entry.created_at
        return age > self.ttl
    
    def cleanup_expired(self, db: Session) -> int:
        """
        Remove expired cache entries.
        
        Args:
            db: Database session
            
        Returns:
            Number of entries removed
        """
        cutoff = datetime.utcnow() - self.ttl
        
        result = db.query(VectorCache).filter(
            VectorCache.created_at < cutoff
        ).delete()
        
        db.commit()
        self._stats.eviction_count += result
        return result


# Global instance
_default_service = None


def get_vector_cache_service(
    max_entries: int = 10000,
    ttl_hours: int = 24 * 7,
) -> VectorCacheService:
    """Get default vector cache service instance."""
    global _default_service
    if _default_service is None:
        _default_service = VectorCacheService(max_entries, ttl_hours)
    return _default_service
