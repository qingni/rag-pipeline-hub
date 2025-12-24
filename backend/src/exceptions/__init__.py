"""
Custom Exceptions Package for Vector Index Module
"""

from .vector_index_errors import (
    VectorIndexError,
    IndexNotFoundError,
    IndexAlreadyExistsError,
    IndexNotReadyError,
    VectorDimensionMismatchError,
    InvalidVectorError,
    ProviderError,
    MilvusConnectionError,
    MilvusOperationError,
    FAISSError,
    IndexPersistenceError,
    IndexLoadError,
    SearchError,
    InsertError,
    DeleteError,
    ConfigurationError,
    BatchSizeExceededError,
    QueryTimeoutError
)

__all__ = [
    "VectorIndexError",
    "IndexNotFoundError",
    "IndexAlreadyExistsError",
    "IndexNotReadyError",
    "VectorDimensionMismatchError",
    "InvalidVectorError",
    "ProviderError",
    "MilvusConnectionError",
    "MilvusOperationError",
    "FAISSError",
    "IndexPersistenceError",
    "IndexLoadError",
    "SearchError",
    "InsertError",
    "DeleteError",
    "ConfigurationError",
    "BatchSizeExceededError",
    "QueryTimeoutError",
]
