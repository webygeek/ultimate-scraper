"""
Proxy Manager - Rotating proxy pool with health checking.
"""
import time
import random
import threading
from typing import Dict, List, Optional
from dataclasses import dataclass
from queue import Queue, Empty
from loguru import logger


@dataclass
class Proxy:
    """A proxy server."""
    url: str
    protocol: str = "http"
    host: str = ""
    port: int = 0
    username: str = ""
    password: str = ""
    enabled: bool = True
    last_used: float = 0
    last_check: float = 0
    failures: int = 0
    success_count: int = 0
    avg_latency_ms: float = 0
    is_working: bool = True

    def __post_init__(self):
        if not self.host:
            self._parse_url()

    def _parse_url(self):
        """Parse proxy URL into components."""
        # Format: http://user:pass@host:port
        url = self.url
        if "://" not in url:
            url = f"http://{url}"

        if "@" in url:
            auth, rest = url.split("@", 1)
            if ":" in auth:
                self.username, self.password = auth.split(":", 1)
            url = rest

        # Remove protocol
        url = url.replace("http://", "").replace("https://", "")
        self.protocol = self.protocol

        # Parse host:port
        if ":" in url:
            self.host, port_str = url.split(":", 1)
            try:
                self.port = int(port_str)
            except ValueError:
                self.port = 8080
        else:
            self.host = url
            self.port = 8080

    def get_dict(self) -> Dict[str, str]:
        """Get proxy as dict for requests."""
        return {
            "http": self.url,
            "https": self.url,
        }

    @property
    def latency(self) -> float:
        """Calculate current latency estimate."""
        if self.avg_latency_ms == 0:
            return 100  # Default estimate
        return self.avg_latency_ms

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        total = self.success_count + self.failures
        if total == 0:
            return 1.0
        return self.success_count / total


class ProxyPool:
    """
    Pool of proxies with automatic rotation and health checking.
    """

    def __init__(
        self,
        proxies: List[str] = None,
        health_check_url: str = "https://httpbin.org/ip",
        health_check_interval: int = 300,  # 5 minutes
        max_failures: int = 3,
    ):
        self.proxies: Dict[str, Proxy] = {}
        self.health_check_url = health_check_url
        self.health_check_interval = health_check_interval
        self.max_failures = max_failures
        self.current_index = 0
        self.lock = threading.Lock()

        # Add proxies
        if proxies:
            for proxy_url in proxies:
                self.add_proxy(proxy_url)

    def add_proxy(self, proxy_url: str):
        """Add a proxy to the pool."""
        with self.lock:
            proxy = Proxy(url=proxy_url)
            self.proxies[proxy_url] = proxy
            logger.info(f"Added proxy: {proxy.host}:{proxy.port}")

    def remove_proxy(self, proxy_url: str):
        """Remove a proxy from the pool."""
        with self.lock:
            if proxy_url in self.proxies:
                del self.proxies[proxy_url]
                logger.info(f"Removed proxy: {proxy_url}")

    def get_next_proxy(self) -> Optional[Proxy]:
        """Get the next proxy in rotation."""
        with self.lock:
            enabled = [p for p in self.proxies.values() if p.enabled and p.is_working]

            if not enabled:
                return None

            # Sort by success rate and latency
            enabled.sort(key=lambda p: (-p.success_rate, p.latency))

            # Round-robin through best proxies
            proxy = enabled[self.current_index % len(enabled)]
            self.current_index = (self.current_index + 1) % len(enabled)

            proxy.last_used = time.time()
            return proxy

    def get_random_proxy(self) -> Optional[Proxy]:
        """Get a random working proxy."""
        with self.lock:
            enabled = [p for p in self.proxies.values() if p.enabled and p.is_working]

            if not enabled:
                return None

            return random.choice(enabled)

    def report_success(self, proxy_url: str, latency_ms: float = None):
        """Report successful use of a proxy."""
        with self.lock:
            if proxy_url not in self.proxies:
                return

            proxy = self.proxies[proxy_url]
            proxy.success_count += 1
            proxy.failures = 0  # Reset failures on success
            proxy.is_working = True

            if latency_ms:
                # Update average latency
                old_avg = proxy.avg_latency_ms
                proxy.avg_latency_ms = (old_avg * 0.7) + (latency_ms * 0.3)

    def report_failure(self, proxy_url: str):
        """Report failed use of a proxy."""
        with self.lock:
            if proxy_url not in self.proxies:
                return

            proxy = self.proxies[proxy_url]
            proxy.failures += 1

            if proxy.failures >= self.max_failures:
                proxy.is_working = False
                logger.warning(f"Proxy disabled after {proxy.failures} failures: {proxy_url}")

    def check_proxy_health(self, proxy: Proxy) -> bool:
        """Check if a proxy is working."""
        try:
            import requests

            start = time.time()
            response = requests.get(
                self.health_check_url,
                proxies=proxy.get_dict(),
                timeout=10,
            )
            latency_ms = (time.time() - start) * 1000

            if response.status_code == 200:
                self.report_success(proxy.url, latency_ms)
                return True

        except Exception as e:
            logger.debug(f"Proxy health check failed for {proxy.url}: {e}")

        self.report_failure(proxy.url)
        return False

    def check_all_health(self):
        """Check health of all proxies."""
        for proxy in list(self.proxies.values()):
            self.check_proxy_health(proxy)

    def get_working_count(self) -> int:
        """Get count of working proxies."""
        with self.lock:
            return sum(1 for p in self.proxies.values() if p.is_working)

    def get_stats(self) -> Dict:
        """Get proxy pool statistics."""
        with self.lock:
            total = len(self.proxies)
            working = sum(1 for p in self.proxies.values() if p.is_working)
            enabled = sum(1 for p in self.proxies.values() if p.enabled)

            avg_success = 0
            if self.proxies:
                avg_success = sum(p.success_rate for p in self.proxies.values()) / total

            return {
                "total": total,
                "working": working,
                "enabled": enabled,
                "average_success_rate": avg_success,
            }


class ProxyManager:
    """
    High-level proxy management with automatic rotation.
    """

    def __init__(self, config: Dict):
        self.config = config
        self.pool = ProxyPool()

        # Load proxies from config
        proxies = config.get("anti_detection", {}).get("proxies", [])
        for proxy in proxies:
            self.pool.add_proxy(proxy)

        # Health check settings
        self.health_check_interval = 300  # 5 minutes
        self.last_health_check = 0

    def get_proxy(self) -> Optional[Dict[str, str]]:
        """Get a working proxy for requests."""
        # Periodic health check
        if time.time() - self.last_health_check > self.health_check_interval:
            self.pool.check_all_health()
            self.last_health_check = time.time()

        proxy = self.pool.get_next_proxy()
        return proxy.get_dict() if proxy else None

    def report_success(self, proxy_url: str, latency_ms: float = None):
        """Report proxy success."""
        self.pool.report_success(proxy_url, latency_ms)

    def report_failure(self, proxy_url: str):
        """Report proxy failure."""
        self.pool.report_failure(proxy_url)

    def add_proxy(self, proxy_url: str):
        """Add a new proxy."""
        self.pool.add_proxy(proxy_url)

    def remove_proxy(self, proxy_url: str):
        """Remove a proxy."""
        self.pool.remove_proxy(proxy_url)

    def get_stats(self) -> Dict:
        """Get proxy statistics."""
        return self.pool.get_stats()
