"""DOC document loader."""
from typing import Dict, Any
from pathlib import Path
import subprocess


class DocLoader:
    """Load DOC documents using antiword or python-docx."""
    
    def __init__(self):
        """Initialize DOC loader."""
        self.name = "doc"
    
    def _extract_with_antiword(self, file_path: str) -> str:
        """
        Extract text using antiword command-line tool.
        
        Args:
            file_path: Path to DOC file
            
        Returns:
            Extracted text
        """
        try:
            result = subprocess.run(
                ['antiword', file_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                return result.stdout
            return None
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return None
    
    def _extract_with_python_docx(self, file_path: str) -> str:
        """
        Try to extract using python-docx (works for some .doc files).
        
        Args:
            file_path: Path to DOC file
            
        Returns:
            Extracted text
        """
        try:
            from docx import Document
            doc = Document(file_path)
            paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
            return "\n\n".join(paragraphs)
        except Exception:
            return None
    
    def extract_text(self, file_path: str) -> Dict[str, Any]:
        """
        Extract text from DOC file using available methods.
        
        Tries multiple extraction methods in order:
        1. antiword (command-line tool)
        2. python-docx (may work for some .doc files)
        
        Args:
            file_path: Path to DOC file
            
        Returns:
            Dictionary with extracted content and metadata
        """
        try:
            path = Path(file_path)
            text = None
            method_used = None
            
            # Try different extraction methods
            extraction_methods = [
                ("antiword", self._extract_with_antiword),
                ("python-docx", self._extract_with_python_docx),
            ]
            
            for method_name, method_func in extraction_methods:
                text = method_func(file_path)
                if text:
                    method_used = method_name
                    break
            
            if not text:
                return {
                    "success": False,
                    "loader": self.name,
                    "error": (
                        "Unable to extract text from DOC file. "
                        "Please install antiword or convert to DOCX format. "
                        "Install antiword: apt-get install antiword (Linux) or brew install antiword (Mac)."
                    )
                }
            
            # Create a single "page" for the entire document
            pages = [{
                "page_number": 1,
                "text": text,
                "char_count": len(text)
            }]
            
            # Extract basic metadata
            metadata = {
                "filename": path.name,
                "format": "doc",
                "extraction_method": method_used,
                "file_size": path.stat().st_size
            }
            
            return {
                "success": True,
                "loader": self.name,
                "metadata": metadata,
                "pages": pages,
                "full_text": text,
                "total_pages": 1,
                "total_chars": len(text)
            }
            
        except Exception as e:
            return {
                "success": False,
                "loader": self.name,
                "error": str(e)
            }


# Global instance
doc_loader = DocLoader()
