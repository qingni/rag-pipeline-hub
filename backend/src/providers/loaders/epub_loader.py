"""EPUB document loader using ebooklib."""
from typing import Dict, Any, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Check if ebooklib is available
EBOOKLIB_AVAILABLE = False
EBOOKLIB_UNAVAILABLE_REASON = None

try:
    import ebooklib
    from ebooklib import epub
    EBOOKLIB_AVAILABLE = True
except ImportError as e:
    EBOOKLIB_UNAVAILABLE_REASON = f"ebooklib not installed: {str(e)}. Install with: pip install ebooklib"

# Check if BeautifulSoup is available for HTML parsing
BS4_AVAILABLE = False
try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    pass


class EPUBLoader:
    """Load EPUB documents using ebooklib."""
    
    def __init__(self):
        """Initialize EPUB loader."""
        self.name = "epub"
    
    def extract_text(self, file_path: str) -> Dict[str, Any]:
        """
        Extract text from EPUB document.
        
        Args:
            file_path: Path to EPUB file
            
        Returns:
            Dictionary with extracted content
        """
        if not EBOOKLIB_AVAILABLE:
            return {
                "success": False,
                "loader": self.name,
                "error": EBOOKLIB_UNAVAILABLE_REASON
            }
        
        try:
            # Read EPUB
            book = epub.read_epub(file_path)
            
            pages = []
            text_parts = []
            images = []
            image_index = 0
            
            # Get metadata
            title = book.get_metadata('DC', 'title')
            author = book.get_metadata('DC', 'creator')
            
            # Extract content from items
            page_num = 0
            for item in book.get_items():
                if item.get_type() == ebooklib.ITEM_DOCUMENT:
                    page_num += 1
                    content = item.get_content().decode('utf-8', errors='ignore')
                    
                    # Parse HTML content
                    if BS4_AVAILABLE:
                        soup = BeautifulSoup(content, 'html.parser')
                        # Remove script and style
                        for element in soup(['script', 'style']):
                            element.decompose()
                        text = soup.get_text(separator='\n', strip=True)
                    else:
                        # Basic HTML tag removal
                        import re
                        text = re.sub(r'<[^>]+>', '', content)
                        text = text.strip()
                    
                    if text:
                        pages.append({
                            "page_number": page_num,
                            "text": text,
                            "char_count": len(text)
                        })
                        text_parts.append(text)
                
                elif item.get_type() == ebooklib.ITEM_IMAGE:
                    images.append({
                        "page_number": 1,
                        "image_index": image_index,
                        "caption": item.get_name(),
                        "alt_text": None
                    })
                    image_index += 1
            
            full_text = "\n\n".join(text_parts)
            
            return {
                "success": True,
                "loader": self.name,
                "metadata": {
                    "title": title[0][0] if title else None,
                    "author": author[0][0] if author else None,
                    "format": "epub",
                    "chapter_count": len(pages)
                },
                "pages": pages,
                "images": images,
                "full_text": full_text,
                "total_pages": len(pages),
                "total_chars": len(full_text)
            }
            
        except Exception as e:
            logger.error(f"EPUB extraction failed: {str(e)}", exc_info=True)
            return {
                "success": False,
                "loader": self.name,
                "error": str(e)
            }
    
    def is_available(self) -> bool:
        """Check if loader is available."""
        return EBOOKLIB_AVAILABLE
    
    def get_unavailable_reason(self) -> Optional[str]:
        """Get reason why loader is unavailable."""
        return EBOOKLIB_UNAVAILABLE_REASON


# Global instance
epub_loader = EPUBLoader()
