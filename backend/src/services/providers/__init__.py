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

try:
    from .faiss_provider import FAISSProvider
    FAISS_AVAILABLE = True
except ImportError as e:
    FAISSProvider = None
    FAISS_AVAILABLE = False
    print(f"Warning: FAISS provider not available: {e}")

__all__ = [
    "BaseProvider",
    "IndexConfig",
    "SearchResult",
    "MilvusProvider",
    "FAISSProvider",
    "MILVUS_AVAILABLE",
    "FAISS_AVAILABLE",
]
