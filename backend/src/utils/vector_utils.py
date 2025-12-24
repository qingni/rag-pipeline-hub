"""
Vector Utility Functions

This module provides utility functions for vector validation and normalization.
"""

import math
import numpy as np
from typing import List, Union


def validate_vector(
    vector: Union[List[float], np.ndarray],
    expected_dim: int,
    allow_zero: bool = False
) -> bool:
    """
    Validate vector data
    
    Args:
        vector: Vector to validate
        expected_dim: Expected vector dimension
        allow_zero: Allow zero vectors
        
    Returns:
        True if valid
        
    Raises:
        ValueError: If validation fails
    """
    # Convert to numpy array if needed
    if isinstance(vector, list):
        vector = np.array(vector, dtype=np.float32)
    
    # Check dimension
    if len(vector) != expected_dim:
        raise ValueError(
            f"Vector dimension mismatch: expected {expected_dim}, got {len(vector)}"
        )
    
    # Check for numeric values
    if not np.all(np.isfinite(vector)):
        raise ValueError("Vector contains NaN or Inf values")
    
    # Check for zero vector
    if not allow_zero:
        norm = np.linalg.norm(vector)
        if np.isclose(norm, 0.0, atol=1e-8):
            raise ValueError("Vector is zero (norm=0)")
    
    return True


def normalize_vector(vector: Union[List[float], np.ndarray]) -> np.ndarray:
    """
    Normalize vector to unit length (L2 normalization)
    
    Args:
        vector: Vector to normalize
        
    Returns:
        Normalized vector as numpy array
        
    Raises:
        ValueError: If vector is zero
    """
    if isinstance(vector, list):
        vector = np.array(vector, dtype=np.float32)
    
    norm = np.linalg.norm(vector)
    
    if np.isclose(norm, 0.0, atol=1e-8):
        raise ValueError("Cannot normalize zero vector")
    
    return vector / norm


def batch_normalize_vectors(vectors: Union[List[List[float]], np.ndarray]) -> np.ndarray:
    """
    Normalize a batch of vectors
    
    Args:
        vectors: Batch of vectors (2D array or list of lists)
        
    Returns:
        Normalized vectors as 2D numpy array
    """
    if isinstance(vectors, list):
        vectors = np.array(vectors, dtype=np.float32)
    
    # Compute norms
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    
    # Avoid division by zero
    norms = np.where(norms == 0, 1, norms)
    
    return vectors / norms


def compute_vector_norm(vector: Union[List[float], np.ndarray]) -> float:
    """
    Compute L2 norm of a vector
    
    Args:
        vector: Input vector
        
    Returns:
        L2 norm (length) of the vector
    """
    if isinstance(vector, list):
        vector = np.array(vector, dtype=np.float32)
    
    return float(np.linalg.norm(vector))


def validate_vector_batch(
    vectors: Union[List[List[float]], np.ndarray],
    expected_dim: int,
    max_batch_size: int = 10000
) -> bool:
    """
    Validate a batch of vectors
    
    Args:
        vectors: Batch of vectors
        expected_dim: Expected dimension
        max_batch_size: Maximum allowed batch size
        
    Returns:
        True if all vectors are valid
        
    Raises:
        ValueError: If validation fails
    """
    if isinstance(vectors, list):
        vectors = np.array(vectors, dtype=np.float32)
    
    # Check batch size
    if len(vectors) > max_batch_size:
        raise ValueError(
            f"Batch size {len(vectors)} exceeds maximum {max_batch_size}"
        )
    
    # Check shape
    if vectors.ndim != 2:
        raise ValueError(f"Expected 2D array, got {vectors.ndim}D")
    
    if vectors.shape[1] != expected_dim:
        raise ValueError(
            f"Vector dimension mismatch: expected {expected_dim}, got {vectors.shape[1]}"
        )
    
    # Check for invalid values
    if not np.all(np.isfinite(vectors)):
        raise ValueError("Batch contains NaN or Inf values")
    
    return True


def convert_to_numpy(
    vectors: Union[List[float], List[List[float]], np.ndarray]
) -> np.ndarray:
    """
    Convert vectors to numpy array with proper shape
    
    Args:
        vectors: Input vectors (1D or 2D)
        
    Returns:
        Numpy array (ensures float32 dtype)
    """
    if isinstance(vectors, np.ndarray):
        return vectors.astype(np.float32)
    
    arr = np.array(vectors, dtype=np.float32)
    
    # Ensure 2D shape for batch processing
    if arr.ndim == 1:
        arr = arr.reshape(1, -1)
    
    return arr


def cosine_distance_to_similarity(distance: float) -> float:
    """
    Convert cosine distance to cosine similarity
    
    For normalized vectors: similarity = 1 - distance
    
    Args:
        distance: Cosine distance (0 to 2)
        
    Returns:
        Cosine similarity (-1 to 1)
    """
    return 1.0 - distance


def euclidean_distance_to_similarity(distance: float, max_distance: float = 1.0) -> float:
    """
    Convert Euclidean distance to similarity score
    
    Args:
        distance: Euclidean distance
        max_distance: Maximum expected distance (for normalization)
        
    Returns:
        Similarity score (0 to 1)
    """
    return 1.0 / (1.0 + distance / max_distance)
