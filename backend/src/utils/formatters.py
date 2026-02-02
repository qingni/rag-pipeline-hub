"""Response formatting utilities."""
from typing import Any, Dict, Optional
from datetime import datetime, timezone
import math


def sanitize_statistics(stats: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    清理 statistics 中的无穷大值，确保 JSON 序列化安全。
    
    Args:
        stats: 原始统计数据
        
    Returns:
        清理后的统计数据
    """
    if not stats:
        return {}
    
    def clean_value(value):
        """递归清理值"""
        if isinstance(value, float):
            if math.isinf(value) or math.isnan(value):
                return 0  # 将 inf/nan 替换为 0
            return value
        elif isinstance(value, dict):
            return {k: clean_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [clean_value(item) for item in value]
        return value
    
    return clean_value(stats)


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
        timestamp = datetime.now(timezone.utc)
    
    return {
        "success": True,
        "data": data,
        "message": message,
        "timestamp": timestamp.isoformat()
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
    # 确保时间以UTC格式返回
    upload_time = None
    if document.upload_time:
        # 如果datetime是naive（没有时区信息），假设它是UTC
        if document.upload_time.tzinfo is None:
            # 将naive datetime视为UTC，并添加时区信息
            utc_time = document.upload_time.replace(tzinfo=timezone.utc)
            upload_time = utc_time.isoformat()
        else:
            # 如果已有时区信息，转换为UTC
            upload_time = document.upload_time.astimezone(timezone.utc).isoformat()
    
    return {
        "id": document.id,
        "filename": document.filename,
        "format": document.format,
        "size_bytes": document.size_bytes,
        "upload_time": upload_time,
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
    # 确保时间以UTC格式返回
    created_at = None
    if result.created_at:
        # 如果datetime是naive（没有时区信息），假设它是UTC
        if result.created_at.tzinfo is None:
            # 将naive datetime视为UTC，并添加时区信息
            utc_time = result.created_at.replace(tzinfo=timezone.utc)
            created_at = utc_time.isoformat()
        else:
            # 如果已有时区信息，转换为UTC
            created_at = result.created_at.astimezone(timezone.utc).isoformat()
    
    return {
        "id": result.id,
        "document_id": result.document_id,
        "processing_type": result.processing_type,
        "provider": result.provider,
        "result_path": result.result_path,
        "metadata": result.extra_metadata,
        "created_at": created_at,
        "status": result.status,
        "error_message": result.error_message
    }
