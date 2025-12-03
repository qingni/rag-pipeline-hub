"""DOCX document loader."""
from typing import Dict, Any, List
from pathlib import Path


class DocxLoader:
    """Load DOCX documents using python-docx."""
    
    def __init__(self):
        """Initialize DOCX loader."""
        self.name = "docx"
    
    def extract_text(self, file_path: str) -> Dict[str, Any]:
        """
        Extract text from DOCX file.
        
        Args:
            file_path: Path to DOCX file
            
        Returns:
            Dictionary with extracted content and metadata
        """
        try:
            # Import here to avoid dependency issues
            from docx import Document
            
            doc = Document(file_path)
            
            # Extract core properties metadata
            metadata = {}
            if hasattr(doc, 'core_properties'):
                cp = doc.core_properties
                metadata = {
                    "title": cp.title or "",
                    "author": cp.author or "",
                    "subject": cp.subject or "",
                    "created": str(cp.created) if cp.created else "",
                    "modified": str(cp.modified) if cp.modified else "",
                    "last_modified_by": cp.last_modified_by or "",
                    "paragraph_count": len(doc.paragraphs)
                }
            
            # Extract text from all paragraphs
            full_text = []
            paragraph_texts = []
            
            for para in doc.paragraphs:
                text = para.text
                if text.strip():  # Only add non-empty paragraphs
                    paragraph_texts.append(text)
                    full_text.append(text)
            
            # Extract text from tables
            table_texts = []
            for table in doc.tables:
                for row in table.rows:
                    row_text = []
                    for cell in row.cells:
                        if cell.text.strip():
                            row_text.append(cell.text.strip())
                    if row_text:
                        table_texts.append(" | ".join(row_text))
            
            if table_texts:
                full_text.extend(table_texts)
            
            full_text_str = "\n\n".join(full_text)
            
            # Create a single "page" for the entire document
            pages = [{
                "page_number": 1,
                "text": full_text_str,
                "char_count": len(full_text_str),
                "paragraph_count": len(paragraph_texts),
                "table_count": len(doc.tables)
            }]
            
            metadata.update({
                "table_count": len(doc.tables),
                "paragraph_count": len(paragraph_texts)
            })
            
            return {
                "success": True,
                "loader": self.name,
                "metadata": metadata,
                "pages": pages,
                "full_text": full_text_str,
                "total_pages": 1,
                "total_chars": len(full_text_str)
            }
            
        except ImportError:
            return {
                "success": False,
                "loader": self.name,
                "error": "python-docx library not installed. Install with: pip install python-docx"
            }
        except Exception as e:
            return {
                "success": False,
                "loader": self.name,
                "error": str(e)
            }


# Global instance
docx_loader = DocxLoader()
