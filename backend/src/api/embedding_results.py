"""
Embedding result management API.

Provides endpoints for:
- Result CRUD operations
- Incremental embedding
- Result comparison
- Export functionality
"""
import time
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..storage.embedding_db import EmbeddingResultDB
from ..services.embedding_service import EmbeddingService, EMBEDDING_MODELS
from ..utils.logging_utils import embedding_logger


router = APIRouter(prefix="/embedding/results", tags=["Embedding Results"])


# ============================================================================
# Request/Response Models
# ============================================================================

class IncrementalEmbeddingRequest(BaseModel):
    """Request for incremental embedding."""
    document_id: str = Field(..., description="Document ID")
    model: str = Field(default="qwen3-embedding-8b", description="Embedding model")
    incremental: bool = Field(default=True, description="Enable incremental mode")
    force_recompute: bool = Field(default=False, description="Force recompute all vectors")
    max_retries: int = Field(default=3, ge=1, le=10)
    timeout: int = Field(default=60, ge=10, le=300)


class CompareRequest(BaseModel):
    """Request for comparing results."""
    result_ids: List[str] = Field(..., min_length=2, max_length=10)


# ============================================================================
# Dependency Injection
# ============================================================================

def get_db():
    """Get database session."""
    from ..storage.database import SessionLocal
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_embedding_service_for_request(
    model: str,
    max_retries: int,
    timeout: int,
) -> EmbeddingService:
    """Get embedding service instance."""
    import os
    from ..models.embedding_models import AuthenticationError
    
    api_key = os.getenv("EMBEDDING_API_KEY")
    if not api_key:
        raise AuthenticationError("EMBEDDING_API_KEY environment variable not set")

    base_url = os.getenv("EMBEDDING_API_BASE_URL")
    if not base_url:
        raise AuthenticationError("EMBEDDING_API_BASE_URL environment variable not set")
    
    return EmbeddingService(
        api_key=api_key,
        model=model,
        base_url=base_url,
        max_retries=max_retries,
        request_timeout=timeout,
    )


# ============================================================================
# Result CRUD Endpoints
# ============================================================================

@router.get("/{result_id}")
async def get_result(
    result_id: str,
    db: Session = Depends(get_db),
):
    """Get embedding result by ID."""
    result = db.query(EmbeddingResultDB).filter(
        EmbeddingResultDB.result_id == result_id
    ).first()
    
    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"Result {result_id} not found"
        )
    
    return {
        "result_id": result.result_id,
        "document_id": result.document_id,
        "model": result.model,
        "is_active": result.is_active,
        "vector_count": result.vector_count,
        "created_at": result.created_at.isoformat() if result.created_at else None,
        "statistics": result.statistics,
    }


@router.get("/document/{document_id}")
async def get_document_results(
    document_id: str,
    db: Session = Depends(get_db),
):
    """Get all embedding results for a document."""
    results = db.query(EmbeddingResultDB).filter(
        EmbeddingResultDB.document_id == document_id
    ).order_by(EmbeddingResultDB.created_at.desc()).all()
    
    return {
        "document_id": document_id,
        "results": [
            {
                "result_id": r.result_id,
                "model": r.model,
                "is_active": r.is_active,
                "vector_count": r.vector_count,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in results
        ],
        "count": len(results),
    }


@router.post("/{result_id}/activate")
async def activate_result(
    result_id: str,
    db: Session = Depends(get_db),
):
    """
    Set an embedding result as active.
    
    Deactivates other results for the same document.
    """
    result = db.query(EmbeddingResultDB).filter(
        EmbeddingResultDB.result_id == result_id
    ).first()
    
    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"Result {result_id} not found"
        )
    
    # Deactivate other results for same document
    db.query(EmbeddingResultDB).filter(
        EmbeddingResultDB.document_id == result.document_id,
        EmbeddingResultDB.result_id != result_id
    ).update({"is_active": False})
    
    # Activate this result
    result.is_active = True
    db.commit()
    
    return {
        "message": f"Result {result_id} activated",
        "result_id": result_id,
        "document_id": result.document_id,
    }


@router.delete("/{result_id}")
async def delete_result(
    result_id: str,
    db: Session = Depends(get_db),
):
    """
    Delete an embedding result.
    
    Only non-active results can be deleted.
    """
    result = db.query(EmbeddingResultDB).filter(
        EmbeddingResultDB.result_id == result_id
    ).first()
    
    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"Result {result_id} not found"
        )
    
    if result.is_active:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete active result. Activate another result first."
        )
    
    db.delete(result)
    db.commit()
    
    return {
        "message": f"Result {result_id} deleted",
        "result_id": result_id,
    }


# ============================================================================
# Comparison Endpoint
# ============================================================================

@router.post("/compare")
async def compare_results(
    request: CompareRequest,
    db: Session = Depends(get_db),
):
    """
    Compare multiple embedding results.
    
    Returns comparison data for different models/configurations.
    """
    results = db.query(EmbeddingResultDB).filter(
        EmbeddingResultDB.result_id.in_(request.result_ids)
    ).all()
    
    if len(results) != len(request.result_ids):
        found_ids = {r.result_id for r in results}
        missing = set(request.result_ids) - found_ids
        raise HTTPException(
            status_code=404,
            detail=f"Results not found: {missing}"
        )
    
    # Build comparison data
    comparison = []
    for result in results:
        model_info = EMBEDDING_MODELS.get(result.model, {})
        comparison.append({
            "result_id": result.result_id,
            "model": result.model,
            "model_display_name": model_info.get("description", result.model),
            "dimension": model_info.get("dimension", 0),
            "vector_count": result.vector_count,
            "is_active": result.is_active,
            "created_at": result.created_at.isoformat() if result.created_at else None,
            "statistics": result.statistics or {},
        })
    
    return {
        "comparison": comparison,
        "count": len(comparison),
    }


# ============================================================================
# Export Endpoint
# ============================================================================

@router.get("/{result_id}/export")
async def export_result(
    result_id: str,
    include_vectors: bool = Query(default=True, description="Include vector data"),
    include_metadata: bool = Query(default=True, description="Include metadata"),
    db: Session = Depends(get_db),
):
    """
    Export embedding result to JSON format.
    """
    result = db.query(EmbeddingResultDB).filter(
        EmbeddingResultDB.result_id == result_id
    ).first()
    
    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"Result {result_id} not found"
        )
    
    export_data = {
        "result_id": result.result_id,
        "document_id": result.document_id,
        "model": result.model,
        "vector_count": result.vector_count,
        "created_at": result.created_at.isoformat() if result.created_at else None,
        "exported_at": datetime.utcnow().isoformat() + "Z",
    }
    
    if include_metadata:
        export_data["statistics"] = result.statistics or {}
        export_data["is_active"] = result.is_active
    
    if include_vectors and result.vectors:
        export_data["vectors"] = result.vectors
    
    return export_data


# ============================================================================
# Incremental Embedding Endpoint
# ============================================================================

@router.post("/incremental")
async def embed_incremental(
    request: IncrementalEmbeddingRequest,
    db: Session = Depends(get_db),
):
    """
    Perform incremental embedding for a document.
    
    Only embeds new or changed chunks, reusing existing vectors for unchanged content.
    """
    from ..services.incremental_embedding_service import get_incremental_embedding_service
    
    request_id = str(uuid.uuid4())
    
    try:
        # Get services
        incremental_service = get_incremental_embedding_service()
        embedding_service = get_embedding_service_for_request(
            model=request.model,
            max_retries=request.max_retries,
            timeout=request.timeout,
        )
        
        # Get existing vectors if incremental
        existing_vectors = {}
        if request.incremental and not request.force_recompute:
            existing_result = db.query(EmbeddingResultDB).filter(
                EmbeddingResultDB.document_id == request.document_id,
                EmbeddingResultDB.is_active == True
            ).first()
            
            if existing_result and existing_result.vectors:
                for v in existing_result.vectors:
                    chunk_id = v.get('chunk_id', str(v.get('index', '')))
                    existing_vectors[chunk_id] = {
                        'vector': v.get('vector', []),
                        'content_hash': v.get('text_hash', ''),
                    }
        
        # Get chunks from document
        from ..models.chunking_result import ChunkingResult, ResultStatus
        from ..models.chunking_task import ChunkingTask
        from ..models.chunk import Chunk
        
        query = db.query(ChunkingResult).join(
            ChunkingTask,
            ChunkingResult.task_id == ChunkingTask.task_id
        ).filter(
            ChunkingTask.source_document_id == request.document_id,
            ChunkingResult.status == ResultStatus.COMPLETED,
            ChunkingResult.is_active == True
        )
        
        chunking_result = query.order_by(ChunkingResult.created_at.desc()).first()
        if not chunking_result:
            raise HTTPException(
                status_code=404,
                detail="No chunks found for document"
            )
        
        chunks = db.query(Chunk).filter(
            Chunk.result_id == chunking_result.result_id
        ).order_by(Chunk.sequence_number).all()
        
        # Prepare chunks for analysis
        chunks_data = [
            {
                'chunk_id': str(c.sequence_number),
                'content': c.content,
                'chunk_type': c.chunk_type or 'text',
            }
            for c in chunks
        ]
        
        # Analyze changes
        analysis = incremental_service.analyze_changes(
            document_id=request.document_id,
            chunks=chunks_data,
            existing_vectors=existing_vectors,
        )
        
        # If force recompute, embed all
        if request.force_recompute or not request.incremental:
            analysis.chunks_to_embed = [c['chunk_id'] for c in chunks_data]
            analysis.chunks_to_reuse = []
        
        # Embed only changed chunks
        start_time = time.time()
        
        new_vectors = []
        failures = []
        
        if analysis.chunks_to_embed:
            texts_to_embed = []
            embed_indices = []
            for c in chunks_data:
                if c['chunk_id'] in analysis.chunks_to_embed:
                    texts_to_embed.append(c['content'])
                    embed_indices.append(c['chunk_id'])
            
            result = embedding_service.embed_documents(texts_to_embed, request_id=request_id)
            
            for i, vec_result in enumerate(result.vectors):
                chunk_id = embed_indices[vec_result.index] if vec_result.index < len(embed_indices) else str(i)
                new_vectors.append({
                    'chunk_id': chunk_id,
                    'vector': vec_result.vector,
                    'text_hash': vec_result.text_hash,
                    'text_length': vec_result.text_length,
                })
            
            for fail in result.failures:
                failures.append({
                    'chunk_id': embed_indices[fail.index] if fail.index < len(embed_indices) else str(fail.index),
                    'error_type': fail.error_type.value,
                    'error_message': fail.error_message,
                })
        
        # Get reused vectors
        reused_vectors = incremental_service.get_reusable_vectors(
            analysis.chunks_to_reuse,
            existing_vectors
        )
        
        processing_time_ms = (time.time() - start_time) * 1000
        
        # Calculate savings
        total_chunks = len(chunks_data)
        reused_count = len(reused_vectors)
        savings_percentage = (reused_count / total_chunks * 100) if total_chunks > 0 else 0.0
        
        return {
            "request_id": request_id,
            "document_id": request.document_id,
            "incremental_mode": request.incremental,
            "force_recompute": request.force_recompute,
            "statistics": {
                "total_chunks": total_chunks,
                "new_chunks": analysis.new_chunks,
                "modified_chunks": analysis.modified_chunks,
                "unchanged_chunks": analysis.unchanged_chunks,
                "embedded_count": len(new_vectors),
                "reused_count": reused_count,
                "failed_count": len(failures),
                "savings_percentage": f"{savings_percentage:.1f}%",
            },
            "processing_time_ms": processing_time_ms,
            "vectors_new": new_vectors,
            "vectors_reused": reused_vectors,
            "failures": failures,
        }
        
    except HTTPException:
        raise
    except Exception as exc:
        embedding_logger.log_request_failed(
            request_id=request_id,
            model=request.model,
            duration_ms=0,
            error_type="INTERNAL_ERROR",
            error_message=str(exc),
        )
        raise HTTPException(
            status_code=500,
            detail=f"Incremental embedding failed: {str(exc)}"
        ) from exc


# ============================================================================
# Statistics Endpoint
# ============================================================================

@router.get("/{result_id}/statistics")
async def get_result_statistics(
    result_id: str,
    db: Session = Depends(get_db),
):
    """Get detailed statistics for an embedding result."""
    result = db.query(EmbeddingResultDB).filter(
        EmbeddingResultDB.result_id == result_id
    ).first()
    
    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"Result {result_id} not found"
        )
    
    # Build comprehensive statistics
    stats = result.statistics or {}
    
    # Add computed statistics
    computed = {
        "result_id": result.result_id,
        "model": result.model,
        "vector_count": result.vector_count,
        "is_active": result.is_active,
    }
    
    if result.vectors:
        # Vector dimension
        if result.vectors:
            computed["dimension"] = len(result.vectors[0].get("vector", []))
        
        # Calculate average text length
        text_lengths = [v.get("text_length", 0) for v in result.vectors if v.get("text_length")]
        if text_lengths:
            computed["avg_text_length"] = sum(text_lengths) / len(text_lengths)
            computed["min_text_length"] = min(text_lengths)
            computed["max_text_length"] = max(text_lengths)
    
    return {
        **computed,
        "stored_statistics": stats,
    }
