"""Chunking history and management endpoints."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func
from typing import Optional, List
from datetime import datetime
from ..storage.database import get_db
from ..models.chunking_result import ChunkingResult
from ..models.document import Document
from ..utils.formatters import success_response, paginated_response
from ..utils.error_handlers import NotFoundError
import os

router = APIRouter()


@router.get("/history")
async def get_chunking_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    document_name: Optional[str] = Query(None, description="Filter by document name"),
    strategy: Optional[str] = Query(None, description="Filter by strategy type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    date_from: Optional[str] = Query(None, description="Filter from date (ISO format)"),
    date_to: Optional[str] = Query(None, description="Filter to date (ISO format)"),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order (asc/desc)"),
    db: Session = Depends(get_db)
):
    """
    Get chunking history with filtering, sorting, and pagination.
    
    Args:
        page: Page number
        page_size: Items per page
        document_name: Filter by document name (partial match)
        strategy: Filter by chunking strategy
        status: Filter by result status
        date_from: Filter from date
        date_to: Filter to date
        sort_by: Sort field
        sort_order: Sort order
        db: Database session
        
    Returns:
        Paginated history list
    """
    query = db.query(ChunkingResult)
    
    # Apply filters
    if document_name:
        query = query.filter(ChunkingResult.document_name.like(f"%{document_name}%"))
    
    if strategy:
        from ..models.chunking_task import StrategyType
        query = query.filter(ChunkingResult.chunking_strategy == StrategyType[strategy.upper()])
    
    if status:
        from ..models.chunking_result import ResultStatus
        query = query.filter(ChunkingResult.status == ResultStatus[status.upper()])
    
    if date_from:
        try:
            date_obj = datetime.fromisoformat(date_from)
            query = query.filter(ChunkingResult.created_at >= date_obj)
        except ValueError:
            pass
    
    if date_to:
        try:
            date_obj = datetime.fromisoformat(date_to)
            query = query.filter(ChunkingResult.created_at <= date_obj)
        except ValueError:
            pass
    
    # Apply sorting
    sort_field = getattr(ChunkingResult, sort_by, ChunkingResult.created_at)
    if sort_order.lower() == "desc":
        query = query.order_by(sort_field.desc())
    else:
        query = query.order_by(sort_field.asc())
    
    # Get total count
    total = query.count()
    
    # Paginate
    offset = (page - 1) * page_size
    results = query.offset(offset).limit(page_size).all()
    
    # Format results
    items = []
    for result in results:
        items.append({
            "result_id": result.result_id,
            "document_id": result.document_id,
            "document_name": result.document_name,
            "strategy_type": result.chunking_strategy.value,
            "status": result.status.value,
            "total_chunks": result.total_chunks,
            "processing_time": result.processing_time,
            "file_size": result.file_size,
            "statistics": result.statistics,
            "created_at": result.created_at.isoformat() if result.created_at else None
        })
    
    return success_response(
        data=paginated_response(
            items=items,
            total=total,
            page=page,
            page_size=page_size
        )
    )


@router.post("/compare")
async def compare_results(
    result_ids: List[str],
    db: Session = Depends(get_db)
):
    """
    Compare multiple chunking results.
    
    Args:
        result_ids: List of result IDs to compare
        db: Database session
        
    Returns:
        Comparison data
    """
    if len(result_ids) < 2:
        from ..utils.error_handlers import ValidationError
        raise ValidationError("At least 2 results required for comparison")
    
    if len(result_ids) > 5:
        from ..utils.error_handlers import ValidationError
        raise ValidationError("Maximum 5 results can be compared at once")
    
    # Fetch results
    results = []
    for result_id in result_ids:
        result = db.query(ChunkingResult).filter(
            ChunkingResult.result_id == result_id
        ).first()
        
        if not result:
            raise NotFoundError("ChunkingResult", result_id)
        
        results.append(result)
    
    # Build comparison data
    comparison = {
        "results": [],
        "statistics_comparison": {},
        "recommendations": []
    }
    
    for result in results:
        comparison["results"].append({
            "result_id": result.result_id,
            "document_name": result.document_name,
            "strategy_type": result.chunking_strategy.value,
            "total_chunks": result.total_chunks,
            "processing_time": result.processing_time,
            "statistics": result.statistics,
            "parameters": result.chunking_params
        })
    
    # Statistical comparison
    comparison["statistics_comparison"] = {
        "avg_chunk_sizes": [r.statistics.get("avg_chunk_size", 0) for r in results],
        "max_chunk_sizes": [r.statistics.get("max_chunk_size", 0) for r in results],
        "min_chunk_sizes": [r.statistics.get("min_chunk_size", 0) for r in results],
        "total_chunks": [r.total_chunks for r in results],
        "processing_times": [r.processing_time for r in results]
    }
    
    # Simple recommendations
    fastest = min(results, key=lambda r: r.processing_time)
    most_balanced = min(results, key=lambda r: abs(
        r.statistics.get("max_chunk_size", 0) - r.statistics.get("avg_chunk_size", 0)
    ))
    
    comparison["recommendations"] = [
        f"最快处理: {fastest.chunking_strategy.value} ({fastest.processing_time:.2f}s)",
        f"最均衡分块: {most_balanced.chunking_strategy.value}"
    ]
    
    return success_response(data=comparison)


@router.delete("/result/{result_id}")
async def delete_result(
    result_id: str,
    db: Session = Depends(get_db)
):
    """
    Delete chunking result (database record and JSON file).
    
    Args:
        result_id: Result ID to delete
        db: Database session
        
    Returns:
        Success message
    """
    result = db.query(ChunkingResult).filter(
        ChunkingResult.result_id == result_id
    ).first()
    
    if not result:
        raise NotFoundError("ChunkingResult", result_id)
    
    # Delete JSON file
    if result.json_file_path and os.path.exists(result.json_file_path):
        try:
            os.remove(result.json_file_path)
        except Exception as e:
            print(f"Failed to delete file {result.json_file_path}: {e}")
    
    # Delete database record (cascades to chunks)
    db.delete(result)
    db.commit()
    
    return success_response(
        data=None,
        message="Result deleted successfully"
    )


@router.get("/export/{result_id}")
async def export_result(
    result_id: str,
    format: str = Query("json", regex="^(json|csv)$"),
    db: Session = Depends(get_db)
):
    """
    Export chunking result in JSON or CSV format.
    
    Args:
        result_id: Result ID to export
        format: Export format (json or csv)
        db: Database session
        
    Returns:
        Export file or data
    """
    from fastapi.responses import FileResponse, StreamingResponse
    import json
    import csv
    import io
    
    result = db.query(ChunkingResult).filter(
        ChunkingResult.result_id == result_id
    ).first()
    
    if not result:
        raise NotFoundError("ChunkingResult", result_id)
    
    if format == "json":
        # Return existing JSON file
        if os.path.exists(result.json_file_path):
            return FileResponse(
                result.json_file_path,
                media_type="application/json",
                filename=f"{result.document_name}_{result.chunking_strategy.value}.json"
            )
    
    elif format == "csv":
        # Generate CSV
        from ..models.chunk import Chunk
        
        chunks = db.query(Chunk).filter(
            Chunk.result_id == result_id
        ).order_by(Chunk.sequence_number).all()
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow([
            "Sequence",
            "Content",
            "Character Count",
            "Start Position",
            "End Position"
        ])
        
        # Data
        for chunk in chunks:
            writer.writerow([
                chunk.sequence_number + 1,
                chunk.content,
                chunk.token_count,
                chunk.start_position,
                chunk.end_position
            ])
        
        output.seek(0)
        
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={result.document_name}_{result.chunking_strategy.value}.csv"
            }
        )
    
    from ..utils.error_handlers import ValidationError
    raise ValidationError(f"Unsupported format: {format}")


@router.get("/queue")
async def get_queue_status():
    """
    Get current queue status.
    
    Returns:
        Queue status information
    """
    from ..services.chunking_queue import queue_manager
    
    status = queue_manager.get_queue_status()
    
    return success_response(data=status)
