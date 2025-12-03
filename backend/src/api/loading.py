"""Document loading API endpoints."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional
from ..storage.database import get_db
from ..services.loading_service import loading_service
from ..utils.formatters import success_response, processing_result_to_dict
from ..utils.validators import validate_document_id

router = APIRouter()


class LoadRequest(BaseModel):
    """Load document request."""
    document_id: str
    loader_type: Optional[str] = None  # Auto-select if None


@router.post("/load")
async def load_document(
    request: LoadRequest,
    db: Session = Depends(get_db)
):
    """
    Load document with specified or auto-selected loader.
    
    Supports multiple document formats:
    - PDF: pymupdf (default), pypdf, unstructured
    - DOCX: docx
    - DOC: doc
    - TXT/Markdown: text
    
    Args:
        request: Load request data
        db: Database session
        
    Returns:
        Processing result
    """
    validate_document_id(request.document_id)
    
    result = loading_service.load_document(
        db=db,
        document_id=request.document_id,
        loader_type=request.loader_type
    )
    
    return success_response(
        data=processing_result_to_dict(result),
        message="Document loaded successfully"
    )


@router.get("/loaders")
async def get_available_loaders():
    """
    Get list of available loaders and supported formats.
    
    Returns:
        Available loaders and supported file formats
    """
    return success_response(
        data={
            "loaders": loading_service.get_available_loaders(),
            "supported_formats": loading_service.get_supported_formats(),
            "format_loader_map": loading_service.format_loader_map
        }
    )
