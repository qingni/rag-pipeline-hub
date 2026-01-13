"""XML document loader using lxml."""
from typing import Dict, Any, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Check if lxml is available
LXML_AVAILABLE = False
LXML_UNAVAILABLE_REASON = None

try:
    from lxml import etree
    LXML_AVAILABLE = True
except ImportError as e:
    LXML_UNAVAILABLE_REASON = f"lxml not installed: {str(e)}. Install with: pip install lxml"
    # Fallback to standard library
    try:
        import xml.etree.ElementTree as etree
        LXML_AVAILABLE = True
        LXML_UNAVAILABLE_REASON = None
    except ImportError:
        pass


class XMLLoader:
    """Load XML documents using lxml or xml.etree."""
    
    def __init__(self):
        """Initialize XML loader."""
        self.name = "xml"
    
    def extract_text(self, file_path: str) -> Dict[str, Any]:
        """
        Extract text from XML document.
        
        Args:
            file_path: Path to XML file
            
        Returns:
            Dictionary with extracted content
        """
        if not LXML_AVAILABLE:
            return {
                "success": False,
                "loader": self.name,
                "error": LXML_UNAVAILABLE_REASON
            }
        
        try:
            # Parse XML
            tree = etree.parse(file_path)
            root = tree.getroot()
            
            # Extract all text content
            text_parts = []
            self._extract_text_recursive(root, text_parts)
            full_text = "\n".join(text_parts)
            
            # Get structure info
            structure = self._get_structure_info(root)
            
            # Create page
            pages = [{
                "page_number": 1,
                "text": full_text,
                "char_count": len(full_text)
            }]
            
            return {
                "success": True,
                "loader": self.name,
                "metadata": {
                    "format": "xml",
                    "root_tag": root.tag if hasattr(root, 'tag') else str(root),
                    "structure": structure
                },
                "pages": pages,
                "full_text": full_text,
                "total_pages": 1,
                "total_chars": len(full_text)
            }
            
        except Exception as e:
            logger.error(f"XML extraction failed: {str(e)}", exc_info=True)
            return {
                "success": False,
                "loader": self.name,
                "error": str(e)
            }
    
    def _extract_text_recursive(self, element, text_parts: list, depth: int = 0) -> None:
        """Recursively extract text from XML elements."""
        # Get element text
        if element.text and element.text.strip():
            text_parts.append(element.text.strip())
        
        # Process children
        for child in element:
            self._extract_text_recursive(child, text_parts, depth + 1)
            
            # Get tail text
            if child.tail and child.tail.strip():
                text_parts.append(child.tail.strip())
    
    def _get_structure_info(self, root) -> Dict[str, Any]:
        """Get XML structure information."""
        def count_elements(element):
            count = 1
            for child in element:
                count += count_elements(child)
            return count
        
        return {
            "element_count": count_elements(root),
            "child_tags": list(set(child.tag for child in root))[:10]  # First 10 unique tags
        }
    
    def is_available(self) -> bool:
        """Check if loader is available."""
        return LXML_AVAILABLE
    
    def get_unavailable_reason(self) -> Optional[str]:
        """Get reason why loader is unavailable."""
        return LXML_UNAVAILABLE_REASON


# Global instance
xml_loader = XMLLoader()
