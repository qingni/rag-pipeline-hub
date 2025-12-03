"""Document parsing service."""
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from ..models.document import Document
from ..models.processing_result import ProcessingResult
from ..storage.json_storage import json_storage
from ..utils.error_handlers import NotFoundError, ProcessingError


class ParsingService:
    """Service for parsing documents with different options."""
    
    def parse_document(
        self,
        db: Session,
        document_id: str,
        parse_option: str = "full_text",
        include_tables: bool = True
    ) -> ProcessingResult:
        """
        Parse document with specified options.
        
        Args:
            db: Database session
            document_id: Document identifier
            parse_option: Parse option (full_text, by_page, by_heading, mixed)
            include_tables: Whether to include tables
            
        Returns:
            ProcessingResult instance
            
        Raises:
            NotFoundError: If document not found
            ProcessingError: If parsing fails
        """
        # Get document
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise NotFoundError("Document", document_id)
        
        # Get load result (need loaded document data)
        load_result = db.query(ProcessingResult).filter(
            ProcessingResult.document_id == document_id,
            ProcessingResult.processing_type == "load",
            ProcessingResult.status == "completed"
        ).order_by(ProcessingResult.created_at.desc()).first()
        
        if not load_result:
            raise ProcessingError("Document must be loaded before parsing")
        
        # Create processing result
        processing_result = ProcessingResult(
            document_id=document_id,
            processing_type="parse",
            provider=parse_option,
            result_path="",
            status="running"
        )
        db.add(processing_result)
        db.commit()
        db.refresh(processing_result)
        
        try:
            # Load the loaded document data
            load_data = json_storage.load_result(load_result.result_path)
            if not load_data:
                raise ProcessingError("Failed to load document data")
            
            # Parse based on option
            if parse_option == "full_text":
                parsed_data = self._parse_full_text(load_data, include_tables)
            elif parse_option == "by_page":
                parsed_data = self._parse_by_page(load_data, include_tables)
            elif parse_option == "by_heading":
                parsed_data = self._parse_by_heading(load_data, include_tables)
            elif parse_option == "mixed":
                parsed_data = self._parse_mixed(load_data, include_tables)
            else:
                raise ProcessingError(f"Unknown parse option: {parse_option}")
            
            # Save result as JSON
            result_path = json_storage.save_result(
                document.filename,
                "parse",
                parsed_data
            )
            
            # Update processing result
            processing_result.result_path = result_path
            processing_result.status = "completed"
            processing_result.extra_metadata = {
                "parse_option": parse_option,
                "include_tables": include_tables,
                "content_length": len(parsed_data.get("content", ""))
            }
            
            db.commit()
            db.refresh(processing_result)
            
            return processing_result
            
        except Exception as e:
            processing_result.status = "failed"
            processing_result.error_message = str(e)
            db.commit()
            raise ProcessingError(f"Parsing failed: {str(e)}")
    
    def _parse_full_text(self, load_data: Dict[str, Any], include_tables: bool) -> Dict[str, Any]:
        """Parse document as full text."""
        return {
            "parse_option": "full_text",
            "content": load_data.get("full_text", ""),
            "metadata": load_data.get("metadata", {}),
            "total_pages": load_data.get("total_pages", 0),
            "include_tables": include_tables
        }
    
    def _parse_by_page(self, load_data: Dict[str, Any], include_tables: bool) -> Dict[str, Any]:
        """Parse document by page."""
        pages = load_data.get("pages", [])
        return {
            "parse_option": "by_page",
            "pages": pages,
            "metadata": load_data.get("metadata", {}),
            "total_pages": len(pages),
            "include_tables": include_tables
        }
    
    def _parse_by_heading(self, load_data: Dict[str, Any], include_tables: bool) -> Dict[str, Any]:
        """Parse document by heading (basic implementation)."""
        # This is a simplified implementation
        # In production, you'd use NLP or regex to detect headings
        full_text = load_data.get("full_text", "")
        sections = full_text.split("\n\n")  # Simple split by double newline
        
        return {
            "parse_option": "by_heading",
            "sections": [{"index": i, "content": s} for i, s in enumerate(sections)],
            "metadata": load_data.get("metadata", {}),
            "total_sections": len(sections),
            "include_tables": include_tables
        }
    
    def _parse_mixed(self, load_data: Dict[str, Any], include_tables: bool) -> Dict[str, Any]:
        """Parse document with mixed strategy."""
        return {
            "parse_option": "mixed",
            "full_text": load_data.get("full_text", ""),
            "pages": load_data.get("pages", []),
            "metadata": load_data.get("metadata", {}),
            "total_pages": load_data.get("total_pages", 0),
            "include_tables": include_tables
        }


# Global instance
parsing_service = ParsingService()
