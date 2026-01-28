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
    
    def _format_row_with_headers(self, headers: list, row: list) -> str:
        """
        将数据行格式化为带列名的文本，便于向量检索时理解语义。
        
        Args:
            headers: 列名列表
            row: 数据行
            
        Returns:
            格式化后的文本，如 "user_id: U001 | game_title: Sekiro | rating: 5"
        """
        parts = []
        for header, value in zip(headers, row):
            # 处理空值
            if pd.isna(value):
                value = ""
            parts.append(f"{header}: {value}")
        return " | ".join(parts)
    
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
            
            # 获取列名
            headers = list(df.columns)
            
            # 将每行数据格式化为带列名的文本，便于分块后保持语义完整性
            lines = []
            for _, row in df.iterrows():
                line = self._format_row_with_headers(headers, row.tolist())
                lines.append(line)
            
            full_text = "\n".join(lines)
            
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
