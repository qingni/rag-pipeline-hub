"""
Result Persistence Utilities

This module provides utilities for persisting operation results to JSON files.
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

logger = logging.getLogger(__name__)


class ResultPersistence:
    """Handler for persisting results to JSON files"""
    
    def __init__(self, results_dir: str = "./results"):
        """
        Initialize result persistence handler
        
        Args:
            results_dir: Directory to store result files
        """
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)
    
    def save_index_build_result(
        self,
        index_name: str,
        vector_count: int,
        duration_seconds: float,
        status: str,
        **kwargs
    ) -> Path:
        """
        Save index build result to JSON
        
        Args:
            index_name: Name of the index
            vector_count: Number of vectors inserted
            duration_seconds: Build duration
            status: Build status
            **kwargs: Additional metadata
            
        Returns:
            Path to saved file
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"index_build_{index_name}_{timestamp}.json"
        
        result = {
            "operation": "index_build",
            "index_name": index_name,
            "vector_count": vector_count,
            "duration_seconds": duration_seconds,
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
            **kwargs
        }
        
        return self._save_json(filename, result)
    
    def save_query_result(
        self,
        index_name: str,
        top_k: int,
        result_count: int,
        latency_ms: float,
        results: list,
        **kwargs
    ) -> Path:
        """
        Save query result to JSON
        
        Args:
            index_name: Name of the index
            top_k: Requested number of results
            result_count: Actual number of results
            latency_ms: Query latency in milliseconds
            results: Query results
            **kwargs: Additional metadata
            
        Returns:
            Path to saved file
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"query_result_{index_name}_{timestamp}.json"
        
        result = {
            "operation": "query",
            "index_name": index_name,
            "top_k": top_k,
            "result_count": result_count,
            "latency_ms": latency_ms,
            "results": self._serialize_results(results),
            "timestamp": datetime.utcnow().isoformat(),
            **kwargs
        }
        
        return self._save_json(filename, result)
    
    def save_batch_search_result(
        self,
        index_name: str,
        query_count: int,
        total_results: int,
        total_latency_ms: float,
        results: list,
        **kwargs
    ) -> Path:
        """
        Save batch search result to JSON
        
        Args:
            index_name: Name of the index
            query_count: Number of queries
            total_results: Total number of results
            total_latency_ms: Total latency
            results: Batch results (list of result lists)
            **kwargs: Additional metadata
            
        Returns:
            Path to saved file
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"batch_search_{index_name}_{timestamp}.json"
        
        result = {
            "operation": "batch_search",
            "index_name": index_name,
            "query_count": query_count,
            "total_results": total_results,
            "total_latency_ms": total_latency_ms,
            "avg_latency_ms": total_latency_ms / query_count if query_count > 0 else 0,
            "results": [self._serialize_results(r) for r in results],
            "timestamp": datetime.utcnow().isoformat(),
            **kwargs
        }
        
        return self._save_json(filename, result)
    
    def save_index_statistics(
        self,
        index_name: str,
        statistics: Dict[str, Any],
        **kwargs
    ) -> Path:
        """
        Save index statistics to JSON
        
        Args:
            index_name: Name of the index
            statistics: Statistics dictionary
            **kwargs: Additional metadata
            
        Returns:
            Path to saved file
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"index_stats_{index_name}_{timestamp}.json"
        
        result = {
            "operation": "statistics",
            "index_name": index_name,
            "statistics": self._serialize_dict(statistics),
            "timestamp": datetime.utcnow().isoformat(),
            **kwargs
        }
        
        return self._save_json(filename, result)
    
    def _save_json(self, filename: str, data: Dict[str, Any]) -> Path:
        """
        Save dictionary to JSON file
        
        Args:
            filename: Output filename
            data: Data to save
            
        Returns:
            Path to saved file
        """
        filepath = self.results_dir / filename
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, cls=CustomJSONEncoder)
            
            logger.info(f"Saved result to {filepath}")
            return filepath
        
        except Exception as e:
            logger.error(f"Failed to save result to {filepath}: {e}")
            raise
    
    def _serialize_results(self, results: list) -> list:
        """Serialize result objects to JSON-compatible format"""
        return [self._serialize_dict(r) for r in results]
    
    def _serialize_dict(self, obj: Any) -> Any:
        """Recursively serialize objects to JSON-compatible types"""
        if isinstance(obj, dict):
            return {k: self._serialize_dict(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [self._serialize_dict(item) for item in obj]
        elif hasattr(obj, 'dict'):  # Pydantic models
            return self._serialize_dict(obj.dict())
        elif hasattr(obj, 'to_dict'):  # Custom models
            return self._serialize_dict(obj.to_dict())
        else:
            return obj
    
    def load_result(self, filepath: Path) -> Dict[str, Any]:
        """
        Load result from JSON file
        
        Args:
            filepath: Path to result file
            
        Returns:
            Loaded data dictionary
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def list_results(
        self,
        operation: Optional[str] = None,
        index_name: Optional[str] = None
    ) -> list[Path]:
        """
        List saved result files
        
        Args:
            operation: Filter by operation type
            index_name: Filter by index name
            
        Returns:
            List of result file paths
        """
        pattern = "*"
        if operation:
            pattern = f"{operation}_*"
        
        files = sorted(self.results_dir.glob(f"{pattern}.json"))
        
        if index_name:
            files = [f for f in files if index_name in f.name]
        
        return files


class CustomJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for special types"""
    
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, UUID):
            return str(obj)
        elif isinstance(obj, Path):
            return str(obj)
        elif hasattr(obj, 'dict'):
            return obj.dict()
        elif hasattr(obj, 'to_dict'):
            return obj.to_dict()
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        return super().default(obj)


# Global instance
_result_persistence: Optional[ResultPersistence] = None


def get_result_persistence(results_dir: str = "./results") -> ResultPersistence:
    """Get the global ResultPersistence instance"""
    global _result_persistence
    if _result_persistence is None:
        _result_persistence = ResultPersistence(results_dir)
    return _result_persistence


def reset_result_persistence():
    """Reset the global instance (useful for testing)"""
    global _result_persistence
    _result_persistence = None
