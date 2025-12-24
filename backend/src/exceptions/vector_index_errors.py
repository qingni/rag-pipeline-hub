"""
Vector Index Custom Exceptions

This module defines custom exception classes for vector index operations.
"""


class VectorIndexError(Exception):
    """Base exception for all vector index errors"""
    
    def __init__(self, message: str, details: dict = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> dict:
        """Convert exception to dictionary format"""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "details": self.details
        }


class IndexNotFoundError(VectorIndexError):
    """Raised when an index does not exist"""
    
    def __init__(self, index_name: str):
        super().__init__(
            f"Index '{index_name}' not found",
            {"index_name": index_name}
        )


class IndexAlreadyExistsError(VectorIndexError):
    """Raised when trying to create an index that already exists"""
    
    def __init__(self, index_name: str):
        super().__init__(
            f"Index '{index_name}' already exists",
            {"index_name": index_name}
        )


class IndexNotReadyError(VectorIndexError):
    """Raised when trying to query an index that is not ready"""
    
    def __init__(self, index_name: str, status: str):
        super().__init__(
            f"Index '{index_name}' is not ready (status: {status})",
            {"index_name": index_name, "status": status}
        )


class VectorDimensionMismatchError(VectorIndexError):
    """Raised when vector dimension doesn't match index dimension"""
    
    def __init__(self, expected: int, actual: int):
        super().__init__(
            f"Vector dimension mismatch: expected {expected}, got {actual}",
            {"expected_dim": expected, "actual_dim": actual}
        )


class InvalidVectorError(VectorIndexError):
    """Raised when a vector contains invalid values"""
    
    def __init__(self, reason: str):
        super().__init__(
            f"Invalid vector: {reason}",
            {"reason": reason}
        )


class ProviderError(VectorIndexError):
    """Base exception for provider-specific errors"""
    
    def __init__(self, provider: str, message: str, details: dict = None):
        details = details or {}
        details["provider"] = provider
        super().__init__(message, details)


class MilvusConnectionError(ProviderError):
    """Raised when Milvus connection fails"""
    
    def __init__(self, message: str, host: str = None, port: int = None):
        details = {}
        if host:
            details["host"] = host
        if port:
            details["port"] = port
        super().__init__("milvus", f"Milvus connection error: {message}", details)


class MilvusOperationError(ProviderError):
    """Raised when a Milvus operation fails"""
    
    def __init__(self, operation: str, message: str):
        super().__init__(
            "milvus",
            f"Milvus {operation} failed: {message}",
            {"operation": operation}
        )


class FAISSError(ProviderError):
    """Raised when a FAISS operation fails"""
    
    def __init__(self, operation: str, message: str):
        super().__init__(
            "faiss",
            f"FAISS {operation} failed: {message}",
            {"operation": operation}
        )


class IndexPersistenceError(VectorIndexError):
    """Raised when index persistence fails"""
    
    def __init__(self, index_name: str, reason: str):
        super().__init__(
            f"Failed to persist index '{index_name}': {reason}",
            {"index_name": index_name, "reason": reason}
        )


class IndexLoadError(VectorIndexError):
    """Raised when index loading fails"""
    
    def __init__(self, index_name: str, reason: str):
        super().__init__(
            f"Failed to load index '{index_name}': {reason}",
            {"index_name": index_name, "reason": reason}
        )


class SearchError(VectorIndexError):
    """Raised when vector search fails"""
    
    def __init__(self, index_name: str, reason: str):
        super().__init__(
            f"Search failed on index '{index_name}': {reason}",
            {"index_name": index_name, "reason": reason}
        )


class InsertError(VectorIndexError):
    """Raised when vector insertion fails"""
    
    def __init__(self, index_name: str, vector_count: int, reason: str):
        super().__init__(
            f"Failed to insert {vector_count} vectors into '{index_name}': {reason}",
            {"index_name": index_name, "vector_count": vector_count, "reason": reason}
        )


class DeleteError(VectorIndexError):
    """Raised when vector deletion fails"""
    
    def __init__(self, index_name: str, vector_ids: list, reason: str):
        super().__init__(
            f"Failed to delete vectors from '{index_name}': {reason}",
            {"index_name": index_name, "vector_count": len(vector_ids), "reason": reason}
        )


class ConfigurationError(VectorIndexError):
    """Raised when configuration is invalid"""
    
    def __init__(self, config_key: str, reason: str):
        super().__init__(
            f"Invalid configuration for '{config_key}': {reason}",
            {"config_key": config_key, "reason": reason}
        )


class BatchSizeExceededError(VectorIndexError):
    """Raised when batch size exceeds limit"""
    
    def __init__(self, actual_size: int, max_size: int):
        super().__init__(
            f"Batch size {actual_size} exceeds maximum {max_size}",
            {"actual_size": actual_size, "max_size": max_size}
        )


class QueryTimeoutError(VectorIndexError):
    """Raised when a query times out"""
    
    def __init__(self, index_name: str, timeout_seconds: float):
        super().__init__(
            f"Query on '{index_name}' timed out after {timeout_seconds}s",
            {"index_name": index_name, "timeout_seconds": timeout_seconds}
        )


class IndexBuildError(VectorIndexError):
    """Raised when index building fails"""
    
    def __init__(self, message: str):
        super().__init__(message)


class ProviderNotFoundError(VectorIndexError):
    """Raised when a provider is not found"""
    
    def __init__(self, provider_name: str):
        super().__init__(
            f"Provider '{provider_name}' not found or not available",
            {"provider_name": provider_name}
        )


# Aliases for compatibility
VectorDimensionError = VectorDimensionMismatchError
