"""Document parsing API endpoints."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..storage.database import get_db
from ..services.parsing_service import parsing_service
from ..utils.formatters import success_response, processing_result_to_dict
from ..utils.validators import validate_document_id

router = APIRouter()


class ParseRequest(BaseModel):
    """Parse document request."""
    document_id: str
    parse_option: str = "full_text"
    include_tables: bool = True


@router.post("/parse")
async def parse_document(
    request: ParseRequest,
    db: Session = Depends(get_db)
):
    """
    Parse document with specified options.
    
    Args:
        request: Parse request data
        db: Database session
        
    Returns:
        Processing result
    """
    validate_document_id(request.document_id)
    
    result = parsing_service.parse_document(
        db=db,
        document_id=request.document_id,
        parse_option=request.parse_option,
        include_tables=request.include_tables
    )
    
    return success_response(
        data=processing_result_to_dict(result),
        message="Document parsed successfully"
    )
