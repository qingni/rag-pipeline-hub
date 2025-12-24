"""
Similarity Metrics Module

This module provides various similarity/distance computation functions.
"""

import numpy as np
from typing import Union, List


def cosine_similarity(
    vec1: Union[List[float], np.ndarray],
    vec2: Union[List[float], np.ndarray]
) -> float:
    """
    Compute cosine similarity between two vectors
    
    Formula: cos(θ) = (A·B) / (||A|| ||B||)
    Range: [-1, 1] where 1 = identical, -1 = opposite
    
    Args:
        vec1: First vector
        vec2: Second vector
        
    Returns:
        Cosine similarity score
    """
    if isinstance(vec1, list):
        vec1 = np.array(vec1, dtype=np.float32)
    if isinstance(vec2, list):
        vec2 = np.array(vec2, dtype=np.float32)
    
    # Compute dot product
    dot_product = np.dot(vec1, vec2)
    
    # Compute norms
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    
    # Avoid division by zero
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    return float(dot_product / (norm1 * norm2))


def euclidean_distance(
    vec1: Union[List[float], np.ndarray],
    vec2: Union[List[float], np.ndarray]
) -> float:
    """
    Compute Euclidean (L2) distance between two vectors
    
    Formula: d = sqrt(sum((A[i] - B[i])^2))
    Range: [0, ∞) where 0 = identical
    
    Args:
        vec1: First vector
        vec2: Second vector
        
    Returns:
        Euclidean distance
    """
    if isinstance(vec1, list):
        vec1 = np.array(vec1, dtype=np.float32)
    if isinstance(vec2, list):
        vec2 = np.array(vec2, dtype=np.float32)
    
    return float(np.linalg.norm(vec1 - vec2))


def dot_product(
    vec1: Union[List[float], np.ndarray],
    vec2: Union[List[float], np.ndarray]
) -> float:
    """
    Compute dot product (inner product) between two vectors
    
    Formula: A·B = sum(A[i] * B[i])
    Range: (-∞, ∞)
    
    For normalized vectors, this equals cosine similarity.
    
    Args:
        vec1: First vector
        vec2: Second vector
        
    Returns:
        Dot product value
    """
    if isinstance(vec1, list):
        vec1 = np.array(vec1, dtype=np.float32)
    if isinstance(vec2, list):
        vec2 = np.array(vec2, dtype=np.float32)
    
    return float(np.dot(vec1, vec2))


def manhattan_distance(
    vec1: Union[List[float], np.ndarray],
    vec2: Union[List[float], np.ndarray]
) -> float:
    """
    Compute Manhattan (L1) distance between two vectors
    
    Formula: d = sum(|A[i] - B[i]|)
    Range: [0, ∞) where 0 = identical
    
    Args:
        vec1: First vector
        vec2: Second vector
        
    Returns:
        Manhattan distance
    """
    if isinstance(vec1, list):
        vec1 = np.array(vec1, dtype=np.float32)
    if isinstance(vec2, list):
        vec2 = np.array(vec2, dtype=np.float32)
    
    return float(np.sum(np.abs(vec1 - vec2)))


def batch_cosine_similarity(
    query_vector: Union[List[float], np.ndarray],
    vectors: Union[List[List[float]], np.ndarray]
) -> np.ndarray:
    """
    Compute cosine similarity between a query vector and multiple vectors
    
    Args:
        query_vector: Single query vector
        vectors: Multiple vectors (2D array)
        
    Returns:
        Array of similarity scores
    """
    if isinstance(query_vector, list):
        query_vector = np.array(query_vector, dtype=np.float32)
    if isinstance(vectors, list):
        vectors = np.array(vectors, dtype=np.float32)
    
    # Normalize query vector
    query_norm = np.linalg.norm(query_vector)
    if query_norm == 0:
        return np.zeros(len(vectors), dtype=np.float32)
    
    query_normalized = query_vector / query_norm
    
    # Normalize all vectors
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1, norms)  # Avoid division by zero
    vectors_normalized = vectors / norms
    
    # Compute dot products
    similarities = np.dot(vectors_normalized, query_normalized)
    
    return similarities


def batch_euclidean_distance(
    query_vector: Union[List[float], np.ndarray],
    vectors: Union[List[List[float]], np.ndarray]
) -> np.ndarray:
    """
    Compute Euclidean distance between a query vector and multiple vectors
    
    Args:
        query_vector: Single query vector
        vectors: Multiple vectors (2D array)
        
    Returns:
        Array of distances
    """
    if isinstance(query_vector, list):
        query_vector = np.array(query_vector, dtype=np.float32)
    if isinstance(vectors, list):
        vectors = np.array(vectors, dtype=np.float32)
    
    # Compute distances using broadcasting
    differences = vectors - query_vector
    distances = np.linalg.norm(differences, axis=1)
    
    return distances


def convert_distance_to_similarity(
    distances: Union[float, np.ndarray],
    metric: str = "cosine"
) -> Union[float, np.ndarray]:
    """
    Convert distance values to similarity scores
    
    Args:
        distances: Distance value(s)
        metric: Metric type ("cosine", "euclidean")
        
    Returns:
        Similarity score(s) in range [0, 1]
    """
    if metric == "cosine":
        # Cosine distance is in [0, 2], similarity in [-1, 1]
        # We map to [0, 1] for consistency
        return (1.0 - distances) / 2.0 + 0.5
    elif metric == "euclidean":
        # Convert Euclidean distance to similarity using exponential decay
        return 1.0 / (1.0 + distances)
    else:
        raise ValueError(f"Unsupported metric: {metric}")
