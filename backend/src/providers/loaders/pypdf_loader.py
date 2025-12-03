"""PyPDF document loader."""
from PyPDF2 import PdfReader
from typing import Dict, Any
from pathlib import Path


class PyPDFLoader:
    """Load documents using PyPDF2 library."""
    
    def __init__(self):
        """Initialize PyPDF loader."""
        self.name = "pypdf"
    
    def extract_text(self, file_path: str) -> Dict[str, Any]:
        """
        Extract text from PDF using PyPDF2.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            Dictionary with extracted content and metadata
        """
        try:
            reader = PdfReader(file_path)
            
            # Extract metadata
            metadata = {}
            if reader.metadata:
                metadata = {
                    "title": reader.metadata.get("/Title", ""),
                    "author": reader.metadata.get("/Author", ""),
                    "subject": reader.metadata.get("/Subject", ""),
                    "creator": reader.metadata.get("/Creator", ""),
                    "producer": reader.metadata.get("/Producer", ""),
                }
            
            # Extract text from all pages
            pages = []
            full_text = []
            
            for page_num, page in enumerate(reader.pages):
                text = page.extract_text()
                
                pages.append({
                    "page_number": page_num + 1,
                    "text": text,
                    "char_count": len(text)
                })
                full_text.append(text)
            
            return {
                "success": True,
                "loader": self.name,
                "metadata": metadata,
                "pages": pages,
                "full_text": "\n\n".join(full_text),
                "total_pages": len(pages),
                "total_chars": sum(p["char_count"] for p in pages)
            }
            
        except Exception as e:
            return {
                "success": False,
                "loader": self.name,
                "error": str(e)
            }


# Global instance
pypdf_loader = PyPDFLoader()
