"""
Rate limiter with adaptive throttling for API calls.

Implements:
- Token bucket algorithm
- Adaptive rate adjustment based on API responses
- Concurrent request limiting
"""
import asyncio
import time
from dataclasses import dataclass, field
from typing import Optional, Callable, Any
from enum import Enum


class RateLimitState(str, Enum):
    """Rate limiter state."""
    NORMAL = "normal"
    THROTTLED = "throttled"
    RECOVERING = "recovering"


@dataclass
class RateLimitConfig:
    """Configuration for rate limiter."""
    initial_rate: int = 5           # 初始请求速率（请求/秒）
    min_rate: int = 1               # 最小速率
    max_rate: int = 20              # 最大速率
    increase_threshold: int = 10    # 连续成功多少次后提升速率
    recovery_delay: float = 1.0     # 限流后恢复等待时间（秒）
    burst_size: int = 10            # 允许的突发请求数


@dataclass
class RateLimitStats:
    """Statistics for rate limiter."""
    total_requests: int = 0
    successful_requests: int = 0
    throttled_requests: int = 0
    rate_limit_hits: int = 0
    current_rate: int = 5
    state: RateLimitState = RateLimitState.NORMAL
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "throttled_requests": self.throttled_requests,
            "rate_limit_hits": self.rate_limit_hits,
            "current_rate": self.current_rate,
            "state": self.state.value,
            "success_rate": self.successful_requests / self.total_requests if self.total_requests > 0 else 0,
        }


class AdaptiveRateLimiter:
    """
    Adaptive rate limiter that adjusts based on API responses.
    
    Features:
    - Automatic rate reduction on rate limit errors
    - Gradual rate recovery after success streak
    - Semaphore-based concurrent request limiting
    """
    
    def __init__(self, config: Optional[RateLimitConfig] = None):
        self.config = config or RateLimitConfig()
        self.current_rate = self.config.initial_rate
        self.semaphore = asyncio.Semaphore(self.config.initial_rate)
        
        # State tracking
        self.state = RateLimitState.NORMAL
        self.success_streak = 0
        self.failure_streak = 0
        self.last_rate_limit_time: Optional[float] = None
        
        # Statistics
        self.stats = RateLimitStats(current_rate=self.current_rate)
        
        # Token bucket for burst control
        self.tokens = float(self.config.burst_size)
        self.last_token_time = time.time()
    
    def _refill_tokens(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_token_time
        self.tokens = min(
            self.config.burst_size,
            self.tokens + elapsed * self.current_rate
        )
        self.last_token_time = now
    
    async def acquire(self) -> bool:
        """
        Acquire permission to make a request.
        
        Returns:
            True if request is allowed, False if throttled
        """
        self._refill_tokens()
        
        if self.tokens < 1:
            self.stats.throttled_requests += 1
            return False
        
        self.tokens -= 1
        self.stats.total_requests += 1
        return True
    
    def on_success(self) -> None:
        """Called when a request succeeds."""
        self.success_streak += 1
        self.failure_streak = 0
        self.stats.successful_requests += 1
        
        # Try to increase rate after success streak
        if self.success_streak >= self.config.increase_threshold:
            if self.current_rate < self.config.max_rate:
                self.current_rate = min(self.current_rate + 1, self.config.max_rate)
                self._update_semaphore()
            self.success_streak = 0
            
            if self.state == RateLimitState.RECOVERING:
                self.state = RateLimitState.NORMAL
        
        self.stats.current_rate = self.current_rate
        self.stats.state = self.state
    
    def on_rate_limit(self, retry_after: Optional[float] = None) -> float:
        """
        Called when a rate limit error is encountered.
        
        Args:
            retry_after: Suggested wait time from API (if provided)
            
        Returns:
            Recommended wait time in seconds
        """
        self.failure_streak += 1
        self.success_streak = 0
        self.stats.rate_limit_hits += 1
        self.last_rate_limit_time = time.time()
        
        # Immediately reduce rate
        self.current_rate = max(self.current_rate // 2, self.config.min_rate)
        self._update_semaphore()
        
        self.state = RateLimitState.THROTTLED
        self.stats.current_rate = self.current_rate
        self.stats.state = self.state
        
        # Calculate wait time
        if retry_after is not None:
            return retry_after
        
        # Exponential backoff based on failure streak
        return min(
            self.config.recovery_delay * (2 ** min(self.failure_streak - 1, 5)),
            60.0  # Max 60 seconds
        )
    
    def on_error(self) -> None:
        """Called when a non-rate-limit error occurs."""
        self.failure_streak += 1
        self.success_streak = 0
        
        # Don't reduce rate as aggressively for other errors
        if self.failure_streak >= 3:
            self.current_rate = max(self.current_rate - 1, self.config.min_rate)
            self._update_semaphore()
        
        self.stats.current_rate = self.current_rate
    
    def _update_semaphore(self) -> None:
        """Update semaphore to match current rate."""
        # Create new semaphore with updated limit
        self.semaphore = asyncio.Semaphore(self.current_rate)
    
    async def execute(
        self,
        func: Callable[..., Any],
        *args,
        **kwargs
    ) -> Any:
        """
        Execute a function with rate limiting.
        
        Args:
            func: Async function to execute
            *args, **kwargs: Arguments to pass to function
            
        Returns:
            Function result
        """
        # Wait for permission
        while not await self.acquire():
            await asyncio.sleep(0.1)
        
        async with self.semaphore:
            try:
                result = await func(*args, **kwargs)
                self.on_success()
                return result
            except Exception as e:
                # Check if it's a rate limit error
                if self._is_rate_limit_error(e):
                    retry_after = self._extract_retry_after(e)
                    wait_time = self.on_rate_limit(retry_after)
                    raise RateLimitException(str(e), wait_time)
                else:
                    self.on_error()
                    raise
    
    def _is_rate_limit_error(self, error: Exception) -> bool:
        """Check if error is a rate limit error."""
        error_str = str(error).lower()
        return any(keyword in error_str for keyword in [
            "rate limit", "ratelimit", "too many requests", "429"
        ])
    
    def _extract_retry_after(self, error: Exception) -> Optional[float]:
        """Extract retry-after value from error if available."""
        # Try to extract from error attributes
        if hasattr(error, 'retry_after'):
            return error.retry_after
        
        # Try to parse from error message
        import re
        match = re.search(r'retry.?after[:\s]+(\d+(?:\.\d+)?)', str(error).lower())
        if match:
            return float(match.group(1))
        
        return None
    
    def get_stats(self) -> RateLimitStats:
        """Get current statistics."""
        return self.stats
    
    def reset(self) -> None:
        """Reset rate limiter to initial state."""
        self.current_rate = self.config.initial_rate
        self.semaphore = asyncio.Semaphore(self.config.initial_rate)
        self.state = RateLimitState.NORMAL
        self.success_streak = 0
        self.failure_streak = 0
        self.tokens = float(self.config.burst_size)
        self.stats = RateLimitStats(current_rate=self.current_rate)


class RateLimitException(Exception):
    """Exception raised when rate limit is hit."""
    
    def __init__(self, message: str, retry_after: float):
        super().__init__(message)
        self.retry_after = retry_after


class SyncRateLimiter:
    """
    Synchronous rate limiter for non-async code.
    
    Uses simple token bucket algorithm.
    """
    
    def __init__(self, rate: int = 5, burst_size: int = 10):
        self.rate = rate
        self.burst_size = burst_size
        self.tokens = float(burst_size)
        self.last_update = time.time()
        self._lock = None  # Lazy initialization for threading
    
    def _get_lock(self):
        """Get or create threading lock."""
        if self._lock is None:
            import threading
            self._lock = threading.Lock()
        return self._lock
    
    def acquire(self, timeout: float = 10.0) -> bool:
        """
        Acquire permission to make a request.
        
        Args:
            timeout: Maximum time to wait for permission
            
        Returns:
            True if acquired, False if timeout
        """
        deadline = time.time() + timeout
        
        while time.time() < deadline:
            with self._get_lock():
                # Refill tokens
                now = time.time()
                elapsed = now - self.last_update
                self.tokens = min(
                    self.burst_size,
                    self.tokens + elapsed * self.rate
                )
                self.last_update = now
                
                if self.tokens >= 1:
                    self.tokens -= 1
                    return True
            
            # Wait before retry
            time.sleep(0.1)
        
        return False
    
    def __enter__(self):
        """Context manager entry."""
        if not self.acquire():
            raise RateLimitException("Rate limit timeout", 0)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        return False
