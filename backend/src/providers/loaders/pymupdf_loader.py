"""PyMuPDF document loader."""
import fitz  # PyMuPDF
from typing import Dict, Any, List
from pathlib import Path


class PyMuPDFLoader:
    """Load documents using PyMuPDF library."""
    
    def __init__(self):
        """Initialize PyMuPDF loader."""
        self.name = "pymupdf"
    
    def extract_text(self, file_path: str) -> Dict[str, Any]:
        """
        Extract text from document using PyMuPDF.
        
        Args:
            file_path: Path to document file
            
        Returns:
            Dictionary with extracted content and metadata
        """
        try:
            doc = fitz.open(file_path)
            
            # Extract metadata
            metadata = {
                "page_count": len(doc),
                "title": doc.metadata.get("title", ""),
                "author": doc.metadata.get("author", ""),
                "subject": doc.metadata.get("subject", ""),
                "creator": doc.metadata.get("creator", ""),
                "producer": doc.metadata.get("producer", ""),
                "format": doc.metadata.get("format", ""),
            }
            
            # Extract text from all pages
            pages = []
            full_text = []
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                
                pages.append({
                    "page_number": page_num + 1,
                    "text": text,
                    "char_count": len(text)
                })
                full_text.append(text)
            
            doc.close()
            
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
    
    def extract_images(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Extract images from document.
        
        Args:
            file_path: Path to document file
            
        Returns:
            List of image information dictionaries
        """
        try:
            doc = fitz.open(file_path)
            images = []
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                image_list = page.get_images()
                
                for img_index, img in enumerate(image_list):
                    xref = img[0]
                    images.append({
                        "page": page_num + 1,
                        "index": img_index,
                        "xref": xref
                    })
            
            doc.close()
            return images
            
        except Exception as e:
            return []
    
    def extract_tables(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Extract tables from document (basic implementation).
        
        Args:
            file_path: Path to document file
            
        Returns:
            List of table information
        """
        # PyMuPDF doesn't have built-in table extraction
        # This is a placeholder for basic table detection
        return []


# Global instance
pymupdf_loader = PyMuPDFLoader()
