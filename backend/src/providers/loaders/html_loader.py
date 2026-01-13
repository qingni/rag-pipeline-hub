"""HTML document loader using BeautifulSoup."""
from typing import Dict, Any, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Check if BeautifulSoup is available
BS4_AVAILABLE = False
BS4_UNAVAILABLE_REASON = None

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError as e:
    BS4_UNAVAILABLE_REASON = f"BeautifulSoup not installed: {str(e)}. Install with: pip install beautifulsoup4 lxml"


class HTMLLoader:
    """Load HTML documents using BeautifulSoup."""
    
    def __init__(self):
        """Initialize HTML loader."""
        self.name = "html"
    
    def extract_text(self, file_path: str) -> Dict[str, Any]:
        """
        Extract text from HTML document.
        
        Args:
            file_path: Path to HTML file
            
        Returns:
            Dictionary with extracted content
        """
        if not BS4_AVAILABLE:
            return {
                "success": False,
                "loader": self.name,
                "error": BS4_UNAVAILABLE_REASON
            }
        
        try:
            # Read file
            path = Path(file_path)
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                html_content = f.read()
            
            # Parse HTML
            soup = BeautifulSoup(html_content, 'lxml' if self._has_lxml() else 'html.parser')
            
            # Remove script and style elements
            for element in soup(['script', 'style', 'meta', 'link', 'noscript']):
                element.decompose()
            
            # Extract title
            title = soup.title.string if soup.title else None
            
            # Extract text
            full_text = soup.get_text(separator='\n', strip=True)
            
            # Extract headings
            headings = []
            for level in range(1, 7):
                for heading in soup.find_all(f'h{level}'):
                    headings.append({
                        'level': level,
                        'text': heading.get_text(strip=True)
                    })
            
            # Extract tables
            tables = self._extract_tables(soup)
            
            # Extract images
            images = self._extract_images(soup)
            
            # Create single page (HTML is typically single page)
            pages = [{
                "page_number": 1,
                "text": full_text,
                "char_count": len(full_text),
                "headings": headings
            }]
            
            return {
                "success": True,
                "loader": self.name,
                "metadata": {
                    "title": title,
                    "format": "html"
                },
                "pages": pages,
                "tables": tables,
                "images": images,
                "full_text": full_text,
                "total_pages": 1,
                "total_chars": len(full_text)
            }
            
        except Exception as e:
            logger.error(f"HTML extraction failed: {str(e)}", exc_info=True)
            return {
                "success": False,
                "loader": self.name,
                "error": str(e)
            }
    
    def _extract_tables(self, soup) -> list:
        """Extract tables from HTML."""
        tables = []
        
        for idx, table in enumerate(soup.find_all('table')):
            headers = []
            rows = []
            
            # Extract headers
            header_row = table.find('thead')
            if header_row:
                for th in header_row.find_all(['th', 'td']):
                    headers.append(th.get_text(strip=True))
            
            # Extract rows
            tbody = table.find('tbody') or table
            for tr in tbody.find_all('tr'):
                cells = tr.find_all(['td', 'th'])
                if cells:
                    row = [cell.get_text(strip=True) for cell in cells]
                    # If no headers yet, use first row as headers
                    if not headers and len(rows) == 0:
                        headers = row
                    else:
                        rows.append(row)
            
            if headers or rows:
                tables.append({
                    "page_number": 1,
                    "table_index": idx,
                    "headers": headers,
                    "rows": rows,
                    "caption": table.find('caption').get_text(strip=True) if table.find('caption') else None,
                    "row_count": len(rows),
                    "col_count": len(headers)
                })
        
        return tables
    
    def _extract_images(self, soup) -> list:
        """Extract image information from HTML."""
        images = []
        
        for idx, img in enumerate(soup.find_all('img')):
            images.append({
                "page_number": 1,
                "image_index": idx,
                "alt_text": img.get('alt'),
                "caption": None
            })
        
        return images
    
    def _has_lxml(self) -> bool:
        """Check if lxml is available."""
        try:
            import lxml
            return True
        except ImportError:
            return False
    
    def is_available(self) -> bool:
        """Check if loader is available."""
        return BS4_AVAILABLE
    
    def get_unavailable_reason(self) -> Optional[str]:
        """Get reason why loader is unavailable."""
        return BS4_UNAVAILABLE_REASON


# Global instance
html_loader = HTMLLoader()
