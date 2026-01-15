"""Unstructured document loader."""
from typing import Dict, Any
from pathlib import Path


class UnstructuredLoader:
    """Load documents using Unstructured library."""
    
    def __init__(self):
        """Initialize Unstructured loader."""
        self.name = "unstructured"
        self._unavailable_reason = None
    
    def is_available(self) -> bool:
        """
        Check if Unstructured library is available.
        
        Returns:
            True if unstructured is installed and usable
        """
        try:
            from unstructured.partition.auto import partition
            self._unavailable_reason = None
            return True
        except ImportError as e:
            self._unavailable_reason = f"Unstructured library not installed: {str(e)}"
            return False
    
    def get_unavailable_reason(self) -> str:
        """Get reason why loader is unavailable."""
        return self._unavailable_reason or "Unknown reason"
    
    def extract_text(self, file_path: str) -> Dict[str, Any]:
        """
        Extract text from document using Unstructured.
        
        Args:
            file_path: Path to document file
            
        Returns:
            Dictionary with extracted content and metadata
        """
        try:
            # Import here to avoid dependency issues
            from unstructured.partition.auto import partition
            
            # Partition document
            elements = partition(filename=file_path)
            
            # Extract text and metadata
            pages_text = {}
            full_text = []
            
            for element in elements:
                text = element.text
                # Try to get page number if available
                page_num = getattr(element.metadata, 'page_number', 1) if hasattr(element, 'metadata') else 1
                
                if page_num not in pages_text:
                    pages_text[page_num] = []
                
                pages_text[page_num].append(text)
                full_text.append(text)
            
            # Format pages
            pages = []
            for page_num in sorted(pages_text.keys()):
                text = "\n".join(pages_text[page_num])
                pages.append({
                    "page_number": page_num,
                    "text": text,
                    "char_count": len(text)
                })
            
            return {
                "success": True,
                "loader": self.name,
                "metadata": {
                    "elements_count": len(elements)
                },
                "pages": pages,
                "full_text": "\n\n".join(full_text),
                "total_pages": len(pages),
                "total_chars": sum(p["char_count"] for p in pages)
            }
            
        except ImportError as e:
            return {
                "success": False,
                "loader": self.name,
                "error": f"Unstructured dependency missing: {str(e)}"
            }
        except Exception as e:
            return {
                "success": False,
                "loader": self.name,
                "error": str(e)
            }


# Global instance
unstructured_loader = UnstructuredLoader()
