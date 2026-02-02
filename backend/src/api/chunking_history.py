"""Chunking history and management endpoints."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func
from typing import Optional, List
from datetime import datetime
from ..storage.database import get_db
from ..models.chunking_result import ChunkingResult
from ..models.document import Document
from ..utils.formatters import success_response, paginated_response, sanitize_statistics
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
    active_only: bool = Query(True, description="Show only active versions"),
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
        active_only: Show only active versions (default: True)
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
    
    if active_only:
        query = query.filter(ChunkingResult.is_active == True)
    
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
        # Enrich statistics with parameters if not present
        stats = sanitize_statistics(result.statistics) or {}
        if 'parameters' not in stats and result.chunking_params:
            stats['parameters'] = result.chunking_params
        
        items.append({
            "result_id": result.result_id,
            "document_id": result.document_id,
            "document_name": result.document_name,
            "strategy_type": result.chunking_strategy.value,
            "status": result.status.value,
            "total_chunks": result.total_chunks,
            "processing_time": result.processing_time,
            "file_size": result.file_size,
            "statistics": stats,
            "version": result.version,
            "is_active": result.is_active,
            "previous_version_id": result.previous_version_id,
            "replacement_reason": result.replacement_reason,
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


@router.get("/versions/{document_id}/{strategy_type}")
async def get_version_history(
    document_id: str,
    strategy_type: str,
    db: Session = Depends(get_db)
):
    """
    Get version history for a specific document and strategy combination.
    
    Args:
        document_id: Document ID
        strategy_type: Strategy type (character/paragraph/heading/semantic)
        db: Database session
        
    Returns:
        List of all versions (active and inactive) ordered by version number
    """
    from ..models.chunking_task import StrategyType
    
    try:
        strategy_enum = StrategyType[strategy_type.upper()]
    except KeyError:
        from ..utils.error_handlers import ValidationError
        raise ValidationError(f"Invalid strategy type: {strategy_type}")
    
    # Query all versions for this document + strategy
    versions = db.query(ChunkingResult).filter(
        ChunkingResult.document_id == document_id,
        ChunkingResult.chunking_strategy == strategy_enum
    ).order_by(ChunkingResult.version.desc()).all()
    
    if not versions:
        return success_response(
            data={
                "document_id": document_id,
                "strategy_type": strategy_type,
                "versions": []
            },
            message="No versions found"
        )
    
    # Format version history
    version_list = []
    for ver in versions:
        version_list.append({
            "result_id": ver.result_id,
            "version": ver.version,
            "is_active": ver.is_active,
            "total_chunks": ver.total_chunks,
            "parameters": ver.chunking_params,
            "processing_time": ver.processing_time,
            "statistics": sanitize_statistics(ver.statistics),
            "previous_version_id": ver.previous_version_id,
            "replacement_reason": ver.replacement_reason,
            "created_at": ver.created_at.isoformat() if ver.created_at else None
        })
    
    return success_response(
        data={
            "document_id": document_id,
            "strategy_type": strategy_type,
            "total_versions": len(version_list),
            "active_version": next((v for v in version_list if v["is_active"]), None),
            "versions": version_list
        }
    )


@router.post("/versions/{result_id}/activate")
async def activate_version(
    result_id: str,
    db: Session = Depends(get_db)
):
    """
    Activate a specific version (deactivate current active version).
    
    Args:
        result_id: Result ID to activate
        db: Database session
        
    Returns:
        Success message
    """
    # Find the result to activate
    result = db.query(ChunkingResult).filter(
        ChunkingResult.result_id == result_id
    ).first()
    
    if not result:
        raise NotFoundError("ChunkingResult", result_id)
    
    # Deactivate all other versions for same document + strategy
    db.query(ChunkingResult).filter(
        ChunkingResult.document_id == result.document_id,
        ChunkingResult.chunking_strategy == result.chunking_strategy,
        ChunkingResult.result_id != result_id
    ).update({"is_active": False})
    
    # Activate this version
    result.is_active = True
    db.commit()
    
    return success_response(
        data={
            "result_id": result_id,
            "version": result.version,
            "is_active": True
        },
        message=f"Version {result.version} activated successfully"
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
            "statistics": sanitize_statistics(result.statistics),
            "parameters": result.chunking_params
        })
    
    # Statistical comparison
    comparison["statistics_comparison"] = {
        "avg_chunk_sizes": [sanitize_statistics(r.statistics).get("avg_chunk_size", 0) for r in results],
        "max_chunk_sizes": [sanitize_statistics(r.statistics).get("max_chunk_size", 0) for r in results],
        "min_chunk_sizes": [sanitize_statistics(r.statistics).get("min_chunk_size", 0) for r in results],
        "total_chunks": [r.total_chunks for r in results],
        "processing_times": [r.processing_time for r in results]
    }
    
    # Simple recommendations
    fastest = min(results, key=lambda r: r.processing_time)
    most_balanced = min(results, key=lambda r: abs(
        sanitize_statistics(r.statistics).get("max_chunk_size", 0) - sanitize_statistics(r.statistics).get("avg_chunk_size", 0)
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
    if result.json_file_path:
        from pathlib import Path
        from ..config import settings
        
        # Handle relative paths (relative to backend directory)
        file_path = Path(result.json_file_path)
        if not file_path.is_absolute():
            # Path is relative to backend directory, resolve via RESULTS_DIR
            file_path = Path(settings.RESULTS_DIR).parent / result.json_file_path
        
        if file_path.exists():
            try:
                file_path.unlink()
            except Exception as e:
                print(f"Failed to delete file {file_path}: {e}")
    
    # Delete database record (cascades to chunks)
    db.delete(result)
    db.commit()
    
    return success_response(
        data=None,
        message="Result deleted successfully"
    )


@router.post("/results/batch-delete")
async def batch_delete_results(
    result_ids: List[str],
    db: Session = Depends(get_db)
):
    """
    Batch delete chunking results.
    
    Args:
        result_ids: List of result IDs to delete
        db: Database session
        
    Returns:
        Deletion summary
    """
    from pathlib import Path
    from ..config import settings
    
    if not result_ids:
        from ..utils.error_handlers import ValidationError
        raise ValidationError("No result IDs provided")
    
    deleted_count = 0
    failed_ids = []
    
    for result_id in result_ids:
        result = db.query(ChunkingResult).filter(
            ChunkingResult.result_id == result_id
        ).first()
        
        if not result:
            failed_ids.append(result_id)
            continue
        
        # Delete JSON file
        if result.json_file_path:
            file_path = Path(result.json_file_path)
            if not file_path.is_absolute():
                file_path = Path(settings.RESULTS_DIR).parent / result.json_file_path
            
            if file_path.exists():
                try:
                    file_path.unlink()
                except Exception as e:
                    print(f"Failed to delete file {file_path}: {e}")
        
        # Delete database record
        db.delete(result)
        deleted_count += 1
    
    db.commit()
    
    return success_response(
        data={
            "deleted_count": deleted_count,
            "failed_ids": failed_ids,
            "total_requested": len(result_ids)
        },
        message=f"Successfully deleted {deleted_count} result(s)"
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
        from pathlib import Path
        from ..config import settings
        
        # Handle relative paths (relative to backend directory)
        file_path = Path(result.json_file_path)
        if not file_path.is_absolute():
            # Resolve relative to backend directory
            file_path = Path(settings.RESULTS_DIR).parent / result.json_file_path
        
        if file_path.exists():
            return FileResponse(
                str(file_path),
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
