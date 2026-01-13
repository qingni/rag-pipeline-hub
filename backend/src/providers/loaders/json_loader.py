"""JSON document loader."""
from typing import Dict, Any, Optional
from pathlib import Path
import json
import logging

logger = logging.getLogger(__name__)


class JSONLoader:
    """Load JSON documents."""
    
    def __init__(self):
        """Initialize JSON loader."""
        self.name = "json"
    
    def extract_text(self, file_path: str) -> Dict[str, Any]:
        """
        Extract text from JSON document.
        
        Args:
            file_path: Path to JSON file
            
        Returns:
            Dictionary with extracted content
        """
        try:
            # Read JSON file
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Convert to formatted text
            full_text = json.dumps(data, indent=2, ensure_ascii=False)
            
            # Extract text content if it's a structured document
            extracted_text = self._extract_text_content(data)
            if extracted_text:
                full_text = extracted_text + "\n\n---\n\n" + full_text
            
            # Create page
            pages = [{
                "page_number": 1,
                "text": full_text,
                "char_count": len(full_text)
            }]
            
            # Extract tables if data is a list of objects
            tables = self._extract_tables(data)
            
            return {
                "success": True,
                "loader": self.name,
                "metadata": {
                    "format": "json",
                    "structure_type": self._get_structure_type(data)
                },
                "pages": pages,
                "tables": tables,
                "full_text": full_text,
                "total_pages": 1,
                "total_chars": len(full_text)
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed: {str(e)}")
            return {
                "success": False,
                "loader": self.name,
                "error": f"Invalid JSON: {str(e)}"
            }
        except Exception as e:
            logger.error(f"JSON extraction failed: {str(e)}", exc_info=True)
            return {
                "success": False,
                "loader": self.name,
                "error": str(e)
            }
    
    def _extract_text_content(self, data: Any, prefix: str = "") -> str:
        """Recursively extract text content from JSON structure."""
        text_parts = []
        
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, str):
                    text_parts.append(f"{key}: {value}")
                elif isinstance(value, (dict, list)):
                    nested = self._extract_text_content(value, f"{prefix}{key}.")
                    if nested:
                        text_parts.append(nested)
        elif isinstance(data, list):
            for i, item in enumerate(data):
                if isinstance(item, str):
                    text_parts.append(item)
                elif isinstance(item, (dict, list)):
                    nested = self._extract_text_content(item, f"{prefix}[{i}].")
                    if nested:
                        text_parts.append(nested)
        
        return "\n".join(text_parts)
    
    def _extract_tables(self, data: Any) -> list:
        """Extract table-like structures from JSON."""
        tables = []
        
        # If data is a list of objects with same keys, treat as table
        if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
            headers = list(data[0].keys())
            rows = []
            
            for item in data:
                if isinstance(item, dict):
                    row = [str(item.get(h, "")) for h in headers]
                    rows.append(row)
            
            if rows:
                tables.append({
                    "page_number": 1,
                    "table_index": 0,
                    "headers": headers,
                    "rows": rows,
                    "caption": None,
                    "row_count": len(rows),
                    "col_count": len(headers)
                })
        
        return tables
    
    def _get_structure_type(self, data: Any) -> str:
        """Determine the structure type of JSON data."""
        if isinstance(data, dict):
            return "object"
        elif isinstance(data, list):
            if len(data) > 0 and isinstance(data[0], dict):
                return "array_of_objects"
            return "array"
        return "primitive"
    
    def is_available(self) -> bool:
        """Check if loader is available."""
        return True
    
    def get_unavailable_reason(self) -> Optional[str]:
        """Get reason why loader is unavailable."""
        return None


# Global instance
json_loader = JSONLoader()
