"""
Cached embedder wrapper.

Wraps embedding service with caching layer:
- Content hash-based lookup
- Automatic cache population
- Cache statistics
"""
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
import time

from ..services.embedding_cache_service import (
    EmbeddingCacheService,
    get_embedding_cache_service,
)


@dataclass
class CachedEmbeddingStats:
    """Statistics for cached embedding operation."""
    total_requests: int
    cache_hits: int
    cache_misses: int
    hit_rate: float
    compute_time_saved_ms: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'total_requests': self.total_requests,
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'hit_rate': self.hit_rate,
            'hit_rate_percent': f'{self.hit_rate * 100:.1f}%',
            'compute_time_saved_ms': self.compute_time_saved_ms,
        }


class CachedEmbedder:
    """
    Cached embedding wrapper.
    
    Wraps any embedding service/function with caching layer.
    Uses content hash to identify cached vectors.
    """
    
    def __init__(
        self,
        cache_service: Optional[EmbeddingCacheService] = None,
        model_name: str = 'default',
        avg_embedding_time_ms: float = 100.0,  # Estimated time per embedding
    ):
        """
        Initialize cached embedder.
        
        Args:
            cache_service: Cache service instance
            model_name: Model name for cache key
            avg_embedding_time_ms: Estimated time per embedding (for stats)
        """
        self.cache_service = cache_service or get_embedding_cache_service()
        self.model_name = model_name
        self.avg_embedding_time_ms = avg_embedding_time_ms
        
        # Session stats
        self._session_hits = 0
        self._session_misses = 0
    
    def get_cached_or_compute(
        self,
        content: str,
        compute_func,
    ) -> tuple[List[float], bool]:
        """
        Get vector from cache or compute using provided function.
        
        Args:
            content: Text content to embed
            compute_func: Function to compute embedding if not cached
            
        Returns:
            Tuple of (vector, was_cached)
        """
        # Try cache first
        cached_vector = self.cache_service.get_cached_vector(content, self.model_name)
        if cached_vector is not None:
            self._session_hits += 1
            return cached_vector, True
        
        # Compute embedding
        self._session_misses += 1
        vector = compute_func(content)
        
        # Cache the result
        self.cache_service.cache_vector(content, vector, self.model_name)
        
        return vector, False
    
    def get_cached_batch_or_compute(
        self,
        contents: List[str],
        batch_compute_func,
    ) -> tuple[List[List[float]], CachedEmbeddingStats]:
        """
        Get vectors from cache or compute using provided batch function.
        
        Args:
            contents: List of text contents to embed
            batch_compute_func: Function to compute embeddings for list of contents
            
        Returns:
            Tuple of (vectors in same order as contents, stats)
        """
        start_time = time.time()
        
        # Check cache for all contents
        cached_vectors, missing_indices = self.cache_service.get_cached_batch(
            contents, self.model_name
        )
        
        cache_hits = len(cached_vectors)
        cache_misses = len(missing_indices)
        
        self._session_hits += cache_hits
        self._session_misses += cache_misses
        
        # Compute missing embeddings
        computed_vectors = {}
        if missing_indices:
            # Get contents to compute
            contents_to_compute = [contents[i] for i in missing_indices]
            
            # Batch compute
            new_vectors = batch_compute_func(contents_to_compute)
            
            # Map results back to indices and cache
            items_to_cache = []
            for i, idx in enumerate(missing_indices):
                computed_vectors[idx] = new_vectors[i]
                items_to_cache.append((contents[idx], new_vectors[i]))
            
            # Cache all computed vectors
            self.cache_service.cache_batch(items_to_cache, self.model_name)
        
        # Merge cached and computed vectors in original order
        result_vectors = []
        for i in range(len(contents)):
            if i in cached_vectors:
                result_vectors.append(cached_vectors[i])
            elif i in computed_vectors:
                result_vectors.append(computed_vectors[i])
            else:
                # This shouldn't happen
                result_vectors.append([])
        
        # Calculate stats
        total_requests = len(contents)
        hit_rate = cache_hits / total_requests if total_requests > 0 else 0.0
        compute_time_saved = cache_hits * self.avg_embedding_time_ms
        
        stats = CachedEmbeddingStats(
            total_requests=total_requests,
            cache_hits=cache_hits,
            cache_misses=cache_misses,
            hit_rate=hit_rate,
            compute_time_saved_ms=compute_time_saved,
        )
        
        return result_vectors, stats
    
    def get_session_stats(self) -> CachedEmbeddingStats:
        """Get statistics for current session."""
        total = self._session_hits + self._session_misses
        hit_rate = self._session_hits / total if total > 0 else 0.0
        
        return CachedEmbeddingStats(
            total_requests=total,
            cache_hits=self._session_hits,
            cache_misses=self._session_misses,
            hit_rate=hit_rate,
            compute_time_saved_ms=self._session_hits * self.avg_embedding_time_ms,
        )
    
    def reset_session_stats(self) -> None:
        """Reset session statistics."""
        self._session_hits = 0
        self._session_misses = 0
    
    def invalidate_cache(self, content: Optional[str] = None) -> bool:
        """
        Invalidate cache entries.
        
        Args:
            content: Specific content to invalidate, or None to invalidate all
            
        Returns:
            True if operation successful
        """
        if content:
            return self.cache_service.invalidate_for_content(content, self.model_name)
        else:
            self.cache_service.invalidate_for_model(self.model_name)
            return True


def cached_embedding(model_name: str = 'default'):
    """
    Decorator for caching embedding function results.
    
    Usage:
        @cached_embedding(model_name='bge-m3')
        def embed_text(text: str) -> List[float]:
            return embedding_service.embed_query(text)
    """
    cache_service = get_embedding_cache_service()
    
    def decorator(func):
        def wrapper(content: str, *args, **kwargs):
            # Try cache first
            cached = cache_service.get_cached_vector(content, model_name)
            if cached is not None:
                return cached
            
            # Compute and cache
            vector = func(content, *args, **kwargs)
            cache_service.cache_vector(content, vector, model_name)
            return vector
        
        return wrapper
    return decorator
