"""
Embedding cache service.

Provides vector caching with:
- LRU eviction policy
- Optional Redis backend
- Content hash-based lookup
- Hit rate statistics
"""
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from collections import OrderedDict
import time
import threading
import hashlib


@dataclass
class CacheEntry:
    """Single cache entry."""
    content_hash: str
    vector: List[float]
    model_name: str
    dimension: int
    created_at: float
    last_accessed: float
    access_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'content_hash': self.content_hash,
            'vector': self.vector,
            'model_name': self.model_name,
            'dimension': self.dimension,
            'created_at': self.created_at,
            'last_accessed': self.last_accessed,
            'access_count': self.access_count,
        }


@dataclass
class CacheStats:
    """Cache statistics."""
    total_entries: int = 0
    total_size_bytes: int = 0
    hit_count: int = 0
    miss_count: int = 0
    eviction_count: int = 0
    
    @property
    def hit_rate(self) -> float:
        total = self.hit_count + self.miss_count
        if total == 0:
            return 0.0
        return self.hit_count / total
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'total_entries': self.total_entries,
            'total_size_bytes': self.total_size_bytes,
            'hit_count': self.hit_count,
            'miss_count': self.miss_count,
            'eviction_count': self.eviction_count,
            'hit_rate': self.hit_rate,
            'hit_rate_percent': f"{self.hit_rate * 100:.1f}%",
        }


class LRUVectorCache:
    """
    LRU-based vector cache.
    
    Stores vectors with automatic eviction when capacity is reached.
    Thread-safe for concurrent access.
    """
    
    def __init__(
        self,
        max_entries: int = 10000,
        max_memory_mb: int = 500,
    ):
        """
        Initialize cache.
        
        Args:
            max_entries: Maximum number of cached vectors
            max_memory_mb: Maximum memory usage in MB
        """
        self.max_entries = max_entries
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()
        self._stats = CacheStats()
        self._current_size = 0
    
    def get(
        self,
        content_hash: str,
        model_name: str,
    ) -> Optional[List[float]]:
        """
        Get vector from cache.
        
        Args:
            content_hash: Content hash key
            model_name: Model name (part of key)
            
        Returns:
            Vector if found, None otherwise
        """
        key = self._make_key(content_hash, model_name)
        
        with self._lock:
            if key not in self._cache:
                self._stats.miss_count += 1
                return None
            
            # Move to end (most recently used)
            entry = self._cache.pop(key)
            entry.last_accessed = time.time()
            entry.access_count += 1
            self._cache[key] = entry
            
            self._stats.hit_count += 1
            return entry.vector
    
    def put(
        self,
        content_hash: str,
        vector: List[float],
        model_name: str,
    ) -> bool:
        """
        Put vector into cache.
        
        Args:
            content_hash: Content hash key
            vector: Vector to cache
            model_name: Model name
            
        Returns:
            True if cached successfully
        """
        key = self._make_key(content_hash, model_name)
        entry_size = self._estimate_size(vector)
        
        with self._lock:
            # Check if already exists
            if key in self._cache:
                # Update existing entry
                old_entry = self._cache.pop(key)
                self._current_size -= self._estimate_size(old_entry.vector)
            
            # Evict if necessary
            while (
                (len(self._cache) >= self.max_entries or
                 self._current_size + entry_size > self.max_memory_bytes)
                and self._cache
            ):
                self._evict_oldest()
            
            # Create new entry
            now = time.time()
            entry = CacheEntry(
                content_hash=content_hash,
                vector=vector,
                model_name=model_name,
                dimension=len(vector),
                created_at=now,
                last_accessed=now,
                access_count=0,
            )
            
            self._cache[key] = entry
            self._current_size += entry_size
            self._stats.total_entries = len(self._cache)
            self._stats.total_size_bytes = self._current_size
            
            return True
    
    def get_batch(
        self,
        content_hashes: List[str],
        model_name: str,
    ) -> Tuple[Dict[str, List[float]], List[str]]:
        """
        Get multiple vectors from cache.
        
        Args:
            content_hashes: List of content hashes
            model_name: Model name
            
        Returns:
            Tuple of (found_vectors dict, missing_hashes list)
        """
        found = {}
        missing = []
        
        for content_hash in content_hashes:
            vector = self.get(content_hash, model_name)
            if vector is not None:
                found[content_hash] = vector
            else:
                missing.append(content_hash)
        
        return found, missing
    
    def put_batch(
        self,
        entries: List[Dict[str, Any]],
        model_name: str,
    ) -> int:
        """
        Put multiple vectors into cache.
        
        Args:
            entries: List of dicts with 'content_hash', 'vector'
            model_name: Model name
            
        Returns:
            Number of entries cached
        """
        cached_count = 0
        for entry in entries:
            if self.put(
                content_hash=entry.get('content_hash', ''),
                vector=entry.get('vector', []),
                model_name=model_name,
            ):
                cached_count += 1
        return cached_count
    
    def invalidate(
        self,
        content_hash: str,
        model_name: str,
    ) -> bool:
        """
        Remove entry from cache.
        
        Args:
            content_hash: Content hash key
            model_name: Model name
            
        Returns:
            True if entry was removed
        """
        key = self._make_key(content_hash, model_name)
        
        with self._lock:
            if key in self._cache:
                entry = self._cache.pop(key)
                self._current_size -= self._estimate_size(entry.vector)
                self._stats.total_entries = len(self._cache)
                self._stats.total_size_bytes = self._current_size
                return True
            return False
    
    def invalidate_model(self, model_name: str) -> int:
        """
        Remove all entries for a specific model.
        
        Args:
            model_name: Model name
            
        Returns:
            Number of entries removed
        """
        removed = 0
        with self._lock:
            keys_to_remove = [
                k for k in self._cache.keys()
                if k.endswith(f":{model_name}")
            ]
            for key in keys_to_remove:
                entry = self._cache.pop(key)
                self._current_size -= self._estimate_size(entry.vector)
                removed += 1
            
            self._stats.total_entries = len(self._cache)
            self._stats.total_size_bytes = self._current_size
        
        return removed
    
    def clear(self) -> int:
        """
        Clear all cache entries.
        
        Returns:
            Number of entries cleared
        """
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            self._current_size = 0
            self._stats = CacheStats()
            return count
    
    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        with self._lock:
            return CacheStats(
                total_entries=self._stats.total_entries,
                total_size_bytes=self._stats.total_size_bytes,
                hit_count=self._stats.hit_count,
                miss_count=self._stats.miss_count,
                eviction_count=self._stats.eviction_count,
            )
    
    def _make_key(self, content_hash: str, model_name: str) -> str:
        """Create cache key from hash and model."""
        return f"{content_hash}:{model_name}"
    
    def _estimate_size(self, vector: List[float]) -> int:
        """Estimate memory size of vector in bytes."""
        # 8 bytes per float64 + overhead
        return len(vector) * 8 + 100
    
    def _evict_oldest(self) -> None:
        """Evict oldest (least recently used) entry."""
        if not self._cache:
            return
        
        # OrderedDict: first item is oldest
        key, entry = self._cache.popitem(last=False)
        self._current_size -= self._estimate_size(entry.vector)
        self._stats.eviction_count += 1


class EmbeddingCacheService:
    """
    High-level embedding cache service.
    
    Wraps LRU cache with additional features:
    - Automatic content hashing
    - Model-specific caching
    - Batch operations
    """
    
    def __init__(
        self,
        cache: Optional[LRUVectorCache] = None,
        max_entries: int = 10000,
        max_memory_mb: int = 500,
    ):
        """
        Initialize service.
        
        Args:
            cache: Optional pre-configured cache
            max_entries: Maximum cache entries
            max_memory_mb: Maximum memory in MB
        """
        self.cache = cache or LRUVectorCache(
            max_entries=max_entries,
            max_memory_mb=max_memory_mb,
        )
    
    def compute_content_hash(self, content: str) -> str:
        """Compute hash for content."""
        return "sha256:" + hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def get_cached_vector(
        self,
        content: str,
        model_name: str,
    ) -> Optional[List[float]]:
        """
        Get cached vector for content.
        
        Args:
            content: Text content
            model_name: Embedding model name
            
        Returns:
            Vector if cached, None otherwise
        """
        content_hash = self.compute_content_hash(content)
        return self.cache.get(content_hash, model_name)
    
    def cache_vector(
        self,
        content: str,
        vector: List[float],
        model_name: str,
    ) -> bool:
        """
        Cache vector for content.
        
        Args:
            content: Text content
            vector: Computed vector
            model_name: Embedding model name
            
        Returns:
            True if cached successfully
        """
        content_hash = self.compute_content_hash(content)
        return self.cache.put(content_hash, vector, model_name)
    
    def get_cached_batch(
        self,
        contents: List[str],
        model_name: str,
    ) -> Tuple[Dict[int, List[float]], List[int]]:
        """
        Get cached vectors for batch of contents.
        
        Args:
            contents: List of text contents
            model_name: Embedding model name
            
        Returns:
            Tuple of (found_vectors by index, missing_indices)
        """
        found = {}
        missing = []
        
        for i, content in enumerate(contents):
            vector = self.get_cached_vector(content, model_name)
            if vector is not None:
                found[i] = vector
            else:
                missing.append(i)
        
        return found, missing
    
    def cache_batch(
        self,
        items: List[Tuple[str, List[float]]],
        model_name: str,
    ) -> int:
        """
        Cache batch of content-vector pairs.
        
        Args:
            items: List of (content, vector) tuples
            model_name: Embedding model name
            
        Returns:
            Number of items cached
        """
        cached = 0
        for content, vector in items:
            if self.cache_vector(content, vector, model_name):
                cached += 1
        return cached
    
    def invalidate_for_content(
        self,
        content: str,
        model_name: str,
    ) -> bool:
        """Invalidate cache for specific content."""
        content_hash = self.compute_content_hash(content)
        return self.cache.invalidate(content_hash, model_name)
    
    def invalidate_for_model(self, model_name: str) -> int:
        """Invalidate all cache for a model."""
        return self.cache.invalidate_model(model_name)
    
    def clear_all(self) -> int:
        """Clear entire cache."""
        return self.cache.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return self.cache.get_stats().to_dict()


# Global instance
_default_service = None


def get_embedding_cache_service(
    max_entries: int = 10000,
    max_memory_mb: int = 500,
) -> EmbeddingCacheService:
    """Get default embedding cache service instance."""
    global _default_service
    if _default_service is None:
        _default_service = EmbeddingCacheService(
            max_entries=max_entries,
            max_memory_mb=max_memory_mb,
        )
    return _default_service
