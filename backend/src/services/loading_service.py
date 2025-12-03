"""Document loading service."""
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from ..models.document import Document
from ..models.processing_result import ProcessingResult
from ..providers.loaders.pymupdf_loader import pymupdf_loader
from ..providers.loaders.pypdf_loader import pypdf_loader
from ..providers.loaders.unstructured_loader import unstructured_loader
from ..storage.json_storage import json_storage
from ..utils.error_handlers import NotFoundError, ProcessingError
import logging

logger = logging.getLogger(__name__)


class LoadingService:
    """Service for loading and parsing documents into processable text data."""
    
    def __init__(self):
        """Initialize loading service with available loaders."""
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
        Load and parse document using specified loader.
        
        Supports parsing PDF documents into processable text data with:
        - Page-by-page text extraction
        - Metadata extraction
        - Character and page counting
        - Error handling and status tracking
        
        Args:
            db: Database session
            document_id: Document identifier
            loader_type: Type of loader to use (pymupdf, pypdf, unstructured)
            
        Returns:
            ProcessingResult instance with loading results
            
        Raises:
            NotFoundError: If document not found
            ProcessingError: If loading fails
        """
        # Get document
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise NotFoundError("Document", document_id)
        
        # Validate file format
        if document.format.lower() not in ["pdf", "txt"]:
            raise ProcessingError(
                f"Unsupported file format: {document.format}",
                {"supported_formats": ["pdf", "txt"]}
            )
        
        # Get loader
        loader = self.loaders.get(loader_type)
        if not loader:
            raise ProcessingError(
                f"Unknown loader type: {loader_type}",
                {"available_loaders": list(self.loaders.keys())}
            )
        
        logger.info(f"Starting document loading: {document_id} with {loader_type}")
        
        # Update document status
        document.status = "processing"
        db.commit()
        
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
            # Load and parse document
            result_data = loader.extract_text(document.storage_path)
            
            if not result_data.get("success"):
                error_msg = result_data.get("error", "Unknown error")
                logger.error(f"Loading failed for {document_id}: {error_msg}")
                raise ProcessingError(f"Loading failed: {error_msg}")
            
            # Extract statistics
            total_pages = result_data.get("total_pages", 0)
            total_chars = result_data.get("total_chars", 0)
            pages_data = result_data.get("pages", [])
            
            logger.info(
                f"Successfully loaded {document_id}: "
                f"{total_pages} pages, {total_chars} characters"
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
                "total_pages": total_pages,
                "total_chars": total_chars,
                "loader_type": loader_type,
                "file_format": document.format
            }
            
            # Update document status
            document.status = "ready"
            
            db.commit()
            db.refresh(processing_result)
            
            logger.info(f"Document loading completed: {document_id}")
            return processing_result
            
        except ProcessingError:
            # Re-raise ProcessingError as-is
            processing_result.status = "failed"
            processing_result.error_message = str(ProcessingError)
            document.status = "error"
            db.commit()
            raise
            
        except Exception as e:
            # Handle unexpected errors
            error_msg = f"Unexpected error during loading: {str(e)}"
            logger.error(f"Loading failed for {document_id}: {error_msg}", exc_info=True)
            
            processing_result.status = "failed"
            processing_result.error_message = error_msg
            document.status = "error"
            db.commit()
            
            raise ProcessingError(error_msg)
    
    def get_loading_result(
        self,
        db: Session,
        document_id: str,
        loader_type: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get loading result for a document.
        
        Args:
            db: Database session
            document_id: Document identifier
            loader_type: Optional specific loader type to retrieve
            
        Returns:
            Loading result data or None if not found
        """
        query = db.query(ProcessingResult).filter(
            ProcessingResult.document_id == document_id,
            ProcessingResult.processing_type == "load"
        )
        
        if loader_type:
            query = query.filter(ProcessingResult.provider == loader_type)
        
        result = query.order_by(ProcessingResult.created_time.desc()).first()
        
        if not result or not result.result_path:
            return None
        
        # Load JSON data
        try:
            return json_storage.load_result(result.result_path)
        except Exception as e:
            logger.error(f"Failed to load result from {result.result_path}: {str(e)}")
            return None
    
    def get_available_loaders(self) -> List[str]:
        """
        Get list of available loader types.
        
        Returns:
            List of loader names
        """
        return list(self.loaders.keys())


# Global instance
loading_service = LoadingService()
