"""
Incremental embedding service.

Provides incremental vectorization support:
- Content hash-based change detection
- Skip unchanged chunks
- Reuse existing vectors
"""
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass
import hashlib
import time

from ..models.embedding_models import ErrorType
from ..utils.logging_utils import embedding_logger
from .content_hash_service import ContentHashService, get_content_hash_service


@dataclass
class ChunkChangeInfo:
    """Information about chunk changes."""
    chunk_id: str
    content_hash: str
    is_new: bool
    is_modified: bool
    has_existing_vector: bool


@dataclass
class IncrementalAnalysis:
    """Analysis result for incremental embedding."""
    total_chunks: int
    new_chunks: int
    modified_chunks: int
    unchanged_chunks: int
    chunks_to_embed: List[str]  # chunk_ids that need embedding
    chunks_to_reuse: List[str]  # chunk_ids with existing vectors
    change_summary: Dict[str, Any]


@dataclass
class IncrementalEmbeddingResult:
    """Result of incremental embedding operation."""
    request_id: str
    total_chunks: int
    embedded_count: int
    reused_count: int
    failed_count: int
    processing_time_ms: float
    vectors_new: List[Dict[str, Any]]
    vectors_reused: List[Dict[str, Any]]
    failures: List[Dict[str, Any]]
    savings_percentage: float  # 节省的计算百分比


class IncrementalEmbeddingService:
    """
    Incremental embedding service.
    
    Detects content changes and only embeds new or modified chunks,
    reusing existing vectors for unchanged content.
    """
    
    def __init__(
        self,
        hash_service: Optional[ContentHashService] = None,
    ):
        """
        Initialize service.
        
        Args:
            hash_service: Content hash service (optional)
        """
        self.hash_service = hash_service or get_content_hash_service()
        self._vector_cache: Dict[str, List[float]] = {}  # content_hash -> vector
    
    def analyze_changes(
        self,
        document_id: str,
        chunks: List[Dict[str, Any]],
        existing_vectors: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> IncrementalAnalysis:
        """
        Analyze which chunks need embedding.
        
        Args:
            document_id: Document identifier
            chunks: List of chunk dicts with 'chunk_id', 'content'
            existing_vectors: Optional dict of existing vectors by chunk_id
                Format: {chunk_id: {'vector': [...], 'content_hash': '...'}}
            
        Returns:
            IncrementalAnalysis with change details
        """
        existing_vectors = existing_vectors or {}
        
        # Calculate content hashes for all chunks
        chunk_hashes = {}
        for chunk in chunks:
            content = chunk.get('content', '')
            chunk_id = chunk.get('chunk_id', '')
            chunk_hashes[chunk_id] = self.hash_service.compute_hash(content)
        
        # Build existing hash lookup
        existing_hashes = {}
        for chunk_id, vec_info in existing_vectors.items():
            existing_hashes[chunk_id] = vec_info.get('content_hash', '')
        
        # Analyze changes
        new_chunks = []
        modified_chunks = []
        unchanged_chunks = []
        chunks_to_embed = []
        chunks_to_reuse = []
        
        for chunk in chunks:
            chunk_id = chunk.get('chunk_id', '')
            new_hash = chunk_hashes.get(chunk_id, '')
            old_hash = existing_hashes.get(chunk_id, '')
            
            if chunk_id not in existing_vectors:
                # New chunk - needs embedding
                new_chunks.append(chunk_id)
                chunks_to_embed.append(chunk_id)
            elif new_hash != old_hash:
                # Modified chunk - needs embedding
                modified_chunks.append(chunk_id)
                chunks_to_embed.append(chunk_id)
            else:
                # Unchanged chunk - can reuse vector
                unchanged_chunks.append(chunk_id)
                chunks_to_reuse.append(chunk_id)
        
        return IncrementalAnalysis(
            total_chunks=len(chunks),
            new_chunks=len(new_chunks),
            modified_chunks=len(modified_chunks),
            unchanged_chunks=len(unchanged_chunks),
            chunks_to_embed=chunks_to_embed,
            chunks_to_reuse=chunks_to_reuse,
            change_summary={
                'new_chunk_ids': new_chunks,
                'modified_chunk_ids': modified_chunks,
                'unchanged_chunk_ids': unchanged_chunks,
                'embed_required': len(chunks_to_embed),
                'reuse_available': len(chunks_to_reuse),
            }
        )
    
    def filter_chunks_for_embedding(
        self,
        chunks: List[Dict[str, Any]],
        analysis: IncrementalAnalysis,
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        Filter chunks to only those needing embedding.
        
        Args:
            chunks: All chunks
            analysis: Change analysis result
            
        Returns:
            Tuple of (chunks_to_embed, chunk_ids_to_reuse)
        """
        chunks_to_embed = []
        embed_set = set(analysis.chunks_to_embed)
        
        for chunk in chunks:
            chunk_id = chunk.get('chunk_id', '')
            if chunk_id in embed_set:
                chunks_to_embed.append(chunk)
        
        return chunks_to_embed, analysis.chunks_to_reuse
    
    def merge_results(
        self,
        new_vectors: List[Dict[str, Any]],
        reused_vectors: List[Dict[str, Any]],
        chunks: List[Dict[str, Any]],
        request_id: str,
        processing_time_ms: float,
        failures: Optional[List[Dict[str, Any]]] = None,
    ) -> IncrementalEmbeddingResult:
        """
        Merge new and reused vectors into final result.
        
        Args:
            new_vectors: Newly computed vectors
            reused_vectors: Reused existing vectors
            chunks: Original chunks list
            request_id: Request identifier
            processing_time_ms: Processing time
            failures: Optional list of failures
            
        Returns:
            IncrementalEmbeddingResult
        """
        failures = failures or []
        total_chunks = len(chunks)
        embedded_count = len(new_vectors)
        reused_count = len(reused_vectors)
        failed_count = len(failures)
        
        # Calculate savings
        if total_chunks > 0:
            savings_percentage = (reused_count / total_chunks) * 100
        else:
            savings_percentage = 0.0
        
        return IncrementalEmbeddingResult(
            request_id=request_id,
            total_chunks=total_chunks,
            embedded_count=embedded_count,
            reused_count=reused_count,
            failed_count=failed_count,
            processing_time_ms=processing_time_ms,
            vectors_new=new_vectors,
            vectors_reused=reused_vectors,
            failures=failures,
            savings_percentage=savings_percentage,
        )
    
    def get_reusable_vectors(
        self,
        chunk_ids: List[str],
        existing_vectors: Dict[str, Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Get vectors that can be reused.
        
        Args:
            chunk_ids: Chunk IDs to get vectors for
            existing_vectors: Dict of existing vectors
            
        Returns:
            List of vector dicts
        """
        reused = []
        for chunk_id in chunk_ids:
            if chunk_id in existing_vectors:
                vec_info = existing_vectors[chunk_id]
                reused.append({
                    'chunk_id': chunk_id,
                    'vector': vec_info.get('vector', []),
                    'content_hash': vec_info.get('content_hash', ''),
                    'reused': True,
                })
        return reused
    
    def should_force_recompute(
        self,
        model_changed: bool,
        force_recompute: bool,
    ) -> bool:
        """
        Determine if full recompute is needed.
        
        Args:
            model_changed: Whether embedding model has changed
            force_recompute: User-specified force recompute flag
            
        Returns:
            True if full recompute is needed
        """
        return model_changed or force_recompute


# Global instance
_default_service = None


def get_incremental_embedding_service() -> IncrementalEmbeddingService:
    """Get default incremental embedding service instance."""
    global _default_service
    if _default_service is None:
        _default_service = IncrementalEmbeddingService()
    return _default_service
