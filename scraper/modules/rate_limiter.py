"""
Self-contained rate limiting with built-in algorithms.
No external services required.
"""
import time
import threading
from collections import deque
from typing import Optional


class SlidingWindowRateLimiter:
    """
    Sliding window rate limiter - pure Python implementation.
    """

    def __init__(self, max_requests: int, window_seconds: float):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = deque()
        self.lock = threading.Lock()

    def acquire(self, timeout: Optional[float] = None) -> bool:
        """Acquire permission to make a request."""
        start_time = time.time()

        while True:
            with self.lock:
                now = time.time()
                cutoff = now - self.window_seconds

                while self.requests and self.requests[0] < cutoff:
                    self.requests.popleft()

                if len(self.requests) < self.max_requests:
                    self.requests.append(now)
                    return True

            if timeout and (time.time() - start_time) >= timeout:
                return False

            time.sleep(0.1)

    def get_wait_time(self) -> float:
        """Get estimated wait time."""
        with self.lock:
            if len(self.requests) < self.max_requests:
                return 0
            oldest = self.requests[0]
            return max(0, oldest + self.window_seconds - time.time())

    def reset(self):
        """Reset the limiter."""
        with self.lock:
            self.requests.clear()


class AdaptiveRateLimiter:
    """
    Self-contained adaptive rate limiter.
    Adjusts based on response codes automatically.
    """

    def __init__(self, config: dict):
        self.config = config
        request_config = config.get("requests", {})

        self.default_delay = request_config.get("rate_limit", {}).get("delay_between_requests", 3)
        self.current_delay = self.default_delay
        self.min_delay = 1.0
        self.max_delay = 60.0
        self.backoff_factor = 2.0
        self.recovery_factor = 0.95

        self.failed_domains: dict[str, float] = {}
        self.lock = threading.Lock()

        # Per-domain limiters
        self.domain_limiters: dict[str, SlidingWindowRateLimiter] = {}

    def _get_domain_limiter(self, domain: str) -> SlidingWindowRateLimiter:
        """Get or create limiter for domain."""
        if domain not in self.domain_limiters:
            rpm = self.config.get("requests", {}).get("rate_limit", {}).get("requests_per_minute", 20)
            self.domain_limiters[domain] = SlidingWindowRateLimiter(rpm, 60)
        return self.domain_limiters[domain]

    def acquire(self, domain: str, timeout: Optional[float] = None) -> bool:
        """Acquire permission with adaptive delay."""
        with self.lock:
            if domain in self.failed_domains:
                cooldown_end = self.failed_domains[domain]
                if time.time() < cooldown_end:
                    wait = cooldown_end - time.time()
                    if timeout:
                        time.sleep(min(wait, timeout))
                    return False
                else:
                    del self.failed_domains[domain]

        # Apply delay
        time.sleep(self.current_delay)

        # Acquire from domain limiter
        limiter = self._get_domain_limiter(domain)
        return limiter.acquire(timeout)

    def report_success(self, domain: str):
        """Report success - gradually speed up."""
        with self.lock:
            self.current_delay = max(self.min_delay, self.current_delay * self.recovery_factor)

    def report_rate_limited(self, domain: str, retry_after: Optional[int] = None):
        """Report rate limited - slow down."""
        with self.lock:
            if retry_after:
                cooldown = retry_after
            else:
                cooldown = self.current_delay * self.backoff_factor

            self.current_delay = min(self.max_delay, cooldown)
            self.failed_domains[domain] = time.time() + cooldown

    def report_error(self, domain: str, status_code: int):
        """Report error based on status code."""
        if status_code == 429:
            self.report_rate_limited(domain)
        elif status_code >= 500:
            with self.lock:
                self.current_delay = min(self.max_delay, self.current_delay * 1.5)

    def reset(self, domain: Optional[str] = None):
        """Reset rate limits."""
        if domain:
            if domain in self.domain_limiters:
                self.domain_limiters[domain].reset()
            if domain in self.failed_domains:
                del self.failed_domains[domain]
        else:
            self.domain_limiters.clear()
            self.failed_domains.clear()
            self.current_delay = self.default_delay


class GlobalRateLimiter:
    """
    Global rate limiter singleton.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, config: Optional[dict] = None):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, config: Optional[dict] = None):
        if self._initialized:
            return

        if config is None:
            config = {}

        self.adaptive_limiter = AdaptiveRateLimiter(config)
        self.global_limiter = SlidingWindowRateLimiter(1000, 3600)
        self.total_requests = 0
        self.start_time = time.time()
        self._initialized = True

    def acquire(self, domain: str, timeout: Optional[float] = None) -> bool:
        """Acquire permission to make a request."""
        if not self.global_limiter.acquire(timeout):
            return False

        if not self.adaptive_limiter.acquire(domain, timeout):
            return False

        self.total_requests += 1
        return True

    def report_success(self, domain: str):
        """Report successful request."""
        self.adaptive_limiter.report_success(domain)

    def report_rate_limited(self, domain: str, retry_after: Optional[int] = None):
        """Report rate limited."""
        self.adaptive_limiter.report_rate_limited(domain, retry_after)

    def report_error(self, domain: str, status_code: int):
        """Report error."""
        self.adaptive_limiter.report_error(domain, status_code)

    def get_stats(self) -> dict:
        """Get statistics."""
        elapsed = time.time() - self.start_time
        return {
            "total_requests": self.total_requests,
            "requests_per_minute": self.total_requests / (elapsed / 60) if elapsed > 0 else 0,
            "current_delay": self.adaptive_limiter.current_delay,
            "elapsed_seconds": elapsed,
        }

    def reset(self):
        """Reset all limits."""
        self.adaptive_limiter.reset()
        self.global_limiter.reset()
        self.total_requests = 0
        self.start_time = time.time()
