"""
Vector Index Providers Package
"""

from .base_provider import BaseProvider, IndexConfig, SearchResult

# Try to import providers, but don't fail if dependencies are missing
try:
    from .milvus_provider import MilvusProvider
    MILVUS_AVAILABLE = True
except ImportError as e:
    MilvusProvider = None
    MILVUS_AVAILABLE = False
    print(f"Warning: Milvus provider not available: {e}")

__all__ = [
    "BaseProvider",
    "IndexConfig",
    "SearchResult",
    "MilvusProvider",
    "MILVUS_AVAILABLE",
]
