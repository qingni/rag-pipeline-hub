"""Document loading service."""
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from ..models.document import Document
from ..models.processing_result import ProcessingResult
from ..providers.loaders.pymupdf_loader import pymupdf_loader
from ..providers.loaders.pypdf_loader import pypdf_loader
from ..providers.loaders.unstructured_loader import unstructured_loader
from ..storage.json_storage import json_storage
from ..utils.error_handlers import NotFoundError, ProcessingError


class LoadingService:
    """Service for loading documents with different loaders."""
    
    def __init__(self):
        """Initialize loading service."""
        self.loaders = {
            "pymupdf": pymupdf_loader,
            "pypdf": pypdf_loader,
            "unstructured": unstructured_loader
        }
    
    def load_document(
        self,
        db: Session,
        document_id: str,
        loader_type: str = "pymupdf"
    ) -> ProcessingResult:
        """
        Load document using specified loader.
        
        Args:
            db: Database session
            document_id: Document identifier
            loader_type: Type of loader to use
            
        Returns:
            ProcessingResult instance
            
        Raises:
            NotFoundError: If document not found
            ProcessingError: If loading fails
        """
        # Get document
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise NotFoundError("Document", document_id)
        
        # Get loader
        loader = self.loaders.get(loader_type)
        if not loader:
            raise ProcessingError(
                f"Unknown loader type: {loader_type}",
                {"available_loaders": list(self.loaders.keys())}
            )
        
        # Create processing result
        processing_result = ProcessingResult(
            document_id=document_id,
            processing_type="load",
            provider=loader_type,
            result_path="",  # Will be set after saving JSON
            status="running"
        )
        db.add(processing_result)
        db.commit()
        db.refresh(processing_result)
        
        try:
            # Load document
            result_data = loader.extract_text(document.storage_path)
            
            if not result_data.get("success"):
                raise ProcessingError(
                    f"Loading failed: {result_data.get('error', 'Unknown error')}"
                )
            
            # Save result as JSON
            result_path = json_storage.save_result(
                document.filename,
                "load",
                result_data
            )
            
            # Update processing result
            processing_result.result_path = result_path
            processing_result.status = "completed"
            processing_result.extra_metadata = {
                "total_pages": result_data.get("total_pages", 0),
                "total_chars": result_data.get("total_chars", 0)
            }
            
            # Update document status
            document.status = "ready"
            
            db.commit()
            db.refresh(processing_result)
            
            return processing_result
            
        except Exception as e:
            processing_result.status = "failed"
            processing_result.error_message = str(e)
            db.commit()
            raise ProcessingError(f"Loading failed: {str(e)}")


# Global instance
loading_service = LoadingService()
