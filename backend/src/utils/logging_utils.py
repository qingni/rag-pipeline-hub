"""
Structured logging utility for embedding service.

Provides JSON-formatted operational metrics logging without text content.
"""
import json
import logging
import time
from datetime import datetime
from typing import Any, Dict, Optional
from contextlib import contextmanager


class EmbeddingLogger:
    """
    Structured logger for embedding operations.
    
    Logs operational metrics in JSON format:
    - Request counts and IDs
    - Processing latencies
    - Model usage
    - Error rates and types
    - Batch sizes and throughput
    - Rate limit encounters
    
    Privacy: Does NOT log text content.
    """
    
    def __init__(self, logger_name: str = "embedding_service"):
        """
        Initialize embedding logger.
        
        Args:
            logger_name: Logger name for identification
        """
        self.logger = logging.getLogger(logger_name)
    
    def _log_json(self, level: int, event: str, data: Dict[str, Any]):
        """
        Log structured JSON data.
        
        Args:
            level: Logging level (logging.INFO, logging.WARNING, etc.)
            event: Event name/type
            data: Additional data fields
        """
        log_entry = {
            "event": event,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            **data
        }
        self.logger.log(level, json.dumps(log_entry))
    
    def log_request_start(
        self,
        request_id: str,
        model: str,
        batch_size: int,
        is_single: bool = False
    ):
        """
        Log embedding request initiation.
        
        Args:
            request_id: Unique request identifier
            model: Embedding model name
            batch_size: Number of texts to process
            is_single: Whether this is a single-text request
        """
        self._log_json(logging.INFO, "embedding_request_start", {
            "request_id": request_id,
            "model": model,
            "batch_size": batch_size,
            "request_type": "single" if is_single else "batch"
        })
    
    def log_request_complete(
        self,
        request_id: str,
        model: str,
        duration_ms: float,
        batch_size: int,
        successful_count: int,
        failed_count: int,
        retry_count: int = 0,
        rate_limit_hits: int = 0
    ):
        """
        Log successful embedding request completion.
        
        Args:
            request_id: Unique request identifier
            model: Embedding model name
            duration_ms: Total processing time in milliseconds
            batch_size: Total texts in request
            successful_count: Successfully vectorized count
            failed_count: Failed vectorization count
            retry_count: Number of retry attempts
            rate_limit_hits: Number of rate limit encounters
        """
        success_rate = successful_count / batch_size if batch_size > 0 else 0
        vectors_per_second = (successful_count / duration_ms * 1000) if duration_ms > 0 else 0
        
        self._log_json(logging.INFO, "embedding_request_complete", {
            "request_id": request_id,
            "model": model,
            "duration_ms": round(duration_ms, 2),
            "batch_size": batch_size,
            "successful_count": successful_count,
            "failed_count": failed_count,
            "success_rate": round(success_rate, 4),
            "vectors_per_second": round(vectors_per_second, 2),
            "retry_count": retry_count,
            "rate_limit_hits": rate_limit_hits,
            "status": "complete"
        })
    
    def log_request_failed(
        self,
        request_id: str,
        model: str,
        duration_ms: float,
        error_type: str,
        error_message: str,
        retry_count: int = 0
    ):
        """
        Log failed embedding request.
        
        Args:
            request_id: Unique request identifier
            model: Embedding model name
            duration_ms: Processing time before failure
            error_type: Error classification
            error_message: Human-readable error
            retry_count: Number of retry attempts made
        """
        self._log_json(logging.ERROR, "embedding_request_failed", {
            "request_id": request_id,
            "model": model,
            "duration_ms": round(duration_ms, 2),
            "error_type": error_type,
            "error_message": error_message,
            "retry_count": retry_count,
            "status": "failed"
        })
    
    def log_partial_success(
        self,
        request_id: str,
        model: str,
        batch_size: int,
        successful_count: int,
        failed_count: int,
        failure_types: Dict[str, int]
    ):
        """
        Log partial batch success.
        
        Args:
            request_id: Unique request identifier
            model: Embedding model name
            batch_size: Total texts in batch
            successful_count: Successfully processed count
            failed_count: Failed processing count
            failure_types: Count of each failure type
        """
        self._log_json(logging.WARNING, "embedding_partial_success", {
            "request_id": request_id,
            "model": model,
            "batch_size": batch_size,
            "successful_count": successful_count,
            "failed_count": failed_count,
            "failure_types": failure_types,
            "status": "partial_success"
        })
    
    def log_retry_attempt(
        self,
        request_id: str,
        attempt: int,
        max_retries: int,
        delay_ms: float,
        error_type: str
    ):
        """
        Log retry attempt.
        
        Args:
            request_id: Unique request identifier
            attempt: Current attempt number
            max_retries: Maximum retry limit
            delay_ms: Backoff delay in milliseconds
            error_type: Error that triggered retry
        """
        self._log_json(logging.WARNING, "embedding_retry", {
            "request_id": request_id,
            "retry_attempt": attempt,
            "max_retries": max_retries,
            "backoff_delay_ms": round(delay_ms, 2),
            "error_type": error_type
        })
    
    def log_rate_limit_hit(
        self,
        request_id: str,
        model: str,
        retry_after_seconds: Optional[int] = None
    ):
        """
        Log rate limit encounter.
        
        Args:
            request_id: Unique request identifier
            model: Embedding model name
            retry_after_seconds: Suggested retry delay from API
        """
        data = {
            "request_id": request_id,
            "model": model,
            "rate_limit_hit": True
        }
        if retry_after_seconds:
            data["retry_after_seconds"] = retry_after_seconds
        
        self._log_json(logging.WARNING, "embedding_rate_limit", data)
    
    def log_dimension_mismatch(
        self,
        request_id: str,
        model: str,
        expected_dimension: int,
        actual_dimension: int
    ):
        """
        Log vector dimension mismatch error.
        
        Args:
            request_id: Unique request identifier
            model: Embedding model name
            expected_dimension: Expected vector dimension
            actual_dimension: Actual received dimension
        """
        self._log_json(logging.ERROR, "embedding_dimension_mismatch", {
            "request_id": request_id,
            "model": model,
            "expected_dimension": expected_dimension,
            "actual_dimension": actual_dimension,
            "error_type": "DIMENSION_MISMATCH_ERROR"
        })
    
    @contextmanager
    def log_operation(
        self,
        request_id: str,
        model: str,
        batch_size: int = 1,
        operation: str = "embedding"
    ):
        """
        Context manager for logging operation lifecycle.
        
        Usage:
            with logger.log_operation(request_id, model, batch_size):
                # Perform embedding operation
                vectors = embed_texts(texts)
        
        Args:
            request_id: Unique request identifier
            model: Embedding model name
            batch_size: Number of texts
            operation: Operation description
        """
        start_time = time.time()
        
        self._log_json(logging.INFO, f"{operation}_start", {
            "request_id": request_id,
            "model": model,
            "batch_size": batch_size
        })
        
        try:
            yield
            
            duration_ms = (time.time() - start_time) * 1000
            self._log_json(logging.INFO, f"{operation}_success", {
                "request_id": request_id,
                "model": model,
                "duration_ms": round(duration_ms, 2)
            })
        
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self._log_json(logging.ERROR, f"{operation}_error", {
                "request_id": request_id,
                "model": model,
                "duration_ms": round(duration_ms, 2),
                "error_type": type(e).__name__,
                "error_message": str(e)
            })
            raise


# Global logger instance
embedding_logger = EmbeddingLogger()
