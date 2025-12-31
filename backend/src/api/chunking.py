"""Chunking API endpoints."""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
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
    search: Optional[str] = Query(None, description="Search by filename"),
    format: Optional[str] = Query(None, description="Filter by file format"),
    sort_by: str = Query("upload_time", regex="^(filename|upload_time|size_bytes)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    db: Session = Depends(get_db)
):
    """
    Get list of documents that have been loaded and are ready for chunking.
    Simplified workflow: load -> chunk (parse step is optional for future optimization).
    
    Args:
        page: Page number
        page_size: Items per page
        search: Search query for filename
        format: Filter by file format (e.g., 'pdf', 'docx', 'txt')
        sort_by: Sort field (filename, upload_time, size_bytes)
        sort_order: Sort order (asc, desc)
        db: Database session
        
    Returns:
        Paginated list of loaded documents with their processing results
    """
    from ..models.processing_result import ProcessingResult
    from sqlalchemy import and_, or_, desc, asc
    
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
    
    # Apply search filter
    if search:
        query = query.filter(Document.filename.ilike(f"%{search}%"))
    
    # Apply format filter
    if format:
        query = query.filter(Document.format == format.lower())
    
    # Apply sorting
    sort_field = getattr(Document, sort_by)
    if sort_order == "desc":
        query = query.order_by(desc(sort_field))
    else:
        query = query.order_by(asc(sort_field))
    
    total = query.count()
    offset = (page - 1) * page_size
    documents = query.offset(offset).limit(page_size).all()
    
    # For each document, get its latest loading result
    items = []
    for doc in documents:
        # Get loading result
        loading_result = db.query(ProcessingResult).filter(
            ProcessingResult.document_id == doc.id,
            ProcessingResult.processing_type == "load",
            ProcessingResult.status == "completed"
        ).order_by(ProcessingResult.created_at.desc()).first()
        
        if loading_result:
            items.append({
                "id": doc.id,
                "filename": doc.filename,
                "format": doc.format,
                "size_bytes": doc.size_bytes,
                "upload_time": doc.upload_time.isoformat() if doc.upload_time else None,
                "processing_type": "loaded",
                "processing_result": {
                    "id": loading_result.id,
                    "result_path": loading_result.result_path,
                    "created_at": loading_result.created_at.isoformat() if loading_result.created_at else None
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
    overwrite_mode: str = Query("auto", regex="^(auto|always|never)$", description="Overwrite mode: auto (smart), always (force overwrite), never (always create new)"),
    db: Session = Depends(get_db)
):
    """
    Create a new chunking task with intelligent version management.
    
    Args:
        request: Chunking request
        overwrite_mode: Overwrite strategy
            - auto: Smart detection (minor changes overwrite, major changes create new)
            - always: Always overwrite existing result for same strategy
            - never: Always create new result (maintain full history)
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
    
    # Import version helper
    from ..utils.chunking_version_helper import ChunkingVersionHelper
    
    # Check for existing results with same document + strategy
    import json
    from ..models.chunking_result import ChunkingResult, ResultStatus
    import logging
    
    logger = logging.getLogger(__name__)
    params_json = json.dumps(validated_params, sort_keys=True)
    logger.info(f"Creating chunking task - Document: {request.document_id}, Strategy: {strategy_enum.value}, Params: {params_json}, OverwriteMode: {overwrite_mode}")
    
    # Query all completed results for this document + strategy (active only)
    existing_results = db.query(ChunkingResult).join(
        ChunkingTask,
        ChunkingResult.task_id == ChunkingTask.task_id
    ).filter(
        ChunkingTask.source_document_id == request.document_id,
        ChunkingTask.chunking_strategy == strategy_enum,
        ChunkingResult.status == ResultStatus.COMPLETED,
        ChunkingResult.is_active == True
    ).order_by(ChunkingResult.created_at.desc()).all()
    
    # Decision logic based on overwrite_mode
    should_overwrite = False
    overwrite_reason = None
    existing_result_to_replace = None
    
    if existing_results:
        latest_result = existing_results[0]
        existing_params_json = json.dumps(latest_result.chunking_params, sort_keys=True)
        
        logger.info(f"Found {len(existing_results)} existing active result(s)")
        logger.info(f"Latest result ID: {latest_result.result_id}, Params: {existing_params_json}")
        
        # Check if parameters are exactly the same
        if existing_params_json == params_json:
            logger.info(f"Parameters match exactly, reusing existing result: {latest_result.result_id}")
            # Return existing result info
            existing_task = db.query(ChunkingTask).filter(
                ChunkingTask.task_id == latest_result.task_id
            ).first()
            
            return success_response(
                data={
                    "task_id": existing_task.task_id,
                    "status": existing_task.status.value,
                    "document_id": existing_task.source_document_id,
                    "strategy_type": existing_task.chunking_strategy.value,
                    "parameters": existing_task.chunking_params,
                    "queue_position": existing_task.queue_position,
                    "result_id": latest_result.result_id,
                    "total_chunks": latest_result.total_chunks,
                    "version": latest_result.version,
                    "is_active": latest_result.is_active,
                    "created_at": existing_task.created_at.isoformat() if existing_task.created_at else None
                },
                message="Using existing chunking result (identical parameters)"
            )
        
        # Parameters differ - apply overwrite mode logic
        if overwrite_mode == "always":
            should_overwrite = True
            overwrite_reason = "Manual override: always overwrite mode"
            existing_result_to_replace = latest_result
            logger.info(f"Overwrite mode 'always': will replace result {latest_result.result_id}")
        
        elif overwrite_mode == "auto":
            # Intelligent detection
            is_minor, reason = ChunkingVersionHelper.is_minor_param_change(
                latest_result.chunking_params,
                validated_params
            )
            
            if is_minor:
                should_overwrite = True
                overwrite_reason = f"Auto-optimization: {reason}"
                existing_result_to_replace = latest_result
                logger.info(f"Auto mode detected minor change: will replace result {latest_result.result_id}. Reason: {reason}")
            else:
                should_overwrite = False
                logger.info(f"Auto mode detected major change: will create new result. Reason: {reason}")
        
        elif overwrite_mode == "never":
            should_overwrite = False
            logger.info("Overwrite mode 'never': creating new result")
    
    # Handle overwrite: deactivate old result
    new_version = 1
    previous_version_id = None
    
    if should_overwrite and existing_result_to_replace:
        # Calculate version
        max_version = db.query(func.max(ChunkingResult.version)).filter(
            ChunkingResult.document_id == request.document_id,
            ChunkingResult.chunking_strategy == strategy_enum
        ).scalar() or 0
        
        new_version = max_version + 1
        previous_version_id = existing_result_to_replace.result_id
        
        # Deactivate old result
        existing_result_to_replace.is_active = False
        db.flush()
        logger.info(f"Deactivated result {existing_result_to_replace.result_id}, new version: {new_version}")
    else:
        # Calculate version for new result
        max_version = db.query(func.max(ChunkingResult.version)).filter(
            ChunkingResult.document_id == request.document_id,
            ChunkingResult.chunking_strategy == strategy_enum
        ).scalar() or 0
        
        new_version = max_version + 1
        logger.info(f"Creating new result version {new_version}")
    
    # Create task (but don't commit yet - wait for processing to succeed)
    task = ChunkingTask(
        source_document_id=request.document_id,
        source_file_path=document.storage_path,
        chunking_strategy=strategy_enum,
        chunking_params=validated_params,
        status=TaskStatus.PENDING,
        queue_position=0  # Will be set by queue manager
    )
    
    db.add(task)
    db.flush()  # Flush to get task_id without committing
    
    # Process task immediately (queue management will be added in Phase 5)
    try:
        result = chunking_service.process_chunking_task(
            task.task_id, 
            db, 
            version=new_version,
            previous_version_id=previous_version_id,
            replacement_reason=overwrite_reason
        )
        db.refresh(task)
        
        # Only commit if processing succeeded
        if task.status == TaskStatus.COMPLETED:
            db.commit()
            
            message = "Chunking task created and completed successfully"
            if should_overwrite:
                message = f"Chunking completed (replaced version {existing_result_to_replace.version})"
            
            return success_response(
                data={
                    "task_id": task.task_id,
                    "status": task.status.value,
                    "document_id": task.source_document_id,
                    "strategy_type": task.chunking_strategy.value,
                    "parameters": task.chunking_params,
                    "queue_position": task.queue_position,
                    "result_id": result.result_id if result else None,
                    "total_chunks": result.total_chunks if result else 0,
                    "version": result.version if result else new_version,
                    "is_active": result.is_active if result else True,
                    "previous_version_id": result.previous_version_id if result else None,
                    "replacement_reason": result.replacement_reason if result else None,
                    "created_at": task.created_at.isoformat() if task.created_at else None
                },
                message=message
            )
        else:
            # Task failed, rollback to avoid creating failed task record
            db.rollback()
            raise ValidationError(
                f"Chunking task failed: {task.error_message or 'Unknown error'}"
            )
    except Exception as e:
        # Rollback transaction to avoid creating failed task record
        db.rollback()
        error_msg = str(e)
        if hasattr(e, 'message'):
            error_msg = e.message
        raise ValidationError(f"Failed to process chunking task: {error_msg}")
    
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


# Get latest chunking result for a document (optionally filtered by strategy and parameters)
@router.get("/result/latest/{document_id}")
async def get_latest_result_for_document(
    document_id: str,
    strategy_type: Optional[str] = Query(None, description="Filter by strategy type"),
    parameters: Optional[str] = Query(None, description="Filter by parameters (JSON string)"),
    db: Session = Depends(get_db)
):
    """
    Get the latest active chunking result for a document.
    Can optionally filter by strategy type and/or parameters.
    
    Args:
        document_id: Document ID
        strategy_type: Optional strategy type filter
        parameters: Optional parameters filter (JSON string)
        db: Database session
        
    Returns:
        Latest chunking result or null if none exists
    """
    from ..models.chunking_result import ResultStatus
    
    # Start with base query for this document
    query = db.query(ChunkingResult).join(
        ChunkingTask,
        ChunkingResult.task_id == ChunkingTask.task_id
    ).filter(
        ChunkingTask.source_document_id == document_id,
        ChunkingResult.status == ResultStatus.COMPLETED,
        ChunkingResult.is_active == True
    )
    
    # Apply strategy filter if provided
    if strategy_type:
        try:
            strategy_enum = StrategyType[strategy_type.upper()]
            query = query.filter(ChunkingTask.chunking_strategy == strategy_enum)
        except KeyError:
            raise ValidationError(f"Invalid strategy type: {strategy_type}")
    
    # Apply parameters filter if provided
    if parameters:
        try:
            import json
            params_dict = json.loads(parameters)
            params_json = json.dumps(params_dict, sort_keys=True)
            
            # Filter by exact parameter match
            query = query.filter(
                func.json_extract(ChunkingResult.chunking_params, '$') == params_json
            )
        except json.JSONDecodeError:
            raise ValidationError("Invalid parameters JSON")
    
    # Get the most recent result
    result = query.order_by(ChunkingResult.created_at.desc()).first()
    
    if not result:
        return success_response(
            data=None,
            message="No chunking results found for this document"
        )
    
    # Get associated task info
    task = db.query(ChunkingTask).filter(ChunkingTask.task_id == result.task_id).first()
    
    return success_response(
        data={
            "result_id": result.result_id,
            "task_id": result.task_id,
            "document_id": result.document_id,
            "document_name": result.document_name,
            "strategy_type": result.chunking_strategy.value,
            "parameters": result.chunking_params,
            "status": result.status.value,
            "total_chunks": result.total_chunks,
            "statistics": result.statistics,
            "version": result.version,
            "is_active": result.is_active,
            "processing_time": result.processing_time,
            "created_at": result.created_at.isoformat() if result.created_at else None
        }
    )


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


# Get latest chunking result for a document (optionally filtered by strategy and parameters)
@router.get("/result/latest/{document_id}")
async def get_latest_result_for_document(
    document_id: str,
    strategy_type: Optional[str] = Query(None, description="Filter by strategy type"),
    parameters: Optional[str] = Query(None, description="Filter by parameters (JSON string)"),
    db: Session = Depends(get_db)
):
    """
    Get the latest active chunking result for a document.
    Can optionally filter by strategy type and/or parameters.
    
    Args:
        document_id: Document ID
        strategy_type: Optional strategy type filter
        parameters: Optional parameters filter (JSON string)
        db: Database session
        
    Returns:
        Latest chunking result or null if none exists
    """
    from ..models.chunking_result import ResultStatus
    
    # Start with base query for this document
    query = db.query(ChunkingResult).join(
        ChunkingTask,
        ChunkingResult.task_id == ChunkingTask.task_id
    ).filter(
        ChunkingTask.source_document_id == document_id,
        ChunkingResult.status == ResultStatus.COMPLETED,
        ChunkingResult.is_active == True
    )
    
    # Apply strategy filter if provided
    if strategy_type:
        try:
            strategy_enum = StrategyType[strategy_type.upper()]
            query = query.filter(ChunkingTask.chunking_strategy == strategy_enum)
        except KeyError:
            raise ValidationError(f"Invalid strategy type: {strategy_type}")
    
    # Apply parameters filter if provided
    if parameters:
        try:
            import json
            params_dict = json.loads(parameters)
            params_json = json.dumps(params_dict, sort_keys=True)
            
            # Filter by exact parameter match
            query = query.filter(
                func.json_extract(ChunkingResult.chunking_params, '$') == params_json
            )
        except json.JSONDecodeError:
            raise ValidationError("Invalid parameters JSON")
    
    # Get the most recent result
    result = query.order_by(ChunkingResult.created_at.desc()).first()
    
    if not result:
        return success_response(
            data=None,
            message="No chunking results found for this document"
        )
    
    # Get associated task info
    task = db.query(ChunkingTask).filter(ChunkingTask.task_id == result.task_id).first()
    
    return success_response(
        data={
            "result_id": result.result_id,
            "task_id": result.task_id,
            "document_id": result.document_id,
            "document_name": result.document_name,
            "strategy_type": result.chunking_strategy.value,
            "parameters": result.chunking_params,
            "status": result.status.value,
            "total_chunks": result.total_chunks,
            "statistics": result.statistics,
            "version": result.version,
            "is_active": result.is_active,
            "processing_time": result.processing_time,
            "created_at": result.created_at.isoformat() if result.created_at else None
        }
    )
