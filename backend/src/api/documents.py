"""Document management API endpoints."""
from fastapi import APIRouter, UploadFile, File, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from ..storage.database import get_db
from ..storage.file_storage import file_storage
from ..models.document import Document
from ..utils.validators import validate_file_upload
from ..utils.formatters import success_response, paginated_response, document_to_dict
from ..utils.error_handlers import NotFoundError
import os

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
    
    # Save file
    storage_path, content_hash = file_storage.save_upload(file.file, file.filename)
    
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
    db: Session = Depends(get_db)
):
    """
    Get list of documents with pagination.
    
    Args:
        page: Page number
        page_size: Items per page
        status: Filter by status
        db: Database session
        
    Returns:
        Paginated list of documents
    """
    query = db.query(Document)
    
    if status:
        query = query.filter(Document.status == status)
    
    # Get total count
    total = query.count()
    
    # Get paginated results
    offset = (page - 1) * page_size
    documents = query.order_by(Document.upload_time.desc()).offset(offset).limit(page_size).all()
    
    return success_response(
        data=paginated_response(
            items=[document_to_dict(d) for d in documents],
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
    
    # Get appropriate loader based on file format
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
            preview_pages = result.get("pages", [])[:pages]
            preview_text = "\n\n".join([p["text"][:500] for p in preview_pages])
            
            return success_response(
                data={
                    "preview_text": preview_text,
                    "page_count": len(preview_pages),
                    "total_pages": result.get("total_pages", 0),
                    "total_chars": result.get("total_chars", 0),
                    "loader_used": loader_type
                }
            )
        else:
            return success_response(
                data={
                    "preview_text": f"Preview not available: {result.get('error', 'Unknown error')}",
                    "page_count": 0
                }
            )
    except Exception as e:
        return success_response(
            data={
                "preview_text": f"Preview generation failed: {str(e)}",
                "page_count": 0
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
    from ..storage.json_storage import json_storage
    
    results = db.query(ProcessingResult).filter(
        ProcessingResult.document_id == document_id
    ).all()
    
    for result in results:
        json_storage.delete_result(result.result_path)
    
    # Delete document (cascade will delete processing results)
    db.delete(document)
    db.commit()
    
    return success_response(
        data=None,
        message="Document deleted successfully"
    )
