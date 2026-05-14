"""
Self-contained anti-detection module.
100% built-in - rotates user agents, manages cookies, evades fingerprinting.
"""
import random
import time
import hashlib
import requests
from typing import Optional
from urllib.parse import urlparse


class AntiDetection:
    """
    Self-contained anti-detection with no external dependencies.
    """

    def __init__(self, config: dict):
        self.config = config.get("anti_detection", {})
        self.enabled = self.config.get("enabled", True)

        # Load user agents from config
        self.user_agents = self.config.get("user_agents", [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        ])

        # Load proxies
        self.proxies = self._load_proxies()
        self.current_proxy_index = 0

        self._last_user_agent = None
        self._cookies = {}  # Session cookies
        self._request_times = []

    def _load_proxies(self) -> list[dict]:
        """Load proxies from config."""
        configured = self.config.get("proxies", [])
        proxies = []

        for p in configured:
            if p:
                proxy_url = p if p.startswith("http") else f"http://{p}"
                proxies.append({
                    "http": proxy_url,
                    "https": proxy_url,
                })

        return proxies

    def get_random_user_agent(self) -> str:
        """Get a random user agent avoiding consecutive repeats."""
        if not self.enabled:
            return self.user_agents[0]

        available = [ua for ua in self.user_agents if ua != self._last_user_agent]
        if not available:
            available = self.user_agents

        selected = random.choice(available)
        self._last_user_agent = selected
        return selected

    def get_random_proxy(self) -> Optional[dict]:
        """Get next proxy in rotation."""
        if not self.proxies:
            return None

        proxy = self.proxies[self.current_proxy_index]
        self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxies)
        return proxy

    def get_headers(self, url: Optional[str] = None) -> dict:
        """Generate realistic browser headers."""
        user_agent = self.get_random_user_agent()

        base_headers = {
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
        }

        if url:
            parsed = urlparse(url)
            base_headers["Referer"] = f"{parsed.scheme}://{parsed.netloc}/"

            # Customize for specific sites
            if "google" in parsed.netloc:
                base_headers["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            elif "amazon" in parsed.netloc:
                base_headers["Accept-Language"] = "en-US,en;q=0.9"
                base_headers["TE"] = "Trailers"

        return base_headers

    def wait_between_requests(self, min_seconds: float = 1.0, max_seconds: float = 5.0):
        """Add randomized delay to appear human-like."""
        if not self.enabled:
            return

        delay = random.uniform(min_seconds, max_seconds)
        now = time.time()
        self._request_times.append(now)

        if random.random() < 0.1:
            delay *= 2

        time.sleep(delay)

    def should_use_proxy(self) -> bool:
        """Decide if proxy should be used."""
        if not self.enabled or not self.proxies:
            return False
        return random.random() < 0.3

    def save_cookies(self, domain: str, cookies: dict):
        """Save cookies for session persistence."""
        if domain not in self._cookies:
            self._cookies[domain] = {}
        self._cookies[domain].update(cookies)

    def get_cookies(self, domain: str) -> dict:
        """Get saved cookies for domain."""
        return self._cookies.get(domain, {})

    def generate_fingerprint(self) -> str:
        """Generate a unique fingerprint hash."""
        components = [
            self.get_random_user_agent(),
            str(random.randint(1000, 9999)),
            str(time.time()),
        ]
        return hashlib.md5("".join(components).encode()).hexdigest()


class RequestSession:
    """
    Self-contained requests session with anti-detection.
    """

    def __init__(self, config: dict):
        self.config = config
        self.anti_detection = AntiDetection(config)
        self.request_config = config.get("requests", {})
        self._session_cookies = {}

    def get(self, url: str, **kwargs) -> "requests.Response":
        """Perform GET request with anti-detection."""
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry

        # Create session with retry
        session = requests.Session()
        retry_strategy = Retry(
            total=self.request_config.get("max_retries", 3),
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # Anti-detection
        self.anti_detection.wait_between_requests()
        headers = self.anti_detection.get_headers(url)
        kwargs.setdefault("headers", headers)
        kwargs.setdefault("timeout", self.request_config.get("timeout", 30))

        proxy = None
        if self.anti_detection.should_use_proxy():
            proxy = self.anti_detection.get_random_proxy()
            if proxy:
                kwargs["proxies"] = proxy

        # Set cookies if any saved
        from urllib.parse import urlparse
        domain = urlparse(url).netloc
        cookies = self.anti_detection.get_cookies(domain)
        if cookies:
            kwargs["cookies"] = cookies

        response = session.get(url, **kwargs)

        # Save cookies
        if response.cookies:
            self.anti_detection.save_cookies(domain, dict(response.cookies))

        return response

    def post(self, url: str, **kwargs) -> "requests.Response":
        """Perform POST request with anti-detection."""

        self.anti_detection.wait_between_requests()
        headers = self.anti_detection.get_headers(url)
        kwargs.setdefault("headers", headers)
        kwargs.setdefault("timeout", self.request_config.get("timeout", 30))

        proxy = None
        if self.anti_detection.should_use_proxy():
            proxy = self.anti_detection.get_random_proxy()
            if proxy:
                kwargs["proxies"] = proxy

        return requests.post(url, **kwargs)

    def close(self):
        """Close session."""
        pass  # Session closes automatically
