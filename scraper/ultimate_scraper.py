"""
Ultimate Self-Evolving Scraper - Automatic technique selection and learning.
"""
import json
import time
import random
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from urllib.parse import urlparse
from dataclasses import dataclass, field, asdict
from pathlib import Path
from loguru import logger
import hashlib

# ============== DATA MODELS ==============

@dataclass
class Technique:
    """A scraping technique."""
    id: str = ""
    name: str = ""
    technique_type: str = ""  # browser, api, proxy, bypass
    method: str = ""
    challenge: str = ""
    success_rate: float = 0.5
    use_count: int = 0
    avg_time: float = 0.0
    code_snippet: str = ""
    tags: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.id:
            self.id = hashlib.md5(f"{self.name}{self.method}".encode()).hexdigest()[:16]


@dataclass
class WebsiteProfile:
    """Profile of a website's scraping characteristics."""
    domain: str = ""
    name: str = ""
    has_cloudflare: bool = False
    has_antibot: bool = False
    has_captcha: bool = False
    uses_lazy_load: bool = False
    requires_auth: bool = False
    best_method: str = ""
    best_success_rate: float = 0.0
    test_count: int = 0
    working_techniques: List[str] = field(default_factory=list)
    failed_techniques: List[str] = field(default_factory=list)
    last_tested: str = ""
    notes: str = ""


@dataclass
class ScrapeAttempt:
    """Record of a scraping attempt."""
    timestamp: str = ""
    url: str = ""
    domain: str = ""
    method_used: str = ""
    success: bool = False
    items_extracted: int = 0
    time_taken: float = 0.0
    challenges: Dict[str, bool] = field(default_factory=dict)
    error: str = ""


@dataclass
class Proxy:
    """A proxy entry."""
    url: str = ""
    proxy_type: str = "http"  # http, socks5, residential
    country: str = ""
    working: bool = True
    success_count: int = 0
    fail_count: int = 0
    avg_latency: float = 0.0
    last_used: str = ""
    last_checked: str = ""


# ============== AUTOMATIC TECHNIQUE SELECTOR ==============

class AutomaticTechniqueSelector:
    """
    Automatically selects the best technique based on:
    1. Past success rate for this website
    2. Challenge detection
    3. Technique performance history
    """

    # Technique registry with metadata
    TECHNIQUES = {
        "stealth_chrome": {
            "type": "browser",
            "challenges": ["cloudflare", "antibot", "detection"],
            "wait_time": 10,
            "priority": 1,
        },
        "stealth_firefox": {
            "type": "browser",
            "challenges": ["cloudflare", "antibot"],
            "wait_time": 12,
            "priority": 2,
        },
        "heavy_scroll": {
            "type": "browser",
            "challenges": ["lazy_load", "infinite_scroll"],
            "wait_time": 30,
            "priority": 1,
        },
        "api_intercept": {
            "type": "api",
            "challenges": ["dynamic_content", "ajax"],
            "wait_time": 5,
            "priority": 1,
        },
        "proxy_rotate": {
            "type": "proxy",
            "challenges": ["ip_block", "rate_limit", "geoblock"],
            "wait_time": 5,
            "priority": 1,
        },
        "wait_retry": {
            "type": "retry",
            "challenges": ["rate_limit", "temporary_block"],
            "wait_time": 60,
            "priority": 3,
        },
        "header_rotate": {
            "type": "bypass",
            "challenges": ["detection", "headers"],
            "wait_time": 5,
            "priority": 2,
        },
        "click_load_more": {
            "type": "browser",
            "challenges": ["lazy_load", "pagination"],
            "wait_time": 15,
            "priority": 2,
        },
    }

    def __init__(self, db_path: str = "data/scraper_profiles.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize database."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute("""
            CREATE TABLE IF NOT EXISTS technique_stats (
                method TEXT PRIMARY KEY,
                name TEXT,
                technique_type TEXT,
                success_count INTEGER DEFAULT 0,
                fail_count INTEGER DEFAULT 0,
                total_time REAL DEFAULT 0,
                tags TEXT
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS website_stats (
                domain TEXT PRIMARY KEY,
                name TEXT,
                has_cloudflare INTEGER DEFAULT 0,
                has_antibot INTEGER DEFAULT 0,
                has_captcha INTEGER DEFAULT 0,
                uses_lazy_load INTEGER DEFAULT 0,
                best_method TEXT,
                best_success_rate REAL DEFAULT 0,
                test_count INTEGER DEFAULT 0,
                last_tested TEXT
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS technique_website (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                domain TEXT,
                method TEXT,
                success INTEGER,
                items_extracted INTEGER DEFAULT 0,
                time_taken REAL DEFAULT 0,
                challenges TEXT,
                timestamp TEXT
            )
        """)

        conn.commit()
        conn.close()

    def detect_challenges(self, html: str, title: str = "", status: int = 200) -> Dict[str, bool]:
        """Detect challenges in response."""
        challenges = {
            "cloudflare": False,
            "antibot": False,
            "captcha": False,
            "lazy_load": False,
            "rate_limit": False,
            "empty": len(html) < 1000,
        }

        content = (html + title).lower()

        cloudflare_signs = ["just a moment", "cloudflare", "checking your browser", "cf-"]
        antibot_signs = ["access denied", "forbidden", "403", "blocked", "suspicious"]
        captcha_signs = ["captcha", "verify you are human", "i'm not a robot"]
        lazy_signs = ["loading", "show more", "load more", "infinite"]
        rate_limit_signs = ["429", "too many requests", "rate limit"]

        for sign in cloudflare_signs:
            if sign in content:
                challenges["cloudflare"] = True
        for sign in antibot_signs:
            if sign in content:
                challenges["antibot"] = True
        for sign in captcha_signs:
            if sign in content:
                challenges["captcha"] = True
        for sign in lazy_signs:
            if sign in content:
                challenges["lazy_load"] = True
        for sign in rate_limit_signs:
            if sign in content:
                challenges["rate_limit"] = True

        return challenges

    def select_technique(
        self,
        domain: str,
        challenges: Dict[str, bool],
        context: Dict = None
    ) -> str:
        """
        Select the best technique based on:
        1. Website history
        2. Current challenges
        3. Technique performance
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # 1. Check if we have a best method for this domain
        c.execute("SELECT best_method, best_success_rate FROM website_stats WHERE domain = ?", (domain,))
        row = c.fetchone()
        if row and row[0] and row[1] > 0.7:
            conn.close()
            logger.info(f"Using known best method for {domain}: {row[0]}")
            return row[0]

        # 2. Score techniques based on challenges
        scores = {}
        for method, meta in self.TECHNIQUES.items():
            score = 0
            method_challenges = set(meta["challenges"])
            detected = set(k for k, v in challenges.items() if v)

            # Match technique to challenges
            overlap = method_challenges & detected
            score += len(overlap) * 10

            # Check historical success
            c.execute(
                "SELECT success_count, fail_count FROM technique_stats WHERE method = ?",
                (method,)
            )
            stats = c.fetchone()
            if stats:
                total = stats[0] + stats[1]
                if total > 0:
                    rate = stats[0] / total
                    score += rate * 5

            scores[method] = score

        conn.close()

        # 3. Return highest scoring technique
        if scores:
            best = max(scores, key=scores.get)
            if scores[best] > 0:
                logger.info(f"Selected technique for {domain}: {best} (score: {scores[best]})")
                return best

        # 4. Default fallback
        return "stealth_chrome"

    def record_attempt(
        self,
        domain: str,
        method: str,
        success: bool,
        items: int = 0,
        time_taken: float = 0.0,
        challenges: Dict = None
    ):
        """Record a scraping attempt for learning."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # Update technique stats
        c.execute("""
            INSERT INTO technique_website (domain, method, success, items_extracted, time_taken, challenges, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            domain,
            method,
            1 if success else 0,
            items,
            time_taken,
            json.dumps(challenges or {}),
            datetime.now().isoformat()
        ))

        # Update technique global stats
        if success:
            c.execute("""
                UPDATE technique_stats SET success_count = success_count + 1 WHERE method = ?
            """, (method,))
        else:
            c.execute("""
                UPDATE technique_stats SET fail_count = fail_count + 1 WHERE method = ?
            """, (method,))

        # Update website stats
        if success and items > 0:
            c.execute("""
                UPDATE website_stats
                SET best_method = ?, best_success_rate = MAX(best_success_rate, ?),
                    test_count = test_count + 1, last_tested = ?
                WHERE domain = ?
            """, (method, items / 100, datetime.now().isoformat(), domain))

        conn.commit()
        conn.close()

    def update_challenges(self, domain: str, challenges: Dict[str, bool]):
        """Update website challenge profile."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        for challenge, detected in challenges.items():
            if detected:
                if challenge == "cloudflare":
                    c.execute("UPDATE website_stats SET has_cloudflare = 1 WHERE domain = ?", (domain,))
                elif challenge == "antibot":
                    c.execute("UPDATE website_stats SET has_antibot = 1 WHERE domain = ?", (domain,))
                elif challenge == "captcha":
                    c.execute("UPDATE website_stats SET has_captcha = 1 WHERE domain = ?", (domain,))
                elif challenge == "lazy_load":
                    c.execute("UPDATE website_stats SET uses_lazy_load = 1 WHERE domain = ?", (domain,))

        conn.commit()
        conn.close()

    def get_suggestions(self, domain: str) -> List[str]:
        """Get suggestions for a website."""
        suggestions = []
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute("SELECT * FROM website_stats WHERE domain = ?", (domain,))
        row = c.fetchone()
        if row:
            if row[2]:  # has_cloudflare
                suggestions.append("Use stealth browser mode")
            if row[3]:  # has_antibot
                suggestions.append("Try proxy rotation")
            if row[5]:  # uses_lazy_load
                suggestions.append("Use scroll pattern")
            if row[4] or row[5]:  # has_captcha or uses_lazy_load
                suggestions.append("Increase wait times")

        conn.close()
        return suggestions


# ============== PROXY POOL MANAGER ==============

class ProxyPool:
    """
    Manages a pool of proxies with automatic rotation and health checking.
    """

    def __init__(self, proxies_file: str = "data/proxies.txt"):
        self.proxies_file = proxies_file
        self.proxies: List[Proxy] = []
        self.current_index = 0
        self.failed_proxies: Dict[str, int] = {}  # proxy -> fail count
        self.max_fails = 3
        self._load_proxies()

    def _load_proxies(self):
        """Load proxies from file."""
        path = Path(self.proxies_file)
        if path.exists():
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        proxy = Proxy(url=line)
                        self.proxies.append(proxy)
            logger.info(f"Loaded {len(self.proxies)} proxies")

    def add_proxy(self, url: str, proxy_type: str = "http", country: str = ""):
        """Add a proxy to the pool."""
        proxy = Proxy(url=url, proxy_type=proxy_type, country=country)
        self.proxies.append(proxy)
        self._save()

    def get_proxy(self) -> Optional[str]:
        """Get next working proxy."""
        attempts = 0
        start_index = self.current_index

        while attempts < len(self.proxies):
            proxy = self.proxies[self.current_index]
            self.current_index = (self.current_index + 1) % len(self.proxies)
            attempts += 1

            # Skip if marked as failed
            if self.failed_proxies.get(proxy.url, 0) >= self.max_fails:
                continue

            # Check if proxy is healthy
            if proxy.working:
                proxy.last_used = datetime.now().isoformat()
                return proxy.url

        return None

    def mark_success(self, proxy_url: str):
        """Mark proxy as successful."""
        for proxy in self.proxies:
            if proxy.url == proxy_url:
                proxy.success_count += 1
                proxy.working = True
                self.failed_proxies[proxy_url] = 0
                break
        self._save()

    def mark_failure(self, proxy_url: str):
        """Mark proxy as failed."""
        for proxy in self.proxies:
            if proxy.url == proxy_url:
                proxy.fail_count += 1
                self.failed_proxies[proxy_url] = self.failed_proxies.get(proxy_url, 0) + 1

                if self.failed_proxies[proxy_url] >= self.max_fails:
                    proxy.working = False
                    logger.warning(f"Proxy marked as failed: {proxy_url}")

                break
        self._save()

    def check_proxy(self, proxy_url: str) -> bool:
        """Check if a proxy is working."""
        import requests

        try:
            response = requests.get(
                "https://httpbin.org/ip",
                proxies={"http": proxy_url, "https": proxy_url},
                timeout=10
            )
            if response.status_code == 200:
                self.mark_success(proxy_url)
                return True
        except:
            pass

        self.mark_failure(proxy_url)
        return False

    def check_all(self):
        """Health check all proxies."""
        for proxy in self.proxies:
            proxy.last_checked = datetime.now().isoformat()
            proxy.working = self.check_proxy(proxy.url)
        self._save()

    def _save(self):
        """Save proxies to file."""
        Path(self.proxies_file).parent.mkdir(parents=True, exist_ok=True)
        with open(self.proxies_file, "w") as f:
            for proxy in self.proxies:
                if proxy.url:
                    f.write(f"{proxy.url}\n")

    def get_stats(self) -> Dict:
        """Get pool statistics."""
        total = len(self.proxies)
        working = sum(1 for p in self.proxies if p.working)
        return {
            "total": total,
            "working": working,
            "failed": total - working,
            "rotation_index": self.current_index,
        }


# ============== BROWSER POOL ==============

class BrowserPool:
    """
    Pool of browser instances for parallel scraping.
    """

    def __init__(
        self,
        pool_size: int = 5,
        headless: bool = True
    ):
        self.pool_size = pool_size
        self.headless = headless
        self.browsers: List = []
        self.available: List = []
        self.in_use: Dict = {}
        self._initialized = False

    def _init_pool(self):
        """Initialize browser pool."""
        try:
            from playwright.sync_api import sync_playwright

            self.playwright = sync_playwright().start()

            for i in range(self.pool_size):
                browser = self.playwright.chromium.launch(headless=self.headless)
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                )
                page = context.new_page()

                self.browsers.append({
                    "browser": browser,
                    "context": context,
                    "page": page,
                    "in_use": False
                })
                self.available.append(i)

            self._initialized = True
            logger.info(f"Browser pool initialized with {self.pool_size} browsers")

        except ImportError:
            logger.warning("Playwright not installed. Browser pool unavailable.")

    def acquire(self) -> Optional[Dict]:
        """Acquire a browser from pool."""
        if not self._initialized:
            self._init_pool()

        if not self.available:
            return None

        index = self.available.pop(0)
        browser = self.browsers[index]
        browser["in_use"] = True
        self.in_use[index] = browser

        return browser

    def release(self, browser: Dict):
        """Release a browser back to pool."""
        for i, b in enumerate(self.browsers):
            if b is browser:
                b["in_use"] = False
                if i not in self.available:
                    self.available.append(i)
                if i in self.in_use:
                    del self.in_use[i]
                break

    def close_all(self):
        """Close all browsers."""
        for browser in self.browsers:
            try:
                browser["page"].close()
                browser["context"].close()
                browser["browser"].close()
            except:
                pass

        if hasattr(self, "playwright"):
            self.playwright.stop()

        self._initialized = False
        logger.info("Browser pool closed")

    def get_stats(self) -> Dict:
        """Get pool statistics."""
        return {
            "total": self.pool_size,
            "available": len(self.available),
            "in_use": len(self.in_use),
        }


# ============== ADAPTIVE RATE LIMITER ==============

class AdaptiveRateLimiter:
    """
    Rate limiter that adapts based on website responses.
    """

    def __init__(self):
        self.delays: Dict[str, float] = {}  # domain -> delay
        self.default_delay = 2.0
        self.min_delay = 0.5
        self.max_delay = 60.0
        self.backoff_factor = 2.0
        self.recovery_factor = 0.9
        self.last_request: Dict[str, float] = {}

    def get_delay(self, domain: str) -> float:
        """Get current delay for domain."""
        return self.delays.get(domain, self.default_delay)

    def record_success(self, domain: str):
        """Record successful request - reduce delay."""
        current = self.delays.get(domain, self.default_delay)
        new_delay = max(self.min_delay, current * self.recovery_factor)
        self.delays[domain] = new_delay
        logger.debug(f"{domain}: delay reduced to {new_delay:.1f}s")

    def record_rate_limit(self, domain: str, retry_after: int = None):
        """Record rate limit - increase delay."""
        if retry_after:
            new_delay = retry_after * 1.5
        else:
            current = self.delays.get(domain, self.default_delay)
            new_delay = min(self.max_delay, current * self.backoff_factor)

        self.delays[domain] = new_delay
        logger.warning(f"{domain}: delay increased to {new_delay:.1f}s due to rate limit")

    def record_error(self, domain: str):
        """Record error - moderate increase."""
        current = self.delays.get(domain, self.default_delay)
        new_delay = min(self.max_delay, current * 1.5)
        self.delays[domain] = new_delay

    def wait_if_needed(self, domain: str):
        """Wait if needed before next request."""
        import time

        delay = self.get_delay(domain)
        last = self.last_request.get(domain, 0)
        elapsed = time.time() - last

        if elapsed < delay:
            wait_time = delay - elapsed
            logger.debug(f"{domain}: waiting {wait_time:.1f}s")
            time.sleep(wait_time)

        self.last_request[domain] = time.time()

    def get_stats(self) -> Dict:
        """Get limiter statistics."""
        return {
            domain: {
                "delay": delay,
                "last_request": self.last_request.get(domain)
            }
            for domain, delay in self.delays.items()
        }


# ============== ULTIMATE SCRAPER ==============

class UltimateScraper:
    """
    Ultimate self-evolving scraper with automatic technique selection,
    proxy pool, browser pool, and adaptive rate limiting.
    """

    def __init__(
        self,
        db_path: str = "data/scraper_profiles.db",
        proxies_file: str = "data/proxies.txt",
        browser_pool_size: int = 3
    ):
        self.selector = AutomaticTechniqueSelector(db_path)
        self.proxy_pool = ProxyPool(proxies_file)
        self.browser_pool = BrowserPool(pool_size=browser_pool_size)
        self.rate_limiter = AdaptiveRateLimiter()
        self.session = None

    def scrape(
        self,
        url: str,
        max_retries: int = 3,
        use_browser: bool = False,
        use_proxy: bool = False,
        custom_technique: str = None,
        extract_func: Callable = None
    ) -> Dict[str, Any]:
        """
        Scrape a URL with automatic technique selection.

        Returns:
            {
                "success": bool,
                "data": Any,
                "technique": str,
                "challenges": Dict,
                "items_extracted": int
            }
        """
        domain = urlparse(url).netloc
        start_time = time.time()

        # Detect challenges
        challenges = self.selector.detect_challenges("", "")
        logger.info(f"Scraping {domain} with challenges: {challenges}")

        # Select technique
        technique = custom_technique or self.selector.select_technique(domain, challenges)

        # Apply rate limiting
        self.rate_limiter.wait_if_needed(domain)

        # Get proxy if needed
        proxy = None
        if use_proxy:
            proxy = self.proxy_pool.get_proxy()
            if proxy:
                logger.info(f"Using proxy: {proxy}")

        # Attempt scraping
        result = {
            "success": False,
            "data": None,
            "technique": technique,
            "challenges": challenges,
            "items_extracted": 0,
            "error": None
        }

        for attempt in range(max_retries):
            try:
                if technique.startswith("stealth"):
                    data = self._scrape_stealth(url, proxy)
                elif technique == "api_intercept":
                    data = self._scrape_api(url)
                else:
                    data = self._scrape_basic(url)

                # Extract data if function provided
                if extract_func and data:
                    data = extract_func(data)

                # Check for challenges in response
                html = data.get("html", "")
                title = data.get("title", "")
                status = data.get("status", 200)

                detected_challenges = self.selector.detect_challenges(html, title, status)

                # Record attempt
                items = len(data.get("links", []))
                elapsed = time.time() - start_time

                self.selector.record_attempt(
                    domain, technique,
                    success=bool(data.get("html")),
                    items=items,
                    time_taken=elapsed,
                    challenges=detected_challenges
                )

                if detected_challenges.get("cloudflare") or detected_challenges.get("antibot"):
                    # Technique failed, try next
                    technique = self.selector.select_technique(domain, detected_challenges)
                    result["technique"] = technique
                    continue

                result["success"] = True
                result["data"] = data
                result["items_extracted"] = items
                result["challenges"] = detected_challenges

                # Update adaptive systems
                self.rate_limiter.record_success(domain)
                if proxy:
                    self.proxy_pool.mark_success(proxy)

                break

            except Exception as e:
                logger.error(f"Attempt {attempt + 1} failed: {e}")
                result["error"] = str(e)

                self.rate_limiter.record_error(domain)
                if proxy:
                    self.proxy_pool.mark_failure(proxy)

                # Select new technique
                technique = self.selector.select_technique(domain, challenges)
                result["technique"] = technique

        # Update challenges
        self.selector.update_challenges(domain, result["challenges"])

        return result

    def _scrape_stealth(self, url: str, proxy: str = None) -> Dict:
        """Scrape using stealth browser."""
        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    args=['--disable-blink-features=AutomationControlled']
                )

                context_options = {
                    "viewport": {"width": 1920, "height": 1080},
                }

                if proxy:
                    context_options["proxy"] = {"server": proxy}

                context = browser.new_context(**context_options)
                page = context.new_page()

                # Stealth script
                page.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                    Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
                """)

                page.goto(url, timeout=60000, wait_until="domcontentloaded")
                page.wait_for_timeout(5000)

                # Scroll for lazy load
                for _ in range(10):
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    page.wait_for_timeout(1000)

                # Extract links
                links = []
                for a in page.query_selector_all("a"):
                    href = a.get_attribute("href") or ""
                    text = a.inner_text().strip()
                    if href:
                        links.append({"url": href, "text": text})

                result = {
                    "html": page.content(),
                    "title": page.title(),
                    "links": links,
                    "status": 200
                }

                browser.close()
                return result

        except Exception as e:
            return {"html": "", "title": "", "links": [], "status": 0, "error": str(e)}

    def _scrape_basic(self, url: str) -> Dict:
        """Basic requests-based scraping."""
        import requests

        response = requests.get(url, timeout=30)

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.text, "lxml")

        links = []
        for a in soup.find_all("a", href=True):
            links.append({
                "url": a["href"],
                "text": a.get_text(strip=True)
            })

        return {
            "html": response.text,
            "title": soup.title.string if soup.title else "",
            "links": links,
            "status": response.status_code
        }

    def _scrape_api(self, url: str) -> Dict:
        """Scrape using API interception pattern."""
        return self._scrape_basic(url)

    def get_stats(self) -> Dict:
        """Get all scraper statistics."""
        return {
            "technique_selector": {
                "proxy_pool": self.proxy_pool.get_stats(),
                "browser_pool": self.browser_pool.get_stats(),
                "rate_limiter": self.rate_limiter.get_stats(),
            }
        }

    def close(self):
        """Clean up resources."""
        self.browser_pool.close_all()


# ============== FACTORY ==============

def create_ultimate_scraper(**kwargs) -> UltimateScraper:
    """Create configured ultimate scraper."""
    return UltimateScraper(**kwargs)
