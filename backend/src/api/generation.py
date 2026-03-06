"""Generation API routes."""
import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..storage.database import get_db
from ..schemas.generation import (
    GenerationRequest,
    GenerationResponse,
    ModelsResponse,
    ModelInfo,
    HistoryListResponse,
    GenerationHistoryItem,
    GenerationHistoryDetail,
    SuccessResponse,
    ErrorResponse,
    TokenUsage,
    SourceReference,
    ContextItem,
)
from ..services.generation_service import (
    GenerationService,
    GenerationError,
    ModelNotFoundError,
    GENERATION_MODELS,
)
from ..models.generation import GenerationHistory, GenerationStatus


router = APIRouter(prefix="/generation", tags=["Generation"])


def get_generation_service() -> GenerationService:
    """Dependency to get generation service instance."""
    try:
        return GenerationService()
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============== Generation Endpoints ==============

@router.post("/generate", response_model=GenerationResponse)
async def generate_text(
    request: GenerationRequest,
    service: GenerationService = Depends(get_generation_service),
    db: Session = Depends(get_db),
):
    """Generate text response (non-streaming)."""
    try:
        # Check context length before generating
        length_check = service.check_context_length(request)
        if not length_check.get("valid"):
            raise HTTPException(status_code=400, detail=length_check.get("message"))
        
        result = await service.generate(request)
        
        # Save to history
        history = GenerationHistory(
            request_id=result.request_id,
            question=request.question,
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            context_summary=request.context[0].content[:200] if request.context else None,
            context_sources=[item.model_dump() for item in request.context],
            answer=result.answer,
            token_usage=result.token_usage.model_dump(),
            processing_time_ms=result.processing_time_ms,
            status=GenerationStatus.COMPLETED.value,
        )
        db.add(history)
        db.commit()
        
        # Cleanup old history
        GenerationService.cleanup_old_history(db)
        
        return GenerationResponse(
            request_id=result.request_id,
            answer=result.answer,
            model=result.model,
            token_usage=result.token_usage,
            processing_time_ms=result.processing_time_ms,
            sources=result.sources,
        )
    except ModelNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except GenerationError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stream")
async def generate_text_stream(
    request: GenerationRequest,
    service: GenerationService = Depends(get_generation_service),
    db: Session = Depends(get_db),
):
    """Generate text response with streaming (SSE)."""
    
    async def event_generator():
        request_id = None
        total_content = ""
        
        try:
            async for chunk in service.generate_stream(request):
                if "request_id" in chunk and chunk["request_id"]:
                    request_id = chunk["request_id"]
                
                if chunk.get("content"):
                    total_content += chunk["content"]
                
                yield f"data: {json.dumps(chunk)}\n\n"
                
                if chunk.get("done"):
                    # Save to history when complete
                    if request_id and not chunk.get("cancelled") and not chunk.get("error"):
                        try:
                            history = GenerationHistory(
                                request_id=request_id,
                                question=request.question,
                                model=request.model,
                                temperature=request.temperature,
                                max_tokens=request.max_tokens,
                                context_summary=request.context[0].content[:200] if request.context else None,
                                context_sources=[item.model_dump() for item in request.context],
                                answer=total_content,
                                token_usage=chunk.get("token_usage"),
                                processing_time_ms=chunk.get("processing_time_ms"),
                                status=GenerationStatus.COMPLETED.value,
                            )
                            db.add(history)
                            db.commit()
                        except Exception as e:
                            print(f"Failed to save history: {e}")
                    break
            
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e), 'done': True})}\n\n"
            yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/cancel/{request_id}", response_model=SuccessResponse)
async def cancel_generation(
    request_id: str,
    service: GenerationService = Depends(get_generation_service),
    db: Session = Depends(get_db),
):
    """Cancel an active generation request."""
    cancelled = service.cancel_generation(request_id)
    
    if cancelled:
        # Update history status
        history = db.query(GenerationHistory).filter(
            GenerationHistory.request_id == request_id
        ).first()
        if history:
            history.status = GenerationStatus.CANCELLED.value
            db.commit()
        
        return SuccessResponse(success=True, message="Generation cancelled")
    
    raise HTTPException(status_code=404, detail="Request not found or already completed")


# ============== Models Endpoints ==============

@router.get("/models", response_model=ModelsResponse)
async def list_models():
    """Get list of available generation models."""
    models = GenerationService.get_available_models()
    return ModelsResponse(
        models=[ModelInfo(**m) for m in models]
    )


# ============== History Endpoints ==============

@router.get("/history", response_model=HistoryListResponse)
async def list_history(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    """Get generation history list with pagination."""
    query = db.query(GenerationHistory).filter(
        GenerationHistory.is_deleted == False
    )
    
    if status:
        query = query.filter(GenerationHistory.status == status)
    
    total = query.count()
    total_pages = (total + page_size - 1) // page_size
    
    items = query.order_by(GenerationHistory.created_at.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()
    
    return HistoryListResponse(
        items=[
            GenerationHistoryItem(
                id=item.id,
                request_id=item.request_id,
                question=item.question,
                answer_preview=item.get_answer_preview(),
                model=item.model,
                status=item.status,
                created_at=item.created_at,
            )
            for item in items
        ],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/history/{id}", response_model=GenerationHistoryDetail)
async def get_history_detail(
    id: int,
    db: Session = Depends(get_db),
):
    """Get generation history detail."""
    history = db.query(GenerationHistory).filter(
        GenerationHistory.id == id,
        GenerationHistory.is_deleted == False,
    ).first()
    
    if not history:
        raise HTTPException(status_code=404, detail="History not found")
    
    # Parse context_sources
    context_sources = []
    if history.context_sources:
        context_sources = [
            ContextItem(**item) for item in history.context_sources
        ]
    
    # Parse token_usage
    token_usage = None
    if history.token_usage:
        token_usage = TokenUsage(**history.token_usage)
    
    return GenerationHistoryDetail(
        id=history.id,
        request_id=history.request_id,
        question=history.question,
        answer=history.answer,
        model=history.model,
        temperature=history.temperature,
        max_tokens=history.max_tokens,
        context_sources=context_sources,
        token_usage=token_usage,
        processing_time_ms=history.processing_time_ms,
        status=history.status,
        error_message=history.error_message,
        created_at=history.created_at,
    )


@router.delete("/history/clear", response_model=SuccessResponse)
async def clear_history(
    db: Session = Depends(get_db),
):
    """Clear all history records (soft delete)."""
    db.query(GenerationHistory).filter(
        GenerationHistory.is_deleted == False
    ).update({"is_deleted": True})
    db.commit()
    
    return SuccessResponse(success=True, message="All history cleared")


@router.delete("/history/{id}", response_model=SuccessResponse)
async def delete_history(
    id: int,
    db: Session = Depends(get_db),
):
    """Soft delete a history record."""
    history = db.query(GenerationHistory).filter(
        GenerationHistory.id == id,
        GenerationHistory.is_deleted == False,
    ).first()
    
    if not history:
        raise HTTPException(status_code=404, detail="History not found")
    
    history.is_deleted = True
    db.commit()
    
    return SuccessResponse(success=True, message="History deleted")
