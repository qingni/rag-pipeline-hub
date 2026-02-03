"""
Embedding cache management API.

Provides endpoints for:
- Cache statistics query
- Cache invalidation
- Cache configuration
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field

from ..services.embedding_cache_service import (
    EmbeddingCacheService,
    get_embedding_cache_service,
)


router = APIRouter(prefix="/embedding/cache", tags=["Embedding Cache"])


# ============================================================================
# Request/Response Models
# ============================================================================

class CacheStatsResponse(BaseModel):
    """Cache statistics response."""
    total_entries: int
    total_size_bytes: int
    total_size_mb: float
    hit_count: int
    miss_count: int
    hit_rate: float
    hit_rate_percent: str
    eviction_count: int


class InvalidateCacheRequest(BaseModel):
    """Request to invalidate cache entries."""
    model_name: Optional[str] = Field(None, description="Model to invalidate cache for")
    content: Optional[str] = Field(None, description="Specific content to invalidate")


class InvalidateCacheResponse(BaseModel):
    """Response for cache invalidation."""
    success: bool
    entries_removed: int
    message: str


# ============================================================================
# Dependency Injection
# ============================================================================

def get_cache_service() -> EmbeddingCacheService:
    """Get cache service."""
    return get_embedding_cache_service()


# ============================================================================
# API Endpoints
# ============================================================================

@router.get("/stats")
async def get_cache_stats(
    service: EmbeddingCacheService = Depends(get_cache_service),
) -> CacheStatsResponse:
    """
    Get cache statistics.
    
    Returns current cache metrics including:
    - Total entries
    - Memory usage
    - Hit/miss rates
    - Eviction count
    """
    try:
        stats = service.get_stats()
        return CacheStatsResponse(
            total_entries=stats['total_entries'],
            total_size_bytes=stats['total_size_bytes'],
            total_size_mb=stats['total_size_bytes'] / (1024 * 1024),
            hit_count=stats['hit_count'],
            miss_count=stats['miss_count'],
            hit_rate=stats['hit_rate'],
            hit_rate_percent=stats['hit_rate_percent'],
            eviction_count=stats['eviction_count'],
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get cache stats: {str(e)}"
        )


@router.post("/invalidate")
async def invalidate_cache(
    request: InvalidateCacheRequest,
    service: EmbeddingCacheService = Depends(get_cache_service),
) -> InvalidateCacheResponse:
    """
    Invalidate cache entries.
    
    Can invalidate:
    - All entries for a specific model
    - Specific content entry
    - All entries (if neither specified)
    """
    try:
        entries_removed = 0
        
        if request.content and request.model_name:
            # Invalidate specific content for model
            if service.invalidate_for_content(request.content, request.model_name):
                entries_removed = 1
            message = f"Invalidated cache for specific content with model {request.model_name}"
            
        elif request.model_name:
            # Invalidate all entries for model
            entries_removed = service.invalidate_for_model(request.model_name)
            message = f"Invalidated all cache entries for model {request.model_name}"
            
        elif request.content:
            raise HTTPException(
                status_code=400,
                detail="model_name is required when invalidating by content"
            )
        else:
            # Clear all cache
            entries_removed = service.clear_all()
            message = "Cleared all cache entries"
        
        return InvalidateCacheResponse(
            success=True,
            entries_removed=entries_removed,
            message=message,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to invalidate cache: {str(e)}"
        )


@router.delete("/clear")
async def clear_all_cache(
    confirm: bool = Query(
        default=False,
        description="Confirm clearing all cache entries"
    ),
    service: EmbeddingCacheService = Depends(get_cache_service),
) -> InvalidateCacheResponse:
    """
    Clear all cache entries.
    
    Requires confirmation flag to prevent accidental clearing.
    """
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="Please confirm clearing by setting confirm=true"
        )
    
    try:
        entries_removed = service.clear_all()
        return InvalidateCacheResponse(
            success=True,
            entries_removed=entries_removed,
            message=f"Cleared {entries_removed} cache entries",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear cache: {str(e)}"
        )


@router.get("/health")
async def cache_health_check(
    service: EmbeddingCacheService = Depends(get_cache_service),
):
    """
    Check cache health status.
    
    Returns basic health metrics and status.
    """
    try:
        stats = service.get_stats()
        
        # Determine health status
        hit_rate = stats['hit_rate']
        if hit_rate >= 0.8:
            status = "healthy"
            level = "good"
        elif hit_rate >= 0.5:
            status = "healthy"
            level = "moderate"
        elif stats['total_entries'] < 100:
            status = "warming"
            level = "warming"
        else:
            status = "unhealthy"
            level = "poor"
        
        return {
            "status": status,
            "level": level,
            "hit_rate": hit_rate,
            "hit_rate_percent": stats['hit_rate_percent'],
            "total_entries": stats['total_entries'],
            "recommendations": _get_recommendations(stats, level),
        }
    except Exception as e:
        return {
            "status": "error",
            "level": "error",
            "error": str(e),
        }


def _get_recommendations(stats: dict, level: str) -> list:
    """Generate cache optimization recommendations."""
    recommendations = []
    
    if level == "warming":
        recommendations.append("缓存正在预热中，命中率会逐步提高")
    
    if level == "poor" and stats['hit_rate'] < 0.5:
        recommendations.append("建议检查缓存配置或增加缓存容量")
    
    if stats['eviction_count'] > stats['hit_count']:
        recommendations.append("缓存淘汰频繁，建议增加缓存容量")
    
    if stats['total_entries'] == 0:
        recommendations.append("缓存为空，首次使用会填充缓存")
    
    return recommendations
