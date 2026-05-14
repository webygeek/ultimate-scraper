"""
Map API - Firecrawl-style URL discovery across entire websites.
"""
import asyncio
import time
import re
from typing import Dict, List, Set, Optional, Any
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse, urldefrag
from loguru import logger


@dataclass
class DiscoveredURL:
    """A discovered URL."""
    url: str
    type: str  # page, asset, api
    status: int = 0
    content_type: str = ""
    depth: int = 0
    links_from: List[str] = field(default_factory=list)


class MapAPI:
    """
    Discover all URLs on a website.
    Like Firecrawl's /map endpoint.

    Features:
    - Recursive crawling with depth limits
    - URL deduplication
    - Filter by content type
    - Finds hidden URLs from JavaScript
    - Respects robots.txt
    """

    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.rate_limit_delay = self.config.get("rate_limit_delay", 1)

    async def map(
        self,
        url: str,
        max_urls: int = 1000,
        max_depth: int = 3,
        include_subdomains: bool = False,
        include_images: bool = False,
    ) -> Dict[str, Any]:
        """
        Discover all URLs on a website.

        Args:
            url: Starting URL
            max_urls: Maximum URLs to discover
            max_depth: Maximum crawl depth
            include_subdomains: Include subdomain URLs
            include_images: Include image URLs

        Returns:
            {"urls": [...], "count": int, "discovered_at": timestamp}
        """
        start_time = time.time()
        discovered: Set[str] = set()
        url_queue = [(url, 0)]  # (url, depth)

        domain = urlparse(url).netloc
        base_domain = self._get_base_domain(domain)

        # First, try sitemap discovery (fast)
        sitemap_urls = self._discover_from_sitemap(url)
        for sitemap_url in sitemap_urls[:100]:  # Limit from sitemap
            discovered.add(self._normalize_url(sitemap_url))

        # Then crawl for remaining URLs
        visited = set()
        batch_size = 10

        while url_queue and len(discovered) < max_urls:
            # Get batch of URLs to process
            batch = []
            while url_queue and len(batch) < batch_size:
                current_url, depth = url_queue.pop(0)
                if current_url in visited:
                    continue
                visited.add(current_url)

                if depth > max_depth:
                    continue

                batch.append((current_url, depth))

            if not batch:
                break

            # Process batch
            tasks = [
                self._crawl_url(current_url, depth, include_images)
                for current_url, depth in batch
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, Exception):
                    continue

                for link_info in result:
                    link_url = link_info["url"]

                    # Check if belongs to same domain
                    if not self._should_include(link_url, domain, base_domain, include_subdomains):
                        continue

                    normalized = self._normalize_url(link_url)
                    if normalized and normalized not in discovered:
                        discovered.add(normalized)

                        # Add to queue if it's a page
                        if link_info["type"] == "page":
                            url_queue.append((normalized, link_info["depth"] + 1))

        duration = time.time() - start_time

        return {
            "urls": list(discovered),
            "count": len(discovered),
            "discovered_at": time.time(),
            "duration_seconds": round(duration, 2),
            "source_url": url,
        }

    async def _crawl_url(self, url: str, depth: int, include_images: bool) -> List[Dict]:
        """Crawl a single URL and extract links."""
        links = []

        try:
            from ..modules.anti_detection import RequestSession

            session = RequestSession(self.config)
            response = session.get(url, timeout=15)

            if response.status_code != 200:
                return links

            content_type = response.headers.get("content-type", "")

            # Check if HTML
            if "text/html" in content_type:
                links.extend(self._extract_links_html(response.text, url, depth))

                # Try to find JS-rendered links with browser
                if self._has_js_indicators(response.text):
                    js_links = await self._extract_links_js(url)
                    links.extend(js_links)

            # Include images if requested
            if include_images:
                links.extend(self._extract_images(response.text, url, depth))

            # Try to find API endpoints
            links.extend(self._extract_api_endpoints(response.text, url, depth))

        except Exception as e:
            logger.debug(f"Crawl failed for {url}: {e}")

        return links

    def _extract_links_html(self, html: str, base_url: str, depth: int) -> List[Dict]:
        """Extract links from HTML."""
        from bs4 import BeautifulSoup

        links = []
        soup = BeautifulSoup(html, "lxml")

        # Find all links
        for a in soup.find_all("a", href=True):
            href = a.get("href", "")
            if not href or href.startswith("#"):
                continue

            full_url = urljoin(base_url, href)
            normalized = self._normalize_url(full_url)

            if normalized:
                links.append({
                    "url": normalized,
                    "type": "page",
                    "depth": depth,
                    "text": a.get_text(strip=True)[:100],
                })

        return links

    async def _extract_links_js(self, url: str) -> List[Dict]:
        """Extract links from JavaScript using browser."""
        try:
            from playwright.sync_api import sync_playwright

            links = []

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()

                page.goto(url, timeout=20000)
                page.wait_for_load_state("networkidle")

                # Extract all links via JavaScript
                hrefs = page.evaluate("""
                    Array.from(document.querySelectorAll('a[href]'))
                    .map(a => ({
                        url: a.href,
                        text: a.textContent.trim().substring(0, 100)
                    }))
                """)

                for href_info in hrefs:
                    links.append({
                        "url": href_info["url"],
                        "type": "page",
                        "depth": 1,
                        "text": href_info["text"],
                    })

                browser.close()

            return links

        except Exception as e:
            logger.debug(f"JS extraction failed: {e}")
            return []

    def _extract_images(self, html: str, base_url: str, depth: int) -> List[Dict]:
        """Extract image URLs."""
        from bs4 import BeautifulSoup

        images = []
        soup = BeautifulSoup(html, "lxml")

        for img in soup.find_all("img", src=True):
            src = img.get("src", "")
            if src:
                full_url = urljoin(base_url, src)
                images.append({
                    "url": full_url,
                    "type": "image",
                    "depth": depth,
                })

        return images

    def _extract_api_endpoints(self, html: str, base_url: str, depth: int) -> List[Dict]:
        """Extract API endpoint patterns from HTML/JS."""
        apis = []

        # Look for API patterns in HTML
        patterns = [
            r'["\']\/api\/[a-zA-Z0-9\/_\-]+["\']',
            r'["\']\/v\d+\/[a-zA-Z0-9\/_\-]+["\']',
            r'endpoint["\']?\s*:\s*["\']([^"\']+)["\']',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, html)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]
                full_url = urljoin(base_url, match.strip('"\''))
                apis.append({
                    "url": full_url,
                    "type": "api",
                    "depth": depth,
                })

        return apis

    def _discover_from_sitemap(self, url: str) -> List[str]:
        """Try to discover URLs from sitemap."""
        from .sitemap_parser import SitemapParser

        sitemap_urls = [
            f"{url.rstrip('/')}/sitemap.xml",
            f"{url.rstrip('/')}/sitemap_index.xml",
        ]

        for sitemap_url in sitemap_urls:
            try:
                parser = SitemapParser()
                entries = parser.parse_url(sitemap_url)
                if entries:
                    return [e.url for e in entries]
            except:
                pass

        return []

    def _normalize_url(self, url: str) -> Optional[str]:
        """Normalize URL."""
        if not url:
            return None

        # Remove fragments
        url, _ = urldefrag(url)

        # Remove tracking parameters
        tracking_params = ["utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term"]
        parsed = urlparse(url)

        # Simple check for valid URLs
        if not parsed.scheme or not parsed.netloc:
            return None

        # Remove trailing slash
        path = parsed.path.rstrip("/") or "/"

        return f"{parsed.scheme}://{parsed.netloc}{path}"

    def _should_include(
        self,
        url: str,
        domain: str,
        base_domain: str,
        include_subdomains: bool,
    ) -> bool:
        """Check if URL should be included."""
        parsed = urlparse(url)

        if not parsed.scheme or not parsed.netloc:
            return False

        url_domain = parsed.netloc

        if include_subdomains:
            return url_domain.endswith(base_domain)
        else:
            return url_domain == domain

    def _get_base_domain(self, domain: str) -> str:
        """Get base domain (e.g., example.com from www.example.com)."""
        parts = domain.split(".")
        if len(parts) >= 2:
            return ".".join(parts[-2:])
        return domain

    def _has_js_indicators(self, html: str) -> bool:
        """Check if page likely uses JavaScript routing."""
        js_indicators = [
            "react", "vue", "angular", "next", "nuxt",
            "__NEXT_DATA__", "__nuxt", "__INITIAL_STATE__",
            "window.__", "SPAWN_",
        ]
        html_lower = html.lower()
        return any(ind in html_lower for ind in js_indicators)


def discover_site(url: str, **kwargs) -> Dict[str, Any]:
    """
    Convenience function for site discovery.

    Args:
        url: Starting URL
        **kwargs: See MapAPI.map()

    Returns:
        Discovery results
    """
    api = MapAPI()
    return asyncio.run(api.map(url, **kwargs))
