"""Properties file loader using jproperties."""
from typing import Dict, Any, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Check if jproperties is available
JPROPERTIES_AVAILABLE = False
JPROPERTIES_UNAVAILABLE_REASON = None

try:
    from jproperties import Properties
    JPROPERTIES_AVAILABLE = True
except ImportError as e:
    JPROPERTIES_UNAVAILABLE_REASON = f"jproperties not installed: {str(e)}. Install with: pip install jproperties"


class PropertiesLoader:
    """Load Java properties files using jproperties."""
    
    def __init__(self):
        """Initialize Properties loader."""
        self.name = "properties"
    
    def extract_text(self, file_path: str) -> Dict[str, Any]:
        """
        Extract text from properties file.
        
        Args:
            file_path: Path to properties file
            
        Returns:
            Dictionary with extracted content
        """
        if not JPROPERTIES_AVAILABLE:
            return self._extract_fallback(file_path)
        
        try:
            # Read properties file
            props = Properties()
            with open(file_path, 'rb') as f:
                props.load(f)
            
            # Convert to text
            text_parts = []
            properties_dict = {}
            
            for key, value in props.items():
                text_parts.append(f"{key} = {value.data}")
                properties_dict[key] = value.data
            
            full_text = '\n'.join(text_parts)
            
            # Create table representation
            tables = [{
                "page_number": 1,
                "table_index": 0,
                "headers": ["Key", "Value"],
                "rows": [[k, v] for k, v in properties_dict.items()],
                "caption": "Properties",
                "row_count": len(properties_dict),
                "col_count": 2
            }]
            
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
                    "format": "properties",
                    "property_count": len(properties_dict)
                },
                "pages": pages,
                "tables": tables,
                "full_text": full_text,
                "total_pages": 1,
                "total_chars": len(full_text)
            }
            
        except Exception as e:
            logger.error(f"Properties extraction failed: {str(e)}", exc_info=True)
            return self._extract_fallback(file_path)
    
    def _extract_fallback(self, file_path: str) -> Dict[str, Any]:
        """Fallback extraction without jproperties."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Simple parsing
            lines = content.split('\n')
            text_parts = []
            properties_dict = {}
            
            for line in lines:
                line = line.strip()
                # Skip comments and empty lines
                if not line or line.startswith('#') or line.startswith('!'):
                    continue
                
                # Parse key=value or key:value
                if '=' in line:
                    key, value = line.split('=', 1)
                elif ':' in line:
                    key, value = line.split(':', 1)
                else:
                    continue
                
                key = key.strip()
                value = value.strip()
                text_parts.append(f"{key} = {value}")
                properties_dict[key] = value
            
            full_text = '\n'.join(text_parts)
            
            tables = [{
                "page_number": 1,
                "table_index": 0,
                "headers": ["Key", "Value"],
                "rows": [[k, v] for k, v in properties_dict.items()],
                "caption": "Properties",
                "row_count": len(properties_dict),
                "col_count": 2
            }]
            
            pages = [{
                "page_number": 1,
                "text": full_text,
                "char_count": len(full_text)
            }]
            
            return {
                "success": True,
                "loader": self.name,
                "metadata": {
                    "format": "properties",
                    "property_count": len(properties_dict),
                    "parsed_with": "fallback"
                },
                "pages": pages,
                "tables": tables,
                "full_text": full_text,
                "total_pages": 1,
                "total_chars": len(full_text)
            }
            
        except Exception as e:
            logger.error(f"Properties fallback extraction failed: {str(e)}", exc_info=True)
            return {
                "success": False,
                "loader": self.name,
                "error": str(e)
            }
    
    def is_available(self) -> bool:
        """Check if loader is available."""
        return True  # Fallback always available
    
    def get_unavailable_reason(self) -> Optional[str]:
        """Get reason why loader is unavailable."""
        return None


# Global instance
properties_loader = PropertiesLoader()
