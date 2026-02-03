"""
Batch embedding service with parallel processing.

Provides:
- Batch document embedding with concurrency control
- Progress tracking via SSE
- Rate limiting and error handling
"""
import asyncio
import time
from typing import List, Dict, Any, Optional, AsyncGenerator, Callable
from dataclasses import dataclass, field
from enum import Enum

from ..models.embedding_task import (
    EmbeddingTask,
    EmbeddingTaskStatus,
    EmbeddingConfig,
    EmbeddingProgress,
)
from ..utils.rate_limiter import AdaptiveRateLimiter, RateLimitConfig


class BatchStatus(str, Enum):
    """Status of batch processing."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class BatchItem:
    """Single item in a batch."""
    index: int
    chunk_id: str
    content: str
    status: str = "pending"
    vector: Optional[List[float]] = None
    error: Optional[str] = None


@dataclass
class BatchProgress:
    """Progress tracking for batch processing."""
    total: int = 0
    completed: int = 0
    failed: int = 0
    cached: int = 0
    current_batch: int = 0
    total_batches: int = 0
    speed: float = 0.0
    eta_seconds: float = 0.0
    status: BatchStatus = BatchStatus.PENDING
    current_item: Optional[str] = None
    
    @property
    def percentage(self) -> float:
        """Calculate completion percentage."""
        processed = self.completed + self.failed + self.cached
        return (processed / self.total) * 100 if self.total > 0 else 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total": self.total,
            "completed": self.completed,
            "failed": self.failed,
            "cached": self.cached,
            "current_batch": self.current_batch,
            "total_batches": self.total_batches,
            "speed": round(self.speed, 2),
            "eta_seconds": round(self.eta_seconds, 1),
            "status": self.status.value,
            "percentage": round(self.percentage, 1),
            "current_item": self.current_item,
        }


@dataclass
class BatchResult:
    """Result of batch processing."""
    success_count: int = 0
    failed_count: int = 0
    cached_count: int = 0
    total_time_seconds: float = 0.0
    vectors: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[Dict[str, str]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success_count": self.success_count,
            "failed_count": self.failed_count,
            "cached_count": self.cached_count,
            "total_time_seconds": round(self.total_time_seconds, 2),
            "vectors_count": len(self.vectors),
            "errors_count": len(self.errors),
        }


class BatchEmbeddingService:
    """
    Service for batch embedding with parallel processing.
    
    Features:
    - Configurable batch size and concurrency
    - Adaptive rate limiting
    - Progress tracking with SSE support
    - Graceful error handling
    """
    
    def __init__(
        self,
        embed_func: Callable,
        config: Optional[EmbeddingConfig] = None,
    ):
        """
        Initialize batch service.
        
        Args:
            embed_func: Async function to embed single content
            config: Embedding configuration
        """
        self.embed_func = embed_func
        self.config = config or EmbeddingConfig()
        
        # Rate limiter
        rate_config = RateLimitConfig(
            initial_rate=self.config.concurrency,
            max_rate=self.config.concurrency * 2,
        )
        self.rate_limiter = AdaptiveRateLimiter(rate_config)
        
        # State
        self._cancelled = False
        self._progress = BatchProgress()
    
    async def process_batch(
        self,
        items: List[Dict[str, Any]],
        progress_callback: Optional[Callable[[BatchProgress], None]] = None,
    ) -> BatchResult:
        """
        Process a batch of items.
        
        Args:
            items: List of items with 'chunk_id' and 'content'
            progress_callback: Optional callback for progress updates
            
        Returns:
            BatchResult with vectors and errors
        """
        self._cancelled = False
        start_time = time.time()
        
        # Initialize progress
        self._progress = BatchProgress(
            total=len(items),
            total_batches=(len(items) + self.config.batch_size - 1) // self.config.batch_size,
            status=BatchStatus.PROCESSING,
        )
        
        result = BatchResult()
        
        # Split into batches
        batches = self._split_batches(items)
        
        try:
            for batch_idx, batch in enumerate(batches):
                if self._cancelled:
                    self._progress.status = BatchStatus.CANCELLED
                    break
                
                self._progress.current_batch = batch_idx + 1
                
                # Process batch with concurrency control
                batch_results = await self._process_single_batch(
                    batch, progress_callback
                )
                
                # Aggregate results
                for item_result in batch_results:
                    if item_result.get('success'):
                        result.success_count += 1
                        result.vectors.append({
                            'chunk_id': item_result['chunk_id'],
                            'vector': item_result['vector'],
                        })
                    elif item_result.get('cached'):
                        result.cached_count += 1
                        result.vectors.append({
                            'chunk_id': item_result['chunk_id'],
                            'vector': item_result['vector'],
                        })
                    else:
                        result.failed_count += 1
                        result.errors.append({
                            'chunk_id': item_result['chunk_id'],
                            'error': item_result.get('error', 'Unknown error'),
                        })
            
            # Set final status
            if self._cancelled:
                self._progress.status = BatchStatus.CANCELLED
            elif result.failed_count > 0 and result.success_count > 0:
                self._progress.status = BatchStatus.PARTIAL
            elif result.failed_count > 0:
                self._progress.status = BatchStatus.FAILED
            else:
                self._progress.status = BatchStatus.COMPLETED
                
        except Exception as e:
            self._progress.status = BatchStatus.FAILED
            raise
        finally:
            result.total_time_seconds = time.time() - start_time
        
        return result
    
    async def process_with_sse(
        self,
        items: List[Dict[str, Any]],
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Process batch with SSE progress streaming.
        
        Yields progress events and final result.
        
        Args:
            items: List of items to process
            
        Yields:
            Progress and result events
        """
        # Initial event
        yield {
            "event": "start",
            "data": {
                "total": len(items),
                "batch_size": self.config.batch_size,
            }
        }
        
        # Process with progress callback
        async def on_progress(progress: BatchProgress):
            yield {
                "event": "progress",
                "data": progress.to_dict(),
            }
        
        result = await self.process_batch(items)
        
        # Final event
        yield {
            "event": "complete",
            "data": result.to_dict(),
        }
    
    def cancel(self):
        """Cancel ongoing batch processing."""
        self._cancelled = True
    
    def get_progress(self) -> BatchProgress:
        """Get current progress."""
        return self._progress
    
    async def _process_single_batch(
        self,
        batch: List[Dict[str, Any]],
        progress_callback: Optional[Callable[[BatchProgress], None]],
    ) -> List[Dict[str, Any]]:
        """Process a single batch with concurrency control."""
        semaphore = asyncio.Semaphore(self.config.concurrency)
        results = []
        
        async def process_item(item: Dict[str, Any]) -> Dict[str, Any]:
            async with semaphore:
                if self._cancelled:
                    return {
                        'chunk_id': item.get('chunk_id', ''),
                        'success': False,
                        'error': 'Cancelled',
                    }
                
                chunk_id = item.get('chunk_id', item.get('id', ''))
                content = item.get('content', '')
                
                self._progress.current_item = chunk_id[:20] + "..." if len(chunk_id) > 20 else chunk_id
                
                try:
                    # Call embedding function
                    vector = await self.embed_func(content)
                    
                    self._progress.completed += 1
                    self.rate_limiter.on_success()
                    
                    return {
                        'chunk_id': chunk_id,
                        'success': True,
                        'vector': vector,
                    }
                except Exception as e:
                    self._progress.failed += 1
                    self.rate_limiter.on_error()
                    
                    return {
                        'chunk_id': chunk_id,
                        'success': False,
                        'error': str(e),
                    }
        
        # Process all items concurrently
        tasks = [process_item(item) for item in batch]
        results = await asyncio.gather(*tasks, return_exceptions=False)
        
        # Update speed and ETA
        elapsed = time.time()
        processed = self._progress.completed + self._progress.failed + self._progress.cached
        if processed > 0:
            self._progress.speed = processed / elapsed if elapsed > 0 else 0
            remaining = self._progress.total - processed
            self._progress.eta_seconds = remaining / self._progress.speed if self._progress.speed > 0 else 0
        
        # Call progress callback
        if progress_callback:
            progress_callback(self._progress)
        
        return results
    
    def _split_batches(
        self,
        items: List[Dict[str, Any]],
    ) -> List[List[Dict[str, Any]]]:
        """Split items into batches."""
        batches = []
        for i in range(0, len(items), self.config.batch_size):
            batches.append(items[i:i + self.config.batch_size])
        return batches


# Factory function
def create_batch_service(
    embed_func: Callable,
    batch_size: int = 50,
    concurrency: int = 5,
) -> BatchEmbeddingService:
    """
    Create batch embedding service.
    
    Args:
        embed_func: Async function to embed single content
        batch_size: Items per batch
        concurrency: Max concurrent requests
        
    Returns:
        BatchEmbeddingService instance
    """
    config = EmbeddingConfig(
        batch_size=batch_size,
        concurrency=concurrency,
    )
    return BatchEmbeddingService(embed_func, config)
