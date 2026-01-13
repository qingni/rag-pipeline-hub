"""Document loading service with Docling integration and fallback strategy.

This service provides document loading capabilities with:
- Docling as the primary parser for high-quality extraction
- Multi-level fallback strategy for reliability
- Intelligent loader selection based on file size and format
- Unified output format (StandardDocumentResult)
"""
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from pathlib import Path
import time
import logging

from ..models.document import Document
from ..models.processing_result import ProcessingResult
from ..models.loading_result import StandardDocumentResult, ExtractionQuality
from ..models.loader_config import LoaderConfig, FormatStrategy
from ..loader_config.format_strategies import (
    FORMAT_STRATEGIES,
    LOADER_REGISTRY,
    get_format_strategy,
    get_loader_config,
    get_supported_formats,
    is_format_supported
)
from ..providers.loaders import (
    LOADER_INSTANCES,
    get_loader,
    pymupdf_loader,
    pypdf_loader,
    unstructured_loader,
    text_loader,
    docx_loader,
    doc_loader,
    docling_loader
)
from ..services.fallback_manager import fallback_manager
from ..storage.json_storage import json_storage
from ..utils.error_handlers import NotFoundError, ProcessingError
from ..utils.result_converter import convert_legacy_result

logger = logging.getLogger(__name__)


class LoadingService:
    """Service for loading and parsing documents into processable text data."""
    
    def __init__(self):
        """Initialize loading service with available loaders."""
        # Register all loaders with fallback manager
        self._register_loaders()
        
        # Legacy format to loader mapping (for backward compatibility)
        self.format_loader_map = {
            fmt: strategy.primary_loader
            for fmt, strategy in FORMAT_STRATEGIES.items()
        }
        
        # Reference to loaders for direct access
        self.loaders = LOADER_INSTANCES
    
    def _register_loaders(self):
        """Register all available loaders with the fallback manager."""
        for name, loader in LOADER_INSTANCES.items():
            fallback_manager.register_loader(name, loader)
    
    def load_document(
        self,
        db: Session,
        document_id: str,
        loader_type: Optional[str] = None,
        enable_fallback: bool = True
    ) -> ProcessingResult:
        """
        Load and parse document using specified or auto-selected loader.
        
        Supports parsing multiple document formats with:
        - Docling as primary parser for PDF, DOCX, XLSX, PPTX
        - Automatic fallback to backup parsers on failure
        - Intelligent selection based on file size
        - Unified output format
        
        Args:
            db: Database session
            document_id: Document identifier
            loader_type: Type of loader to use. If None, auto-selects based on file format.
            enable_fallback: Whether to enable fallback to other loaders
            
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
        
        file_format = document.format.lower().lstrip('.')
        file_path = document.storage_path
        
        # Edge Case: Check if file exists (T059)
        if not Path(file_path).exists():
            raise ProcessingError(
                f"Source file not found: {document.filename}",
                {"file_path": file_path, "hint": "The file may have been deleted or moved"}
            )
        
        # Check if format is supported
        if not is_format_supported(file_format):
            raise ProcessingError(
                f"Unsupported file format: {document.format}",
                {"supported_formats": get_supported_formats()}
            )
        
        # Get file size
        try:
            file_size = Path(file_path).stat().st_size
        except Exception:
            file_size = 0
        
        # Edge Case: Large file warning (T060)
        MAX_FILE_SIZE_MB = 100
        if file_size > MAX_FILE_SIZE_MB * 1024 * 1024:
            logger.warning(
                f"Large file detected: {document.filename} ({file_size / 1024 / 1024:.1f} MB). "
                f"Processing may take longer and use more memory."
            )
        
        logger.info(
            f"Starting document loading: {document_id} "
            f"(format: {file_format}, size: {file_size / 1024:.1f} KB, "
            f"loader: {loader_type or 'auto'})"
        )
        
        # Update document status
        document.status = "processing"
        db.commit()
        
        # Create processing result
        processing_result = ProcessingResult(
            document_id=document_id,
            processing_type="load",
            provider=loader_type or "auto",
            result_path="",
            status="running"
        )
        db.add(processing_result)
        db.commit()
        db.refresh(processing_result)
        
        start_time = time.time()
        
        try:
            # Load document with fallback strategy
            result_data = fallback_manager.load_with_fallback(
                file_path=file_path,
                file_format=file_format,
                file_size_bytes=file_size,
                preferred_loader=loader_type,
                enable_fallback=enable_fallback
            )
            
            processing_time = time.time() - start_time
            
            if not result_data.get("success"):
                error_msg = result_data.get("error", "Unknown error")
                error_details = result_data.get("error_details", {})
                logger.error(f"Loading failed for {document_id}: {error_msg}")
                raise ProcessingError(f"Loading failed: {error_msg}", error_details)
            
            # Extract statistics
            total_pages = result_data.get("total_pages", 0)
            total_chars = result_data.get("total_chars", 0)
            actual_loader = result_data.get("loader", loader_type or "unknown")
            fallback_used = result_data.get("fallback_used", False)
            
            logger.info(
                f"Successfully loaded {document_id}: "
                f"{total_pages} pages, {total_chars} characters, "
                f"loader: {actual_loader}, fallback: {fallback_used}"
            )
            
            # Add processing time to result
            result_data["processing_time"] = processing_time
            
            # Save result as JSON
            result_path = json_storage.save_result(
                document.filename,
                "load",
                result_data
            )
            
            # Update processing result
            processing_result.result_path = result_path
            processing_result.status = "completed"
            processing_result.provider = actual_loader
            processing_result.extra_metadata = {
                "total_pages": total_pages,
                "total_chars": total_chars,
                "loader_type": actual_loader,
                "file_format": document.format,
                "processing_time": processing_time,
                "fallback_used": fallback_used,
                "fallback_reason": result_data.get("fallback_reason"),
                "original_parser": result_data.get("original_parser"),
                "table_count": len(result_data.get("tables", [])),
                "image_count": len(result_data.get("images", [])),
            }
            
            # Update document status
            document.status = "ready"
            
            db.commit()
            db.refresh(processing_result)
            
            logger.info(f"Document loading completed: {document_id}")
            return processing_result
            
        except ProcessingError:
            processing_result.status = "failed"
            processing_result.error_message = str(ProcessingError)
            document.status = "error"
            db.commit()
            raise
            
        except Exception as e:
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
        
        try:
            return json_storage.load_result(result.result_path)
        except Exception as e:
            logger.error(f"Failed to load result from {result.result_path}: {str(e)}")
            return None
    
    def get_available_loaders(self) -> List[Dict[str, Any]]:
        """
        Get list of available loaders with their configurations.
        
        Returns:
            List of loader configuration dictionaries
        """
        loaders = []
        for name, config in LOADER_REGISTRY.items():
            loader_info = config.to_dict()
            # Check actual availability
            loader_instance = get_loader(name)
            if loader_instance and hasattr(loader_instance, 'is_available'):
                loader_info['is_available'] = loader_instance.is_available()
                if not loader_info['is_available']:
                    loader_info['unavailable_reason'] = loader_instance.get_unavailable_reason()
            loaders.append(loader_info)
        return loaders
    
    def get_supported_formats(self) -> List[str]:
        """
        Get list of supported file formats.
        
        Returns:
            List of supported file extensions
        """
        return get_supported_formats()
    
    def get_format_strategies(self) -> List[Dict[str, Any]]:
        """
        Get list of format strategies.
        
        Returns:
            List of format strategy dictionaries
        """
        return [strategy.to_dict() for strategy in FORMAT_STRATEGIES.values()]
    
    def get_loader_for_format(self, file_format: str) -> Optional[str]:
        """
        Get recommended loader for a specific file format.
        
        Args:
            file_format: File format/extension (e.g., 'pdf', 'docx')
            
        Returns:
            Loader name or None if format not supported
        """
        try:
            strategy = get_format_strategy(file_format)
            return strategy.primary_loader
        except KeyError:
            return None
    
    def get_recommended_loader(
        self,
        file_format: str,
        file_size_bytes: int = 0
    ) -> str:
        """
        Get recommended loader based on format and file size.
        
        Args:
            file_format: File format/extension
            file_size_bytes: File size in bytes
            
        Returns:
            Recommended loader name
        """
        return fallback_manager.get_recommended_loader(file_format, file_size_bytes)


# Global instance
loading_service = LoadingService()
