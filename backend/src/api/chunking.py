"""Chunking API endpoints."""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from ..storage.database import get_db
from ..services.chunking_service import chunking_service
from ..models.document import Document
from ..models.chunking_strategy import ChunkingStrategy
from ..models.chunking_task import ChunkingTask, StrategyType, TaskStatus
from ..models.chunking_result import ChunkingResult
from ..utils.formatters import success_response, paginated_response
from ..utils.error_handlers import NotFoundError, ValidationError
import json

router = APIRouter()


# Request/Response Models
class ChunkingRequest(BaseModel):
    """Request model for chunking operation."""
    document_id: str = Field(..., description="Document ID to chunk")
    strategy_type: str = Field(..., description="Chunking strategy type")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Strategy parameters")


class ChunkingTaskResponse(BaseModel):
    """Response model for chunking task."""
    task_id: str
    status: str
    document_id: str
    strategy_type: str
    parameters: Dict[str, Any]
    queue_position: Optional[int] = None


# T015: GET /api/documents/parsed - Get list of loaded documents (ready for chunking)
@router.get("/documents/parsed")
async def get_parsed_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Get list of documents that have been loaded and are ready for chunking.
    Simplified workflow: load -> chunk (parse step is optional for future optimization).
    
    Args:
        page: Page number
        page_size: Items per page
        db: Database session
        
    Returns:
        Paginated list of loaded documents with their processing results
    """
    from ..models.processing_result import ProcessingResult
    from sqlalchemy import and_, or_
    
    # Query documents that have either load or parse results (both can be chunked)
    query = db.query(Document).join(
        ProcessingResult,
        Document.id == ProcessingResult.document_id
    ).filter(
        or_(
            and_(
                ProcessingResult.processing_type == "load",
                ProcessingResult.status == "completed"
            ),
            and_(
                ProcessingResult.processing_type == "parse",
                ProcessingResult.status == "completed"
            )
        )
    ).distinct()
    
    total = query.count()
    offset = (page - 1) * page_size
    documents = query.order_by(Document.upload_time.desc()).offset(offset).limit(page_size).all()
    
    # For each document, get its latest processing result (prefer parse over load)
    items = []
    for doc in documents:
        # Check for parsing result first (preferred if available)
        parsing_result = db.query(ProcessingResult).filter(
            ProcessingResult.document_id == doc.id,
            ProcessingResult.processing_type == "parse",
            ProcessingResult.status == "completed"
        ).order_by(ProcessingResult.created_at.desc()).first()
        
        # Fall back to loading result
        loading_result = db.query(ProcessingResult).filter(
            ProcessingResult.document_id == doc.id,
            ProcessingResult.processing_type == "load",
            ProcessingResult.status == "completed"
        ).order_by(ProcessingResult.created_at.desc()).first()
        
        # Use whichever is available (prefer parsing if both exist)
        processing_result = parsing_result or loading_result
        processing_type = "parsed" if parsing_result else "loaded"
        
        if processing_result:
            items.append({
                "id": doc.id,
                "filename": doc.filename,
                "format": doc.format,
                "size_bytes": doc.size_bytes,
                "upload_time": doc.upload_time.isoformat() if doc.upload_time else None,
                "processing_type": processing_type,
                "processing_result": {
                    "id": processing_result.id,
                    "result_path": processing_result.result_path,
                    "created_at": processing_result.created_at.isoformat() if processing_result.created_at else None
                }
            })
    
    return success_response(
        data=paginated_response(
            items=items,
            total=total,
            page=page,
            page_size=page_size
        )
    )


# T016: GET /api/chunking/strategies - Get available chunking strategies
@router.get("/strategies")
async def get_chunking_strategies(
    active_only: bool = Query(True, description="Only return active strategies"),
    db: Session = Depends(get_db)
):
    """
    Get list of available chunking strategies.
    
    Args:
        active_only: Filter to only active strategies
        db: Database session
        
    Returns:
        List of chunking strategies
    """
    query = db.query(ChunkingStrategy)
    
    if active_only:
        query = query.filter(ChunkingStrategy.is_enabled == True)
    
    strategies = query.order_by(ChunkingStrategy.strategy_id).all()
    
    items = []
    for strategy in strategies:
        items.append({
            "id": strategy.strategy_id,
            "name": strategy.strategy_name,
            "type": strategy.strategy_type.value,
            "description": strategy.description,
            "default_parameters": strategy.default_params,
            "is_active": strategy.is_enabled
        })
    
    return success_response(data={"strategies": items})


# T028: POST /api/chunking/chunk - Create chunking task
@router.post("/chunk")
async def create_chunking_task(
    request: ChunkingRequest,
    db: Session = Depends(get_db)
):
    """
    Create a new chunking task.
    
    Args:
        request: Chunking request
        db: Database session
        
    Returns:
        Created task information
    """
    # Validate document exists
    document = db.query(Document).filter(Document.id == request.document_id).first()
    if not document:
        raise NotFoundError("Document", request.document_id)
    
    # Check if document has been processed (load or parse)
    from ..models.processing_result import ProcessingResult
    from sqlalchemy import or_, and_
    
    processing_result = db.query(ProcessingResult).filter(
        ProcessingResult.document_id == request.document_id,
        or_(
            and_(
                ProcessingResult.processing_type == "parse",
                ProcessingResult.status == "completed"
            ),
            and_(
                ProcessingResult.processing_type == "load",
                ProcessingResult.status == "completed"
            )
        )
    ).order_by(ProcessingResult.created_at.desc()).first()
    
    if not processing_result:
        raise ValidationError(f"Document {request.document_id} must be loaded first")
    
    # Convert strategy_type string to enum
    try:
        strategy_enum = StrategyType[request.strategy_type.upper()]
    except KeyError:
        raise ValidationError(f"Invalid strategy type: {request.strategy_type}")
    
    # Validate strategy exists
    strategy = db.query(ChunkingStrategy).filter(
        ChunkingStrategy.strategy_type == strategy_enum,
        ChunkingStrategy.is_enabled == True
    ).first()
    
    if not strategy:
        raise ValidationError(f"Strategy '{request.strategy_type}' not found or inactive")
    
    # Validate parameters
    validated_params = chunking_service.validate_strategy_parameters(
        request.strategy_type,
        request.parameters
    )
    
    # Create task
    task = ChunkingTask(
        source_document_id=request.document_id,
        source_file_path=document.storage_path,
        chunking_strategy=strategy_enum,
        chunking_params=validated_params,
        status=TaskStatus.PENDING,
        queue_position=0  # Will be set by queue manager
    )
    
    db.add(task)
    db.commit()
    db.refresh(task)
    
    # Process task immediately (queue management will be added in Phase 5)
    try:
        result = chunking_service.process_chunking_task(task.task_id, db)
        db.refresh(task)
    except Exception as e:
        # Task status already updated in service
        pass
    
    return success_response(
        data={
            "task_id": task.task_id,
            "status": task.status.value,
            "document_id": task.source_document_id,
            "strategy_type": task.chunking_strategy.value,
            "parameters": task.chunking_params,
            "queue_position": task.queue_position,
            "created_at": task.created_at.isoformat() if task.created_at else None
        },
        message="Chunking task created successfully"
    )


# T029: GET /api/chunking/task/{task_id} - Get task status
@router.get("/task/{task_id}")
async def get_chunking_task(
    task_id: str,
    db: Session = Depends(get_db)
):
    """
    Get chunking task status and details.
    
    Args:
        task_id: Task identifier
        db: Database session
        
    Returns:
        Task information
    """
    task = db.query(ChunkingTask).filter(ChunkingTask.task_id == task_id).first()
    if not task:
        raise NotFoundError("ChunkingTask", task_id)
    
    # Get associated result if completed
    result = None
    if task.status.value == "completed":
        result = db.query(ChunkingResult).filter(
            ChunkingResult.task_id == task_id
        ).first()
    
    response_data = {
        "task_id": task.task_id,
        "status": task.status.value,
        "document_id": task.source_document_id,
        "strategy_type": task.chunking_strategy.value,
        "parameters": task.chunking_params,
        "queue_position": task.queue_position,
        "error_message": task.error_message,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "result_id": None,
        "total_chunks": 0
    }
    
    if result:
        response_data["result_id"] = result.result_id
        response_data["total_chunks"] = result.total_chunks
    
    return success_response(data=response_data)


# T030: GET /api/chunking/result/{result_id} - Get chunking result
@router.get("/result/{result_id}")
async def get_chunking_result(
    result_id: str,
    include_chunks: bool = Query(True, description="Include chunk data"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """
    Get chunking result with optional chunk data.
    
    Args:
        result_id: Result identifier
        include_chunks: Whether to include chunk content
        page: Page number for chunks
        page_size: Chunks per page
        db: Database session
        
    Returns:
        Chunking result with optional chunks
    """
    result = db.query(ChunkingResult).filter(ChunkingResult.result_id == result_id).first()
    if not result:
        raise NotFoundError("ChunkingResult", result_id)
    
    # Get document info
    document = db.query(Document).filter(Document.id == result.document_id).first()
    
    response_data = {
        "result_id": result.result_id,
        "task_id": result.task_id,
        "document_id": result.document_id,
        "document_name": result.document_name,
        "strategy_type": result.chunking_strategy.value,
        "parameters": result.chunking_params,
        "status": result.status.value,
        "total_chunks": result.total_chunks,
        "statistics": result.statistics,
        "file_path": result.json_file_path,
        "created_at": result.created_at.isoformat() if result.created_at else None
    }
    
    if include_chunks and result.status.value == "completed":
        from ..models.chunk import Chunk
        
        # Get paginated chunks
        query = db.query(Chunk).filter(Chunk.result_id == result_id).order_by(Chunk.sequence_number)
        total_chunks = query.count()
        offset = (page - 1) * page_size
        chunks = query.offset(offset).limit(page_size).all()
        
        chunk_list = []
        for chunk in chunks:
            chunk_list.append({
                "id": chunk.id,
                "sequence_number": chunk.sequence_number,
                "content": chunk.content,
                "metadata": chunk.chunk_metadata,
                "start_position": chunk.start_position,
                "end_position": chunk.end_position,
                "token_count": chunk.token_count
            })
        
        response_data["chunks"] = paginated_response(
            items=chunk_list,
            total=total_chunks,
            page=page,
            page_size=page_size
        )
    
    return success_response(data=response_data)
