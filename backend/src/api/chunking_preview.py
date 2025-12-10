"""Chunking preview endpoint for strategy testing."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Dict, Any, List
from ..storage.database import get_db
from ..services.chunking_service import chunking_service
from ..utils.formatters import success_response
from ..utils.error_handlers import NotFoundError, ValidationError

router = APIRouter()


class PreviewRequest(BaseModel):
    """Request model for chunking preview."""
    document_id: str = Field(..., description="Document ID")
    strategy_type: str = Field(..., description="Strategy type")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Parameters")
    max_chunks: int = Field(default=5, ge=1, le=20, description="Max chunks to return")


@router.post("/preview")
async def preview_chunking(
    request: PreviewRequest,
    db: Session = Depends(get_db)
):
    """
    Preview chunking strategy on document without saving.
    
    Returns first N chunks for preview purposes.
    
    Args:
        request: Preview request
        db: Database session
        
    Returns:
        Preview chunks
    """
    try:
        # Validate parameters
        validated_params = chunking_service.validate_strategy_parameters(
            request.strategy_type,
            request.parameters
        )
        
        # Load document
        text = chunking_service.load_source_document(request.document_id, db)
        
        # Get chunker and process
        chunker = chunking_service.get_chunker(request.strategy_type, validated_params)
        all_chunks = chunker.chunk(text)
        
        # Return only first N chunks for preview
        preview_chunks = all_chunks[:request.max_chunks]
        
        # Calculate preview statistics
        from ..utils.chunking_helpers import ChunkStatistics
        preview_stats = ChunkStatistics.calculate_statistics(preview_chunks)
        
        return success_response(
            data={
                "preview_chunks": preview_chunks,
                "total_chunks_estimate": len(all_chunks),
                "preview_count": len(preview_chunks),
                "statistics": preview_stats,
                "has_fallback": any(
                    'fallback_strategy' in chunk.get('metadata', {})
                    for chunk in preview_chunks
                )
            },
            message="Preview generated successfully"
        )
        
    except ValueError as e:
        raise ValidationError(str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
