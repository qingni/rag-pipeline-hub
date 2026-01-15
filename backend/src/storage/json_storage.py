"""JSON result storage management."""
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional
from ..config import settings


class JSONStorageManager:
    """Manage JSON result file storage."""
    
    def __init__(self):
        """Initialize JSON storage manager."""
        self.results_dir = Path(settings.RESULTS_DIR)
        self.results_dir.mkdir(parents=True, exist_ok=True)
    
    def save_result(
        self, 
        document_filename: str, 
        processing_type: str, 
        data: Dict[str, Any]
    ) -> str:
        """
        Save processing result as JSON file.
        
        Args:
            document_filename: Original document filename
            processing_type: Type of processing (load, parse, chunk, etc.)
            data: Result data to save
            
        Returns:
            Path to saved JSON file
        """
        # Generate filename: {document_name}_{timestamp}_{type}.json
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        base_name = Path(document_filename).stem
        json_filename = f"{base_name}_{timestamp}_{processing_type}.json"
        
        # Save to subdirectory by processing type
        type_dir = self.results_dir / processing_type
        type_dir.mkdir(exist_ok=True)
        
        result_path = type_dir / json_filename
        
        # Write JSON file
        with open(result_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return str(result_path)
    
    def load_result(self, result_path: str) -> Optional[Dict[str, Any]]:
        """
        Load result from JSON file.
        
        Args:
            result_path: Path to JSON file
            
        Returns:
            Loaded data or None if error
        """
        try:
            path = Path(result_path)
            
            # If absolute path, use directly
            if path.is_absolute():
                pass
            # If path starts with results/, try both from project root and RESULTS_DIR
            elif result_path.startswith("results/") or result_path.startswith("results\\"):
                # First try from project root (backend directory)
                path = Path(result_path)
                if not path.exists():
                    # If not found, try removing 'results/' prefix and prepend RESULTS_DIR
                    rel_path = result_path.replace("results/", "").replace("results\\", "")
                    path = Path(settings.RESULTS_DIR) / rel_path
            else:
                # Prepend RESULTS_DIR for relative paths
                path = Path(settings.RESULTS_DIR) / path
            
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading result: {e}")
            return None
    
    def list_results(
        self, 
        document_id: Optional[str] = None,
        processing_type: Optional[str] = None
    ) -> List[str]:
        """
        List result files.
        
        Args:
            document_id: Filter by document ID (optional)
            processing_type: Filter by processing type (optional)
            
        Returns:
            List of result file paths
        """
        results = []
        
        if processing_type:
            search_dir = self.results_dir / processing_type
            if search_dir.exists():
                results.extend(str(p) for p in search_dir.glob("*.json"))
        else:
            results.extend(str(p) for p in self.results_dir.rglob("*.json"))
        
        return results
    
    def delete_result(self, result_path: str) -> bool:
        """
        Delete result file.
        
        Args:
            result_path: Path to result file
            
        Returns:
            True if deleted successfully
        """
        try:
            path = Path(result_path)
            
            # If absolute path, use directly
            if path.is_absolute():
                pass
            # If path starts with results/, try both from project root and RESULTS_DIR
            elif result_path.startswith("results/") or result_path.startswith("results\\"):
                # First try from project root (backend directory)
                path = Path(result_path)
                if not path.exists():
                    # If not found, try removing 'results/' prefix and prepend RESULTS_DIR
                    rel_path = result_path.replace("results/", "").replace("results\\", "")
                    path = Path(settings.RESULTS_DIR) / rel_path
            else:
                path = Path(settings.RESULTS_DIR) / path
            
            if path.exists():
                path.unlink()
                return True
            return False
        except Exception as e:
            print(f"Error deleting result: {e}")
            return False


# Global instance
json_storage = JSONStorageManager()
