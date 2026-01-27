"""Document management API endpoints."""
from fastapi import APIRouter, UploadFile, File, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from ..storage.database import get_db
from ..storage.file_storage import file_storage
from ..storage.json_storage import json_storage
from ..models.document import Document
from ..models.processing_result import ProcessingResult
from ..utils.validators import validate_file_upload
from ..utils.formatters import success_response, paginated_response, document_to_dict
from ..utils.error_handlers import NotFoundError
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor

# 线程池用于执行 IO 密集型操作，避免阻塞事件循环
_io_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="file_io")

router = APIRouter()


@router.post("/documents")
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload a new document.
    
    Args:
        file: Uploaded file
        db: Database session
        
    Returns:
        Document information
    """
    # Validate file
    validate_file_upload(file.file, file.filename)
    
    # Check for duplicate filename
    existing_doc = db.query(Document).filter(
        Document.filename == file.filename
    ).first()
    
    if existing_doc:
        from ..utils.error_handlers import ValidationError
        raise ValidationError(f"文件 '{file.filename}' 已存在，请勿重复上传")
    
    # 读取文件内容（UploadFile 是异步的，需要先读取）
    file_content = await file.read()
    filename = file.filename
    
    # 在线程池中执行 IO 密集型操作，避免阻塞事件循环
    loop = asyncio.get_event_loop()
    storage_path, content_hash = await loop.run_in_executor(
        _io_executor,
        lambda: file_storage.save_upload_bytes(file_content, filename)
    )
    
    # Get file size
    file_size = os.path.getsize(storage_path)
    
    # Get file format
    file_ext = os.path.splitext(file.filename)[1].lower().replace(".", "")
    
    # Create document record
    document = Document(
        filename=file.filename,
        format=file_ext,
        size_bytes=file_size,
        storage_path=storage_path,
        content_hash=content_hash,
        status="uploaded"
    )
    
    db.add(document)
    db.commit()
    db.refresh(document)
    
    return success_response(
        data=document_to_dict(document),
        message="Document uploaded successfully"
    )


@router.get("/documents")
async def list_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    has_chunking_result: Optional[bool] = Query(None, description="Filter documents with/without chunking results"),
    db: Session = Depends(get_db)
):
    """
    Get list of documents with pagination.
    
    Args:
        page: Page number
        page_size: Items per page
        status: Filter by status
        has_chunking_result: Filter documents with active chunking results
        db: Database session
        
    Returns:
        Paginated list of documents
    """
    query = db.query(Document)
    
    if status:
        query = query.filter(Document.status == status)
    
    # Filter by chunking result availability
    if has_chunking_result is not None:
        from ..models.chunking_result import ChunkingResult, ResultStatus
        from ..models.chunking_task import ChunkingTask
        
        if has_chunking_result:
            # Only show documents with active chunking results
            query = query.join(
                ChunkingTask,
                ChunkingTask.source_document_id == Document.id
            ).join(
                ChunkingResult,
                ChunkingResult.task_id == ChunkingTask.task_id
            ).filter(
                ChunkingResult.status == ResultStatus.COMPLETED,
                ChunkingResult.is_active == True
            ).distinct()
        else:
            # Only show documents without any chunking results
            from sqlalchemy import exists, and_
            has_result = exists().where(
                and_(
                    ChunkingTask.source_document_id == Document.id,
                    ChunkingResult.task_id == ChunkingTask.task_id,
                    ChunkingResult.status == ResultStatus.COMPLETED,
                    ChunkingResult.is_active == True
                )
            )
            query = query.filter(~has_result)
    
    # Get total count
    total = query.count()
    
    # Get paginated results
    offset = (page - 1) * page_size
    documents = query.order_by(Document.upload_time.desc()).offset(offset).limit(page_size).all()
    
    # 获取每个文档的加载耗时
    document_ids = [d.id for d in documents]
    loading_results = {}
    if document_ids:
        # 查询每个文档最新的加载结果
        from sqlalchemy import func
        subquery = db.query(
            ProcessingResult.document_id,
            func.max(ProcessingResult.created_at).label('max_created_at')
        ).filter(
            ProcessingResult.document_id.in_(document_ids),
            ProcessingResult.processing_type == "load",
            ProcessingResult.status == "completed"
        ).group_by(ProcessingResult.document_id).subquery()
        
        results = db.query(ProcessingResult).join(
            subquery,
            (ProcessingResult.document_id == subquery.c.document_id) &
            (ProcessingResult.created_at == subquery.c.max_created_at)
        ).all()
        
        for r in results:
            loading_results[r.document_id] = {
                'loading_time': r.extra_metadata.get('processing_time') if r.extra_metadata else None,
                'provider': r.provider
            }
    
    # 构建返回数据，包含加载耗时和解析器
    items = []
    for d in documents:
        doc_dict = document_to_dict(d)
        result_info = loading_results.get(d.id, {})
        doc_dict['loading_time'] = result_info.get('loading_time')
        doc_dict['provider'] = result_info.get('provider')
        items.append(doc_dict)
    
    return success_response(
        data=paginated_response(
            items=items,
            total=total,
            page=page,
            page_size=page_size
        )
    )


@router.get("/documents/{document_id}")
async def get_document(
    document_id: str,
    db: Session = Depends(get_db)
):
    """
    Get document by ID.
    
    Args:
        document_id: Document identifier
        db: Database session
        
    Returns:
        Document information
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise NotFoundError("Document", document_id)
    
    return success_response(data=document_to_dict(document))


@router.get("/documents/{document_id}/preview")
async def preview_document(
    document_id: str,
    pages: int = Query(3, ge=1, le=10),
    db: Session = Depends(get_db)
):
    """
    Get document preview.
    
    Supports multiple document formats:
    - PDF, DOCX, DOC, TXT, Markdown
    
    Args:
        document_id: Document identifier
        pages: Number of pages to preview (for multi-page documents)
        db: Database session
        
    Returns:
        Preview content
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise NotFoundError("Document", document_id)
    
    # 调试日志：打印文档状态
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"[Preview] Document {document_id}: status={document.status}, filename={document.filename}")
    
    # 检查文档状态，只有已加载的文档才能预览
    if document.status == "uploaded":
        return success_response(
            data={
                "preview_text": "",
                "page_count": 0,
                "status": "not_loaded",
                "message": "文档尚未加载，请先点击「开始加载」按钮解析文档内容"
            }
        )
    
    if document.status == "processing":
        return success_response(
            data={
                "preview_text": "",
                "page_count": 0,
                "status": "processing",
                "message": "文档正在加载中，请稍候..."
            }
        )
    
    if document.status == "error":
        return success_response(
            data={
                "preview_text": "",
                "page_count": 0,
                "status": "error",
                "message": "文档加载失败，请重试"
            }
        )
    
    # 文档状态是 ready，优先从已保存的加载结果中读取
    if document.status == "ready":
        # 查找该文档的加载结果
        loading_result = db.query(ProcessingResult).filter(
            ProcessingResult.document_id == document_id,
            ProcessingResult.processing_type == "load"
        ).order_by(ProcessingResult.created_at.desc()).first()
        
        if loading_result and loading_result.result_path:
            try:
                result_data = json_storage.load_result(loading_result.result_path)
                if result_data:
                    # 优先使用 full_text（Docling 返回的完整 Markdown）
                    full_text = result_data.get("full_text", "")
                    
                    if full_text:
                        # 返回完整内容，不截断（避免截断 base64 图片）
                        preview_text = full_text
                    else:
                        # 降级：从 pages 数组获取
                        preview_pages = result_data.get("pages", [])[:pages]
                        # 不截断单页内容，保持完整的 Markdown 结构
                        preview_text = "\n\n".join([p.get("text", "") for p in preview_pages])
                    
                    return success_response(
                        data={
                            "preview_text": preview_text,
                            "page_count": result_data.get("total_pages", len(result_data.get("pages", []))),
                            "total_pages": result_data.get("total_pages", 0),
                            "total_chars": result_data.get("total_chars", 0),
                            "loader_used": result_data.get("loader", "unknown"),
                            "status": "ready",
                            "metadata": result_data.get("metadata", {}),
                            "pages": result_data.get("pages", [])
                        }
                    )
            except Exception as e:
                # 如果读取结果文件失败，继续使用 loader 重新解析
                pass
    
    # 如果没有保存的结果或读取失败，使用 loader 解析
    from ..services.loading_service import loading_service
    
    file_format = document.format.lower()
    loader_type = loading_service.get_loader_for_format(file_format)
    
    if not loader_type:
        return success_response(
            data={
                "preview_text": f"Preview not available for {file_format} format",
                "page_count": 0
            }
        )
    
    try:
        loader = loading_service.loaders.get(loader_type)
        result = loader.extract_text(document.storage_path)
        
        if result.get("success"):
            # 优先使用 full_text（完整 Markdown）
            full_text = result.get("full_text", "")
            
            if full_text:
                # 返回完整内容，不截断
                preview_text = full_text
                page_count = result.get("total_pages", 1)
            else:
                # 降级：从 pages 数组获取，不截断单页内容
                preview_pages = result.get("pages", [])[:pages]
                preview_text = "\n\n".join([p.get("text", "") for p in preview_pages])
                page_count = len(preview_pages)
            
            return success_response(
                data={
                    "preview_text": preview_text,
                    "page_count": page_count,
                    "total_pages": result.get("total_pages", 0),
                    "total_chars": result.get("total_chars", 0),
                    "loader_used": loader_type,
                    "status": "ready"
                }
            )
        else:
            return success_response(
                data={
                    "preview_text": f"Preview not available: {result.get('error', 'Unknown error')}",
                    "page_count": 0,
                    "status": "error"
                }
            )
    except Exception as e:
        return success_response(
            data={
                "preview_text": f"Preview generation failed: {str(e)}",
                "page_count": 0,
                "status": "error"
            }
        )


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: str,
    db: Session = Depends(get_db)
):
    """
    Delete document and all related data.
    
    Args:
        document_id: Document identifier
        db: Database session
        
    Returns:
        Success message
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise NotFoundError("Document", document_id)
    
    # Delete file from storage
    file_storage.delete_file(document.storage_path)
    
    # Delete processing results JSON files
    from ..models.processing_result import ProcessingResult
    from ..models.loading_task import LoadingTask
    from ..storage.json_storage import json_storage
    
    results = db.query(ProcessingResult).filter(
        ProcessingResult.document_id == document_id
    ).all()
    
    for result in results:
        json_storage.delete_result(result.result_path)
    
    # Delete loading tasks (SQLite doesn't enforce ON DELETE CASCADE on existing tables)
    db.query(LoadingTask).filter(LoadingTask.document_id == document_id).delete()
    
    # Delete document (cascade will delete processing results)
    db.delete(document)
    db.commit()
    
    return success_response(
        data=None,
        message="Document deleted successfully"
    )
