"""Response formatting utilities."""
from typing import Any, Dict, Optional
from datetime import datetime


def success_response(
    data: Any,
    message: str = "Operation successful",
    timestamp: Optional[datetime] = None
) -> Dict[str, Any]:
    """
    Create standardized success response.
    
    Args:
        data: Response data
        message: Success message
        timestamp: Response timestamp
        
    Returns:
        Formatted response dictionary
    """
    if timestamp is None:
        timestamp = datetime.utcnow()
    
    return {
        "success": True,
        "data": data,
        "message": message,
        "timestamp": timestamp.isoformat() + "Z"
    }


def paginated_response(
    items: list,
    total: int,
    page: int,
    page_size: int
) -> Dict[str, Any]:
    """
    Create paginated response.
    
    Args:
        items: List of items for current page
        total: Total number of items
        page: Current page number
        page_size: Items per page
        
    Returns:
        Paginated response data
    """
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }


def document_to_dict(document: Any) -> Dict[str, Any]:
    """
    Convert Document model to dictionary.
    
    Args:
        document: Document model instance
        
    Returns:
        Dictionary representation
    """
    return {
        "id": document.id,
        "filename": document.filename,
        "format": document.format,
        "size_bytes": document.size_bytes,
        "upload_time": document.upload_time.isoformat() if document.upload_time else None,
        "storage_path": document.storage_path,
        "content_hash": document.content_hash,
        "status": document.status
    }


def processing_result_to_dict(result: Any) -> Dict[str, Any]:
    """
    Convert ProcessingResult model to dictionary.
    
    Args:
        result: ProcessingResult model instance
        
    Returns:
        Dictionary representation
    """
    return {
        "id": result.id,
        "document_id": result.document_id,
        "processing_type": result.processing_type,
        "provider": result.provider,
        "result_path": result.result_path,
        "metadata": result.extra_metadata,
        "created_at": result.created_at.isoformat() if result.created_at else None,
        "status": result.status,
        "error_message": result.error_message
    }
