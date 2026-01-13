"""CSV document loader using pandas."""
from typing import Dict, Any, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Check if pandas is available
PANDAS_AVAILABLE = False
PANDAS_UNAVAILABLE_REASON = None

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError as e:
    PANDAS_UNAVAILABLE_REASON = f"pandas not installed: {str(e)}. Install with: pip install pandas"


class CSVLoader:
    """Load CSV documents using pandas."""
    
    def __init__(self):
        """Initialize CSV loader."""
        self.name = "csv"
    
    def extract_text(self, file_path: str) -> Dict[str, Any]:
        """
        Extract text from CSV document.
        
        Args:
            file_path: Path to CSV file
            
        Returns:
            Dictionary with extracted content
        """
        if not PANDAS_AVAILABLE:
            return {
                "success": False,
                "loader": self.name,
                "error": PANDAS_UNAVAILABLE_REASON
            }
        
        try:
            # Read CSV file
            df = pd.read_csv(file_path, encoding='utf-8', on_bad_lines='skip')
            
            # Convert to text representation
            full_text = df.to_string(index=False)
            
            # Create table representation
            tables = [{
                "page_number": 1,
                "table_index": 0,
                "headers": list(df.columns),
                "rows": df.values.tolist(),
                "caption": Path(file_path).stem,
                "row_count": len(df),
                "col_count": len(df.columns)
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
                    "format": "csv",
                    "row_count": len(df),
                    "column_count": len(df.columns),
                    "columns": list(df.columns)
                },
                "pages": pages,
                "tables": tables,
                "full_text": full_text,
                "total_pages": 1,
                "total_chars": len(full_text)
            }
            
        except Exception as e:
            logger.error(f"CSV extraction failed: {str(e)}", exc_info=True)
            return {
                "success": False,
                "loader": self.name,
                "error": str(e)
            }
    
    def is_available(self) -> bool:
        """Check if loader is available."""
        return PANDAS_AVAILABLE
    
    def get_unavailable_reason(self) -> Optional[str]:
        """Get reason why loader is unavailable."""
        return PANDAS_UNAVAILABLE_REASON


# Global instance
csv_loader = CSVLoader()
