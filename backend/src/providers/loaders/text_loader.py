"""Plain text document loader."""
from typing import Dict, Any
from pathlib import Path


class TextLoader:
    """Load plain text and markdown documents."""
    
    def __init__(self):
        """Initialize text loader."""
        self.name = "text"
        self.supported_formats = [".txt", ".md", ".markdown"]
    
    def extract_text(self, file_path: str) -> Dict[str, Any]:
        """
        Extract text from plain text or markdown file.
        
        Args:
            file_path: Path to text file
            
        Returns:
            Dictionary with extracted content and metadata
        """
        try:
            path = Path(file_path)
            
            # Try different encodings
            encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1']
            text = None
            used_encoding = None
            
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        text = f.read()
                    used_encoding = encoding
                    break
                except UnicodeDecodeError:
                    continue
            
            if text is None:
                return {
                    "success": False,
                    "loader": self.name,
                    "error": "Unable to decode file with supported encodings"
                }
            
            # Split into lines for page-like structure
            lines = text.split('\n')
            
            # Create a single "page" for the entire document
            pages = [{
                "page_number": 1,
                "text": text,
                "char_count": len(text),
                "line_count": len(lines)
            }]
            
            # Extract basic metadata
            metadata = {
                "filename": path.name,
                "format": path.suffix[1:] if path.suffix else "txt",
                "encoding": used_encoding,
                "line_count": len(lines),
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
text_loader = TextLoader()
