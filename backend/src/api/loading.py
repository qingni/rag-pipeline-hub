"""Document loading API endpoints.

Enhanced loading API with Docling integration and fallback strategy support.
Includes async loading endpoints for large files.
Supports multi-task queue management for parallel processing.
"""
from fastapi import APIRouter, Depends, Query, Path, Body
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Optional, List
from ..storage.database import get_db
from ..services.loading_service import loading_service
from ..services.task_queue_service import task_queue_service
from ..utils.formatters import success_response, processing_result_to_dict
from ..utils.validators import validate_document_id

router = APIRouter()


class LoadRequest(BaseModel):
    """Load document request."""
    document_id: str = Field(..., description="Document ID to load")
    loader_type: Optional[str] = Field(
        None,
        description="Loader type to use. If not specified, auto-selects based on format and size."
    )
    enable_fallback: bool = Field(
        True,
        description="Whether to enable fallback to other loaders if primary fails"
    )


class AsyncLoadRequest(BaseModel):
    """Async load document request."""
    document_id: str = Field(..., description="Document ID to load")
    loader_type: Optional[str] = Field(
        None,
        description="Loader type to use. For async, typically 'docling_serve'"
    )


class BatchStatusRequest(BaseModel):
    """Batch task status request."""
    task_ids: List[str] = Field(..., description="List of task IDs to query")


# ==================== 任务队列 API ====================

@router.get("/load/queue/stats")
async def get_queue_stats():
    """
    Get task queue statistics.
    
    Returns queue status including:
    - Total tasks count
    - Tasks by status (pending, running, success, failure)
    - Tasks by category (local_fast, local_medium, local_heavy, remote)
    - Pool configurations
    """
    stats = task_queue_service.get_queue_stats()
    
    return success_response(
        data=stats,
        message="Queue stats retrieved"
    )


@router.get("/load/queue/active")
async def get_active_tasks():
    """
    Get all active tasks in the queue.
    
    Returns tasks that are currently pending, queued, or running.
    """
    tasks = task_queue_service.get_active_tasks()
    
    return success_response(
        data={
            "tasks": tasks,
            "total": len(tasks)
        },
        message="Active tasks retrieved"
    )


@router.post("/load/queue/batch-status")
async def get_batch_task_status(
    request: BatchStatusRequest
):
    """
    Get status for multiple tasks in one request.
    
    Reduces frontend polling overhead by fetching multiple task statuses at once.
    
    Args:
        request: Contains list of task_ids to query
        
    Returns:
        Dictionary mapping task_id to task status
    """
    statuses = task_queue_service.get_batch_status(request.task_ids)
    
    return success_response(
        data={
            "statuses": statuses,
            "queried": len(request.task_ids),
            "found": len(statuses)
        },
        message="Batch status retrieved"
    )


# ==================== 异步加载 API (放在前面避免路由冲突) ====================

@router.post("/load/async")
async def load_document_async(
    request: AsyncLoadRequest,
    db: Session = Depends(get_db)
):
    """
    Submit async document loading task.
    
    For large files or complex documents, this endpoint submits the task
    to Docling Serve's async API and returns immediately with a task_id.
    
    Use GET /load/task/{task_id}/status to poll for progress.
    Use GET /load/task/{task_id}/result to get the final result.
    
    Returns:
        task_id: Unique task identifier
        status: Initial task status (pending)
    """
    validate_document_id(request.document_id)
    
    result = loading_service.submit_async_load(
        db=db,
        document_id=request.document_id,
        loader_type=request.loader_type
    )
    
    return success_response(
        data=result,
        message="Async loading task submitted"
    )


@router.get("/load/tasks")
async def list_load_tasks(
    document_id: Optional[str] = Query(None, description="Filter by document ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(20, ge=1, le=100, description="Max results"),
    db: Session = Depends(get_db)
):
    """
    List async loading tasks.
    
    Returns recent loading tasks with optional filters.
    """
    tasks = loading_service.list_async_tasks(
        db=db,
        document_id=document_id,
        status=status,
        limit=limit
    )
    
    return success_response(
        data={
            "tasks": tasks,
            "total": len(tasks)
        }
    )


@router.get("/load/task/{task_id}/status")
async def get_load_task_status(
    task_id: str = Path(..., description="Loading task ID"),
    db: Session = Depends(get_db)
):
    """
    Get async loading task status.
    
    Poll this endpoint to check task progress.
    
    Returns:
        status: pending/started/success/failure
        progress: 0-100 (if available)
    """
    result = await loading_service.get_async_task_status(db, task_id)
    
    return success_response(
        data=result,
        message="Task status retrieved"
    )


@router.get("/load/task/{task_id}/result")
async def get_load_task_result(
    task_id: str = Path(..., description="Loading task ID"),
    db: Session = Depends(get_db)
):
    """
    Get async loading task result.
    
    Call this after task status is 'success' to get the parsed content.
    
    Returns:
        Full loading result with parsed content
    """
    result = loading_service.get_async_task_result(db, task_id)
    
    return success_response(
        data=result,
        message="Task result retrieved"
    )


@router.post("/load/task/{task_id}/cancel")
async def cancel_load_task(
    task_id: str = Path(..., description="Loading task ID"),
    db: Session = Depends(get_db)
):
    """
    Cancel an async loading task.
    
    Note: Cancellation may not be immediate if the task is already processing.
    """
    result = loading_service.cancel_async_task(db, task_id)
    
    return success_response(
        data=result,
        message="Task cancellation requested"
    )


# ==================== 同步加载 API ====================

@router.post("/load")
async def load_document(
    request: LoadRequest,
    db: Session = Depends(get_db)
):
    """
    Load and parse document with specified or auto-selected loader.
    
    Supports multiple document formats with Docling as the primary parser:
    - PDF: docling (primary), pymupdf, pypdf, unstructured
    - DOCX: docling (primary), python-docx, unstructured
    - XLSX: docling (primary), openpyxl, unstructured
    - PPTX: docling (primary), python-pptx, unstructured
    - HTML/CSV/TXT/MD: Specialized loaders
    - And 15+ more formats
    
    Features:
    - Automatic fallback to backup parsers on failure
    - Intelligent loader selection based on file size
    - Structured content extraction (tables, images, formulas)
    - Unified output format
    
    Args:
        request: Load request data
        db: Database session
        
    Returns:
        Processing result with loading details
    """
    validate_document_id(request.document_id)
    
    result = loading_service.load_document(
        db=db,
        document_id=request.document_id,
        loader_type=request.loader_type,
        enable_fallback=request.enable_fallback
    )
    
    return success_response(
        data=processing_result_to_dict(result),
        message="Document loaded successfully"
    )


@router.post("/load/{document_id}")
async def load_document_by_path(
    document_id: str = Path(..., description="Document ID to load"),
    loader_type: Optional[str] = Query(
        None,
        description="Loader type to use"
    ),
    enable_fallback: bool = Query(
        True,
        description="Whether to enable fallback"
    ),
    db: Session = Depends(get_db)
):
    """
    Load document by path parameter.
    
    Alternative endpoint that accepts document_id as path parameter.
    """
    validate_document_id(document_id)
    
    result = loading_service.load_document(
        db=db,
        document_id=document_id,
        loader_type=loader_type,
        enable_fallback=enable_fallback
    )
    
    return success_response(
        data=processing_result_to_dict(result),
        message="Document loaded successfully"
    )


@router.get("/load/{document_id}/result")
async def get_loading_result(
    document_id: str = Path(..., description="Document ID"),
    loader_type: Optional[str] = Query(
        None,
        description="Get result from specific loader"
    ),
    db: Session = Depends(get_db)
):
    """
    Get loading result for a document.
    
    Returns the parsed content and metadata from the most recent loading operation.
    """
    validate_document_id(document_id)
    
    result = loading_service.get_loading_result(
        db=db,
        document_id=document_id,
        loader_type=loader_type
    )
    
    if result is None:
        return success_response(
            data=None,
            message="No loading result found"
        )
    
    return success_response(
        data=result,
        message="Loading result retrieved"
    )


@router.get("/loaders")
async def get_available_loaders():
    """
    Get list of available loaders with their configurations.
    
    Returns detailed information about each loader including:
    - Supported formats
    - Quality level
    - Speed characteristics
    - Availability status
    - Required dependencies
    """
    loaders = loading_service.get_available_loaders()
    
    return success_response(
        data={
            "loaders": loaders,
            "total": len(loaders)
        }
    )


@router.get("/loaders/formats")
async def get_supported_formats():
    """
    Get list of supported file formats and their parsing strategies.
    
    Returns format-to-loader mapping with fallback chains.
    """
    formats = loading_service.get_supported_formats()
    strategies = loading_service.get_format_strategies()
    
    return success_response(
        data={
            "formats": formats,
            "strategies": strategies,
            "total": len(formats)
        }
    )


@router.get("/loaders/recommend")
async def get_recommended_loader(
    format: str = Query(..., description="File format (e.g., pdf, docx)"),
    size_bytes: int = Query(0, description="File size in bytes")
):
    """
    Get recommended loader for a specific file format and size.
    
    Uses intelligent selection based on:
    - File format
    - File size (larger files may use faster loaders)
    - Loader availability
    """
    recommended = loading_service.get_recommended_loader(format, size_bytes)
    
    return success_response(
        data={
            "format": format,
            "size_bytes": size_bytes,
            "recommended_loader": recommended
        }
    )
