"""FastAPI routes for embedding result queries."""
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, HTTPException, status, Depends, Query
from sqlalchemy.orm import Session

from ..models.embedding_models import (
    EmbeddingResult,
    ErrorResponse,
    EmbeddingResultDetail,
    EmbeddingResultListResponse,
    PaginationMeta,
)
from ..storage.embedding_db import EmbeddingResultDB

router = APIRouter(prefix="/embedding/results", tags=["embedding-queries"])


# Import database dependency
def get_db():
    """Get database session."""
    from ..storage.database import SessionLocal
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get(
    "/{result_id}",
    response_model=EmbeddingResultDetail,
    status_code=status.HTTP_200_OK,
    responses={
        404: {"model": ErrorResponse, "description": "Result not found"},
    },
)
async def get_embedding_result(
    result_id: str,
    db: Session = Depends(get_db),
):
    """
    Retrieve embedding result by unique result_id.
    
    Implements FR-025: Query by result_id
    
    Args:
        result_id: Unique embedding result identifier
        db: Database session
        
    Returns:
        Complete embedding result metadata
        
    Raises:
        404: Result not found
    """
    db_query = EmbeddingResultDB(db)
    result = db_query.get_by_result_id(result_id)
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "RESULT_NOT_FOUND",
                    "message": f"Embedding result '{result_id}' not found"
                }
            },
        )
    
    return EmbeddingResultDetail.model_validate(result)


@router.get(
    "/by-document/{document_id}",
    response_model=EmbeddingResultDetail,
    status_code=status.HTTP_200_OK,
    responses={
        404: {"model": ErrorResponse, "description": "Result not found"},
    },
)
async def get_latest_embedding_result(
    document_id: str,
    model: Optional[str] = Query(None, description="Filter by embedding model"),
    db: Session = Depends(get_db),
):
    """
    Retrieve latest embedding result for a document.
    
    Implements FR-026: Query latest by document_id (with model filter)
    
    Args:
        document_id: Document identifier
        model: Optional model filter (e.g., 'bge-m3')
        db: Database session
        
    Returns:
        Latest embedding result metadata
        
    Raises:
        404: No result found for document
    """
    db_query = EmbeddingResultDB(db)
    result = db_query.get_latest_by_document(document_id, model=model)
    
    if not result:
        model_msg = f" with model '{model}'" if model else ""
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "RESULT_NOT_FOUND",
                    "message": f"No embedding result found for document '{document_id}'{model_msg}"
                }
            },
        )
    
    return EmbeddingResultDetail.model_validate(result)


@router.get(
    "",
    response_model=EmbeddingResultListResponse,
    status_code=status.HTTP_200_OK,
)
async def list_embedding_results(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Results per page"),
    document_id: Optional[str] = Query(None, description="Filter by document ID"),
    model: Optional[str] = Query(None, description="Filter by embedding model"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (SUCCESS/FAILED/PARTIAL_SUCCESS)"),
    date_from: Optional[datetime] = Query(None, description="Filter by start date (ISO format)"),
    date_to: Optional[datetime] = Query(None, description="Filter by end date (ISO format)"),
    db: Session = Depends(get_db),
):
    """
    List embedding results with pagination and filters.
    
    Implements FR-027: List query API with pagination and filters
    
    Args:
        page: Page number (1-indexed)
        page_size: Results per page (max 100)
        document_id: Filter by document ID
        model: Filter by embedding model
        status_filter: Filter by status
        date_from: Filter by start date
        date_to: Filter by end date
        db: Database session
        
    Returns:
        Paginated list of embedding results with metadata
    """
    db_query = EmbeddingResultDB(db)
    
    # Build filters dictionary
    filters = {}
    if document_id:
        filters['document_id'] = document_id
    if model:
        filters['model'] = model
    if status_filter:
        filters['status'] = status_filter
    if date_from:
        filters['date_from'] = date_from
    if date_to:
        filters['date_to'] = date_to
    
    # Query with pagination
    results, total_count = db_query.list_results(
        filters=filters,
        page=page,
        page_size=page_size
    )
    
    # Build response
    total_pages = (total_count + page_size - 1) // page_size
    
    return EmbeddingResultListResponse(
        results=[EmbeddingResultDetail.model_validate(r) for r in results],
        pagination=PaginationMeta(
            total_count=total_count,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
    )


@router.get(
    "/stats/by-status/{status}",
    status_code=status.HTTP_200_OK,
)
async def get_count_by_status(
    status: str,
    db: Session = Depends(get_db),
):
    """
    Count embedding results by status.
    
    Args:
        status: Status value (SUCCESS/FAILED/PARTIAL_SUCCESS)
        db: Database session
        
    Returns:
        Count of results with specified status
    """
    db_query = EmbeddingResultDB(db)
    count = db_query.count_by_status(status)
    
    return {
        "status": status,
        "count": count
    }


@router.get(
    "/stats/by-model/{model}",
    status_code=status.HTTP_200_OK,
)
async def get_count_by_model(
    model: str,
    db: Session = Depends(get_db),
):
    """
    Count embedding results by model.
    
    Args:
        model: Model name
        db: Database session
        
    Returns:
        Count of results for specified model
    """
    db_query = EmbeddingResultDB(db)
    count = db_query.count_by_model(model)
    
    return {
        "model": model,
        "count": count
    }


@router.get(
    "/stats/processing",
    status_code=status.HTTP_200_OK,
)
async def get_processing_stats(
    date_from: Optional[datetime] = Query(None, description="Start date"),
    date_to: Optional[datetime] = Query(None, description="End date"),
    db: Session = Depends(get_db),
):
    """
    Get processing statistics for a date range.
    
    Args:
        date_from: Start date
        date_to: End date
        db: Database session
        
    Returns:
        Processing statistics (avg time, success rate, etc.)
    """
    db_query = EmbeddingResultDB(db)
    stats = db_query.get_processing_stats(date_from, date_to)
    
    return stats
