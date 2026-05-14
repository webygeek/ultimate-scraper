"""
Self-contained retry logic with exponential backoff.
No external services required.
"""
import time
import random
import functools
import threading
from typing import Callable, TypeVar, Optional

T = TypeVar('T')


class RetryConfig:
    """Configuration for retry behavior."""
    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: float = 0.1,
        retry_on_status_codes: tuple = (429, 500, 502, 503, 504),
    ):
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retry_on_status_codes = retry_on_status_codes


class RetryHandler:
    """
    Self-contained retry handler with exponential backoff.
    """

    def __init__(self, config: RetryConfig):
        self.config = config

    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay with exponential backoff and jitter."""
        delay = min(
            self.config.initial_delay * (self.config.exponential_base ** attempt),
            self.config.max_delay
        )
        jitter_range = delay * self.config.jitter
        delay += random.uniform(-jitter_range, jitter_range)
        return max(0, delay)

    def should_retry(self, attempt: int, status_code: Optional[int] = None) -> bool:
        """Check if we should retry."""
        if attempt >= self.config.max_attempts:
            return False

        if status_code:
            return status_code in self.config.retry_on_status_codes

        return True

    def execute(self, func: Callable[[], T], on_retry: Optional[Callable] = None) -> T:
        """Execute function with retry logic."""
        last_exception = None

        for attempt in range(self.config.max_attempts):
            try:
                return func()
            except Exception as e:
                last_exception = e

                # Check if we should retry
                status_code = getattr(e, 'response', None)
                if hasattr(status_code, 'status_code'):
                    status_code = status_code.status_code
                else:
                    status_code = None

                if not self.should_retry(attempt, status_code):
                    raise

                if attempt < self.config.max_attempts - 1:
                    delay = self.calculate_delay(attempt)
                    if on_retry:
                        on_retry(attempt + 1, e, delay)
                    time.sleep(delay)

        raise last_exception


def retry_with_backoff(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: float = 0.1,
    retry_status_codes: tuple = (429, 500, 502, 503, 504),
):
    """
    Decorator for retry logic.

    Usage:
        @retry_with_backoff(max_attempts=5)
        def fetch_url(url):
            return requests.get(url)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e

                    status_code = getattr(e, 'response', None)
                    if hasattr(status_code, 'status_code'):
                        status_code = status_code.status_code
                    else:
                        status_code = None

                    should_retry = False
                    if status_code and status_code in retry_status_codes:
                        should_retry = True
                    elif isinstance(e, (ConnectionError, TimeoutError, OSError)):
                        should_retry = True

                    if not should_retry or attempt >= max_attempts - 1:
                        raise

                    delay = min(
                        initial_delay * (exponential_base ** attempt),
                        max_delay
                    )
                    delay += random.uniform(-jitter * delay, jitter * delay)

                    time.sleep(delay)

            raise last_exception

        return wrapper
    return decorator


class CircuitBreaker:
    """
    Circuit breaker pattern - prevents cascading failures.
    Opens circuit after failures, closes after recovery timeout.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = "closed"  # closed, open, half-open
        self._lock = threading.Lock()

    def call(self, func: Callable[[], T], *args, **kwargs) -> T:
        """Execute with circuit breaker protection."""
        import threading
        if self._lock is None:
            self._lock = threading.Lock()

        with self._lock:
            if self.state == "open":
                if time.time() - self.last_failure_time >= self.recovery_timeout:
                    self.state = "half-open"
                else:
                    raise CircuitBreakerOpen(
                        f"Circuit breaker open. Retry after {self.recovery_timeout}s"
                    )

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _on_success(self):
        """Handle successful call."""
        import threading
        with self._lock:
            self.failure_count = 0
            if self.state == "half-open":
                self.state = "closed"

    def _on_failure(self):
        """Handle failed call."""
        import threading
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            if self.failure_count >= self.failure_threshold:
                self.state = "open"

    def reset(self):
        """Reset the circuit breaker."""
        import threading
        with self._lock:
            self.failure_count = 0
            self.state = "closed"
            self.last_failure_time = None


class CircuitBreakerOpen(Exception):
    """Exception raised when circuit breaker is open."""
    pass
