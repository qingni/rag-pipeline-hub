"""
Base Provider Interface

This module defines the abstract base class for vector index providers.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import numpy as np


@dataclass
class IndexConfig:
    """索引配置"""
    index_name: str
    dimension: int
    metric_type: str = "cosine"
    index_type: Optional[str] = None
    num_vectors: int = 0  # 预期向量数量，用于动态调整索引参数
    enable_sparse: bool = False  # 是否启用稀疏向量字段（用于混合检索）


@dataclass
class SearchResult:
    """搜索结果"""
    vector_id: str
    score: float
    metadata: Dict[str, Any]


class BaseProvider(ABC):
    """
    Abstract base class for vector index providers
    
    All provider implementations (Milvus) must inherit from this class
    and implement all abstract methods.
    """
    
    def __init__(self, index_name: str, dimension: int, metric_type: str, **kwargs):
        """
        Initialize provider
        
        Args:
            index_name: Name of the index
            dimension: Vector dimension
            metric_type: Similarity metric ("cosine", "euclidean", "dot_product")
            **kwargs: Provider-specific parameters
        """
        self.index_name = index_name
        self.dimension = dimension
        self.metric_type = metric_type
        self.config = kwargs
    
    @abstractmethod
    def create_index(self, index_type: str, index_params: Dict[str, Any]) -> bool:
        """
        Create a new index
        
        Args:
            index_type: Index algorithm type
            index_params: Index-specific parameters
            
        Returns:
            True if successful
            
        Raises:
            Exception: If index creation fails
        """
        pass
    
    @abstractmethod
    def insert_vectors(
        self,
        vectors: np.ndarray,
        vector_ids: List[str],
        metadata: Optional[List[Dict[str, Any]]] = None
    ) -> bool:
        """
        Insert vectors into the index
        
        Args:
            vectors: Vector data (2D numpy array)
            vector_ids: List of vector IDs
            metadata: Optional metadata for each vector
            
        Returns:
            True if successful
            
        Raises:
            Exception: If insertion fails
        """
        pass
    
    @abstractmethod
    def search_vectors(
        self,
        query_vector: np.ndarray,
        top_k: int = 5,
        threshold: Optional[float] = None,
        filter_expr: Optional[str] = None,
        **search_params
    ) -> List[Dict[str, Any]]:
        """
        Search for similar vectors
        
        Args:
            query_vector: Query vector (1D numpy array)
            top_k: Number of results to return
            threshold: Minimum similarity threshold
            filter_expr: Optional filter expression
            **search_params: Provider-specific search parameters
            
        Returns:
            List of search results with format:
            [
                {
                    "vector_id": str,
                    "score": float,
                    "distance": float,
                    "metadata": dict
                },
                ...
            ]
            
        Raises:
            Exception: If search fails
        """
        pass
    
    @abstractmethod
    def delete_vectors(self, vector_ids: List[str]) -> bool:
        """
        Delete vectors from the index
        
        Args:
            vector_ids: List of vector IDs to delete
            
        Returns:
            True if successful
            
        Raises:
            Exception: If deletion fails
        """
        pass
    
    @abstractmethod
    def get_vector_count(self) -> int:
        """
        Get the total number of vectors in the index
        
        Returns:
            Vector count
        """
        pass
    
    @abstractmethod
    def persist_index(self) -> bool:
        """
        Persist the index to storage
        
        Returns:
            True if successful
            
        Raises:
            Exception: If persistence fails
        """
        pass
    
    @abstractmethod
    def load_index(self) -> bool:
        """
        Load the index from storage
        
        Returns:
            True if successful
            
        Raises:
            Exception: If loading fails
        """
        pass
    
    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """
        Check provider health status
        
        Returns:
            Dictionary with health information:
            {
                "status": "healthy" | "degraded" | "unhealthy",
                "details": {...}
            }
        """
        pass
    
    @abstractmethod
    def get_index_stats(self) -> Dict[str, Any]:
        """
        Get index statistics
        
        Returns:
            Dictionary with statistics:
            {
                "vector_count": int,
                "index_size_bytes": int,
                "...": ...
            }
        """
        pass
    
    def batch_search(
        self,
        query_vectors: np.ndarray,
        top_k: int = 5,
        **search_params
    ) -> List[List[Dict[str, Any]]]:
        """
        Batch search for multiple query vectors
        
        Default implementation calls search_vectors for each query.
        Providers can override for optimized batch processing.
        
        Args:
            query_vectors: Multiple query vectors (2D numpy array)
            top_k: Number of results per query
            **search_params: Provider-specific search parameters
            
        Returns:
            List of result lists (one per query)
        """
        results = []
        for query_vector in query_vectors:
            result = self.search_vectors(query_vector, top_k, **search_params)
            results.append(result)
        return results
    
    def hybrid_search(
        self,
        dense_vector: np.ndarray,
        sparse_vector: Optional[Dict] = None,
        top_n: int = 20,
        rrf_k: int = 60,
        output_fields: Optional[List[str]] = None,
        **search_params
    ) -> List[Dict[str, Any]]:
        """
        Hybrid search using dense + sparse vectors with RRF fusion
        
        Default implementation: falls back to dense-only search.
        Providers supporting hybrid search should override this method.
        
        Args:
            dense_vector: Dense query vector (1D numpy array)
            sparse_vector: Sparse query vector ({index: weight} dict), optional
            top_n: Number of candidates for coarse ranking (RRF output)
            rrf_k: RRF smoothing parameter
            output_fields: Fields to return
            **search_params: Provider-specific search parameters
            
        Returns:
            List of search results with rrf_score
        """
        # 默认降级到纯稠密检索
        results = self.search_vectors(dense_vector, top_n, **search_params)
        # 添加 search_mode 标记
        for r in results:
            r["search_mode"] = "dense_only"
            r["rrf_score"] = r.get("score", 0)
        return results
    
    def update_vectors(
        self,
        vectors: np.ndarray,
        vector_ids: List[str],
        metadata: Optional[List[Dict[str, Any]]] = None
    ) -> bool:
        """
        Update existing vectors
        
        Default implementation: delete then insert.
        Providers can override for optimized update operations.
        
        Args:
            vectors: New vector data
            vector_ids: Vector IDs to update
            metadata: Optional new metadata
            
        Returns:
            True if successful
        """
        self.delete_vectors(vector_ids)
        return self.insert_vectors(vectors, vector_ids, metadata)
    
    def close(self):
        """
        Close connections and cleanup resources
        
        Optional method for resource cleanup.
        """
        pass
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
        return False
