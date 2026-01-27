"""
Utility Functions Package for Vector Index Module
"""

from .vector_utils import (
    validate_vector,
    normalize_vector,
    batch_normalize_vectors,
    compute_vector_norm,
    validate_vector_batch,
    convert_to_numpy,
    cosine_distance_to_similarity,
    euclidean_distance_to_similarity
)
from .similarity import (
    cosine_similarity,
    euclidean_distance,
    dot_product,
    manhattan_distance,
    batch_cosine_similarity,
    batch_euclidean_distance,
    convert_distance_to_similarity
)
from .result_persistence import (
    ResultPersistence,
    get_result_persistence,
    reset_result_persistence
)
from .logger import (
    setup_vector_index_logger,
    get_vector_index_logger
)
from .image_storage import (
    ImageStorageConfig,
    ImageStorageManager,
    get_image_storage_manager,
    process_image,
    process_base64_image,
)

__all__ = [
    # Vector utilities
    "validate_vector",
    "normalize_vector",
    "batch_normalize_vectors",
    "compute_vector_norm",
    "validate_vector_batch",
    "convert_to_numpy",
    "cosine_distance_to_similarity",
    "euclidean_distance_to_similarity",
    
    # Similarity metrics
    "cosine_similarity",
    "euclidean_distance",
    "dot_product",
    "manhattan_distance",
    "batch_cosine_similarity",
    "batch_euclidean_distance",
    "convert_distance_to_similarity",
    
    # Result persistence
    "ResultPersistence",
    "get_result_persistence",
    "reset_result_persistence",
    
    # Logging
    "setup_vector_index_logger",
    "get_vector_index_logger",
    
    # Image storage
    "ImageStorageConfig",
    "ImageStorageManager",
    "get_image_storage_manager",
    "process_image",
    "process_base64_image",
]
