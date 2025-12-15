"""
JSON persistence layer for embedding results.

Implements atomic writes with per-request file storage per constitution requirement.
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import UUID

from ..models.embedding_models import (
    SingleEmbeddingResponse,
    BatchEmbeddingResponse,
    Vector,
    EmbeddingFailure
)


class EmbeddingStorage:
    """
    JSON storage for embedding results.
    
    Features:
    - Per-request JSON files
    - Atomic writes (tmp file + rename)
    - Directory structure: results/embedding/YYYY-MM-DD/
    - Naming convention: embedding_{request_id}_{timestamp}.json
    """
    
    def __init__(self, results_dir: str = "results/embedding"):
        """
        Initialize storage handler.
        
        Args:
            results_dir: Base directory for results
        """
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_daily_dir(self, date: Optional[datetime] = None) -> Path:
        """
        Get directory for date-based organization.
        
        Args:
            date: Date for directory (default: today)
            
        Returns:
            Path to daily directory
        """
        if date is None:
            date = datetime.utcnow()
        
        daily_dir = self.results_dir / date.strftime("%Y-%m-%d")
        daily_dir.mkdir(parents=True, exist_ok=True)
        return daily_dir
    
    def _generate_filename(self, request_id: str, timestamp: datetime) -> str:
        """
        Generate filename for embedding result.
        
        Format: embedding_{request_id}_{timestamp}.json
        
        Args:
            request_id: Unique request identifier
            timestamp: Request timestamp
            
        Returns:
            Filename string
        """
        # Format timestamp as YYYYMMDD_HHMMSS
        ts_str = timestamp.strftime("%Y%m%d_%H%M%S")
        return f"embedding_{request_id}_{ts_str}.json"
    
    def _atomic_write(self, filepath: Path, data: dict):
        """
        Perform atomic write using tmp file + rename.
        
        Args:
            filepath: Target file path
            data: Data to write
        """
        tmp_filepath = filepath.with_suffix('.tmp')
        
        try:
            # Write to temporary file
            with open(tmp_filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
            
            # Atomic rename
            tmp_filepath.rename(filepath)
        
        except Exception as e:
            # Clean up tmp file on failure
            if tmp_filepath.exists():
                tmp_filepath.unlink()
            raise IOError(f"Failed to write embedding result: {e}") from e
    
    def save_single_result(
        self,
        response: SingleEmbeddingResponse
    ) -> Path:
        """
        Save single text embedding result.
        
        Args:
            response: Single embedding response
            
        Returns:
            Path to saved file
        """
        daily_dir = self._get_daily_dir(response.timestamp)
        filename = self._generate_filename(response.request_id, response.timestamp)
        filepath = daily_dir / filename
        
        # Convert response to dict
        data = {
            "request_id": response.request_id,
            "status": response.status,
            "timestamp": response.timestamp.isoformat() + "Z",
            "metadata": {
                "model": response.metadata.model,
                "model_dimension": response.metadata.model_dimension,
                "processing_time_ms": response.metadata.processing_time_ms,
                "api_latency_ms": response.metadata.api_latency_ms,
                "retry_count": response.metadata.retry_count,
                "rate_limit_hits": response.metadata.rate_limit_hits,
                "config": {
                    "api_endpoint": response.metadata.config.api_endpoint,
                    "max_retries": response.metadata.config.max_retries,
                    "timeout_seconds": response.metadata.config.timeout_seconds,
                    "exponential_backoff": response.metadata.config.exponential_backoff,
                    "initial_delay_seconds": response.metadata.config.initial_delay_seconds,
                    "max_delay_seconds": response.metadata.config.max_delay_seconds
                }
            }
        }
        
        if response.vector:
            data["vector"] = {
                "index": response.vector.index,
                "vector": response.vector.vector,
                "dimension": response.vector.dimension,
                "text_hash": response.vector.text_hash,
                "text_length": response.vector.text_length,
                "processing_time_ms": response.vector.processing_time_ms
            }
        
        if response.error:
            data["error"] = {
                "index": response.error.index,
                "text_preview": response.error.text_preview,
                "error_type": response.error.error_type,
                "error_message": response.error.error_message,
                "retry_recommended": response.error.retry_recommended,
                "retry_count": response.error.retry_count
            }
        
        self._atomic_write(filepath, data)
        return filepath
    
    def save_batch_result(
        self,
        response: BatchEmbeddingResponse
    ) -> Path:
        """
        Save batch embedding result.
        
        Args:
            response: Batch embedding response
            
        Returns:
            Path to saved file
        """
        daily_dir = self._get_daily_dir(response.timestamp)
        filename = self._generate_filename(response.request_id, response.timestamp)
        filepath = daily_dir / filename
        
        # Convert response to dict
        data = {
            "request_id": response.request_id,
            "status": response.status,
            "timestamp": response.timestamp.isoformat() + "Z",
            "metadata": {
                "model": response.metadata.model,
                "model_dimension": response.metadata.model_dimension,
                "batch_size": response.metadata.batch_size,
                "successful_count": response.metadata.successful_count,
                "failed_count": response.metadata.failed_count,
                "processing_time_ms": response.metadata.processing_time_ms,
                "api_latency_ms": response.metadata.api_latency_ms,
                "retry_count": response.metadata.retry_count,
                "rate_limit_hits": response.metadata.rate_limit_hits,
                "vectors_per_second": response.metadata.vectors_per_second,
                "config": {
                    "api_endpoint": response.metadata.config.api_endpoint,
                    "max_retries": response.metadata.config.max_retries,
                    "timeout_seconds": response.metadata.config.timeout_seconds,
                    "exponential_backoff": response.metadata.config.exponential_backoff,
                    "initial_delay_seconds": response.metadata.config.initial_delay_seconds,
                    "max_delay_seconds": response.metadata.config.max_delay_seconds
                }
            },
            "vectors": [
                {
                    "index": v.index,
                    "vector": v.vector,
                    "dimension": v.dimension,
                    "text_hash": v.text_hash,
                    "text_length": v.text_length,
                    "processing_time_ms": v.processing_time_ms
                }
                for v in response.vectors
            ],
            "failures": [
                {
                    "index": f.index,
                    "text_preview": f.text_preview,
                    "error_type": f.error_type,
                    "error_message": f.error_message,
                    "retry_recommended": f.retry_recommended,
                    "retry_count": f.retry_count
                }
                for f in response.failures
            ]
        }
        
        self._atomic_write(filepath, data)
        return filepath
    
    def load_result(self, request_id: str, date: Optional[datetime] = None) -> Optional[dict]:
        """
        Load embedding result by request ID.
        
        Args:
            request_id: Unique request identifier
            date: Date to search (default: today)
            
        Returns:
            Result data or None if not found
        """
        daily_dir = self._get_daily_dir(date)
        
        # Search for file matching request_id pattern
        pattern = f"embedding_{request_id}_*.json"
        matches = list(daily_dir.glob(pattern))
        
        if not matches:
            return None
        
        # Return first match (should only be one)
        with open(matches[0], 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def list_results(
        self,
        date: Optional[datetime] = None,
        limit: int = 100
    ) -> list:
        """
        List recent embedding results.
        
        Args:
            date: Date to search (default: today)
            limit: Maximum results to return
            
        Returns:
            List of result summaries
        """
        daily_dir = self._get_daily_dir(date)
        
        results = []
        for filepath in sorted(daily_dir.glob("embedding_*.json"), reverse=True)[:limit]:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                results.append({
                    "request_id": data["request_id"],
                    "status": data["status"],
                    "timestamp": data["timestamp"],
                    "model": data["metadata"]["model"],
                    "batch_size": data["metadata"].get("batch_size", 1),
                    "filename": filepath.name
                })
        
        return results
