"""
Exponential backoff retry utility for embedding service.

Implements exponential backoff with jitter for resilient API calls.
"""
import time
import random
import logging
from typing import Callable, TypeVar, Optional, Tuple
from functools import wraps

from ..models.embedding_models import RateLimitError

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ExponentialBackoffRetry:
    """
    Exponential backoff retry handler with jitter.
    
    Configuration:
    - Initial delay: 1 second
    - Max delay: 32 seconds
    - Backoff multiplier: 2x
    - Jitter: ±25%
    - Default max retries: 3 attempts
    """
    
    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 32.0,
        jitter_pct: float = 0.25
    ):
        """
        Initialize retry handler.
        
        Args:
            max_retries: Maximum number of retry attempts
            initial_delay: Initial delay in seconds
            max_delay: Maximum delay cap in seconds
            jitter_pct: Jitter percentage (0.25 = ±25%)
        """
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.jitter_pct = jitter_pct
    
    def _calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay with exponential backoff and jitter.
        
        Formula: min(initial_delay * (2 ** attempt), max_delay) + jitter
        
        Args:
            attempt: Current attempt number (0-based)
            
        Returns:
            Delay duration in seconds
        """
        # Exponential backoff
        delay = min(self.initial_delay * (2 ** attempt), self.max_delay)
        
        # Add jitter (±25%)
        jitter = delay * random.uniform(-self.jitter_pct, self.jitter_pct)
        
        return delay + jitter
    
    def execute(
        self,
        func: Callable[[], T],
        retryable_exceptions: tuple = (Exception,),
        on_retry: Optional[Callable[[Exception, int, float], None]] = None
    ) -> T:
        """
        Execute function with retry logic.
        
        Args:
            func: Function to execute
            retryable_exceptions: Tuple of exceptions that trigger retry
            on_retry: Optional callback on retry (exception, attempt, delay)
            
        Returns:
            Function result
            
        Raises:
            Last exception if all retries exhausted
        """
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                return func()
            except retryable_exceptions as e:
                last_exception = e
                
                if attempt == self.max_retries - 1:
                    # Last attempt failed, re-raise
                    logger.error(
                        f"All {self.max_retries} retry attempts exhausted",
                        extra={
                            "error_type": type(e).__name__,
                            "error_message": str(e),
                            "total_attempts": self.max_retries
                        }
                    )
                    raise
                
                # Calculate delay and wait
                delay = self._calculate_delay(attempt)
                
                logger.warning(
                    f"Retry attempt {attempt + 1}/{self.max_retries}",
                    extra={
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                        "retry_delay_ms": delay * 1000,
                        "next_attempt": attempt + 2
                    }
                )
                
                # Call retry callback if provided
                if on_retry:
                    on_retry(e, attempt + 1, delay)
                
                time.sleep(delay)
        
        # Should never reach here, but for type safety
        if last_exception:
            raise last_exception
        raise RuntimeError("Retry logic error: no exception but no success")


def detect_rate_limit_error(error: Exception) -> Tuple[bool, Optional[int]]:
    """Detect whether an exception represents a rate limit condition.

    Args:
        error: Exception raised by upstream API client

    Returns:
        Tuple[bool, Optional[int]] indicating whether error is rate limit and retry-after seconds
    """
    if isinstance(error, RateLimitError):
        return True, getattr(error, 'retry_after', None)

    status_code = getattr(error, 'status_code', None)
    if status_code == 429:
        retry_after_header = None
        response = getattr(error, 'response', None)
        if response is not None:
            headers = getattr(response, 'headers', {})
            retry_after_header = headers.get('retry-after') or headers.get('Retry-After')
        try:
            retry_after_value = int(retry_after_header) if retry_after_header else None
        except (TypeError, ValueError):
            retry_after_value = None
        return True, retry_after_value

    message = str(error).lower()
    if 'rate limit' in message or 'too many requests' in message:
        return True, None

    return False, None


def with_retry(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 32.0,
    retryable_exceptions: tuple = (Exception,)
):
    """
    Decorator for automatic retry with exponential backoff.
    
    Usage:
        @with_retry(max_retries=5, retryable_exceptions=(RateLimitError,))
        def call_api():
            return api.request()
    
    Args:
        max_retries: Maximum retry attempts
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay cap in seconds
        retryable_exceptions: Exceptions that trigger retry
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            retry_handler = ExponentialBackoffRetry(
                max_retries=max_retries,
                initial_delay=initial_delay,
                max_delay=max_delay
            )
            return retry_handler.execute(
                lambda: func(*args, **kwargs),
                retryable_exceptions=retryable_exceptions
            )
        return wrapper
    return decorator


# Utility function for quick retry
def retry_on_rate_limit(func: Callable[[], T], max_retries: int = 3) -> T:
    """
    Quick utility for retrying rate-limited operations.
    
    Args:
        func: Function to execute
        max_retries: Maximum retry attempts
        
    Returns:
        Function result
    """
    # Import here to avoid circular dependency
    try:
        from ..models.embedding_models import RateLimitError
        retryable = (RateLimitError,)
    except ImportError:
        # Fallback if models not yet available
        retryable = (Exception,)
    
    retry_handler = ExponentialBackoffRetry(max_retries=max_retries)
    return retry_handler.execute(func, retryable_exceptions=retryable)
