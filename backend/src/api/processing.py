"""Processing results API endpoints."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from ..storage.database import get_db
from ..models.processing_result import ProcessingResult
from ..utils.formatters import success_response, processing_result_to_dict
from ..utils.validators import validate_document_id
from ..utils.error_handlers import NotFoundError

router = APIRouter()


@router.get("/results/{document_id}")
async def get_processing_results(
    document_id: str,
    processing_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get processing results for a document.
    
    Args:
        document_id: Document identifier
        processing_type: Filter by processing type
        db: Database session
        
    Returns:
        List of processing results
    """
    validate_document_id(document_id)
    
    query = db.query(ProcessingResult).filter(
        ProcessingResult.document_id == document_id
    )
    
    if processing_type:
        query = query.filter(ProcessingResult.processing_type == processing_type)
    
    results = query.order_by(ProcessingResult.created_at.desc()).all()
    
    return success_response(
        data=[processing_result_to_dict(r) for r in results]
    )


@router.get("/results/detail/{result_id}")
async def get_processing_result(
    result_id: str,
    db: Session = Depends(get_db)
):
    """
    Get processing result by ID.
    
    Args:
        result_id: Result identifier
        db: Database session
        
    Returns:
        Processing result details
    """
    result = db.query(ProcessingResult).filter(
        ProcessingResult.id == result_id
    ).first()
    
    if not result:
        raise NotFoundError("ProcessingResult", result_id)
    
    # Load actual result data from JSON file
    from ..storage.json_storage import json_storage
    result_data = json_storage.load_result(result.result_path)
    
    return success_response(
        data={
            **processing_result_to_dict(result),
            "result_data": result_data
        }
    )
