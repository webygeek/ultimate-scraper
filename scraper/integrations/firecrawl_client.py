"""
Firecrawl Integration - Cloudflare bypass and intelligent web scraping.
Supports: Local Docker, Cloud API, or Self-hosted instances.

Quick Start:
    1. Start Firecrawl: cd c:/tmp/firecrawl && docker compose up -d
    2. Use: from scraper.integrations.firecrawl_client import FirecrawlClient

Usage:
    client = FirecrawlClient()
    result = client.scrape("https://example.com")

Or with config:
    client = FirecrawlClient({"firecrawl": {"base_url": "http://localhost:3002"}})
"""
import requests
import time
from typing import Optional, Dict, List
from loguru import logger


class FirecrawlClient:
    """
    Firecrawl client for scraping Cloudflare-protected sites.

    Supports three modes:
    1. Local Docker: http://localhost:3002 (no API key needed)
    2. Self-hosted: Your own Firecrawl instance
    3. Cloud API: firecrawl.dev (API key required)

    Features:
    - Cloudflare/antibot bypass
    - JavaScript rendering
    - Markdown extraction
    - Batch scraping
    - Crawling with depth control
    """

    def __init__(self, config: Dict = None):
        cfg = config.get("firecrawl", {}) if config else {}

        self.base_url = cfg.get("base_url", "http://localhost:3002").rstrip("/")
        self.api_key = cfg.get("api_key", "")
        self.timeout = cfg.get("timeout", 120)
        self.max_retries = cfg.get("max_retries", 3)
        self.wait_time = cfg.get("wait_between_requests", 1.0)

        self.session = requests.Session()
        if self.api_key:
            self.session.headers.update({"Authorization": f"Bearer {self.api_key}"})

    def is_available(self) -> bool:
        """Check if Firecrawl is running and accessible."""
        try:
            resp = self.session.get(self.base_url, timeout=5)
            return resp.status_code == 200
        except:
            return False

    def is_healthy(self) -> bool:
        """Alias for is_available()."""
        return self.is_available()

    def scrape(
        self,
        url: str,
        formats: List[str] = None,
        only_main_content: bool = True,
        timeout: int = None,
    ) -> Optional[Dict]:
        """
        Scrape a single URL.

        Args:
            url: URL to scrape
            formats: ['markdown', 'html', 'screenshot', 'links', 'rawHtml']
            only_main_content: Extract main content only (default: True)
            timeout: Request timeout in seconds

        Returns:
            Dict with 'success', 'markdown', 'html', 'metadata' keys
            or None on failure
        """
        if formats is None:
            formats = ["markdown", "html"]

        payload = {
            "url": url,
            "formats": formats,
            "onlyMainContent": only_main_content,
        }

        timeout = timeout or self.timeout

        for attempt in range(self.max_retries):
            try:
                logger.debug(f"Firecrawl: Scraping {url} (attempt {attempt + 1})")

                response = self.session.post(
                    f"{self.base_url}/v1/scrape",
                    json=payload,
                    timeout=timeout,
                )

                if response.status_code == 200:
                    data = response.json()
                    if data.get("success"):
                        return {
                            "success": True,
                            "url": url,
                            "markdown": data.get("data", {}).get("markdown", ""),
                            "html": data.get("data", {}).get("html", ""),
                            "metadata": data.get("data", {}).get("metadata", {}),
                        }
                    else:
                        logger.warning(f"Firecrawl failed: {data.get('error')}")
                        if attempt == self.max_retries - 1:
                            return {"success": False, "error": data.get("error")}
                else:
                    logger.warning(f"Firecrawl HTTP {response.status_code}")

            except requests.exceptions.Timeout:
                logger.warning(f"Firecrawl timeout for {url}")
            except Exception as e:
                logger.warning(f"Firecrawl error: {e}")

            if attempt < self.max_retries - 1:
                time.sleep(self.wait_time * (attempt + 1))

        return {"success": False, "error": "All retries failed"}

    def scrape_markdown(self, url: str) -> Optional[str]:
        """Get just the markdown content."""
        result = self.scrape(url, formats=["markdown"])
        if result and result.get("success"):
            return result.get("markdown", "")
        return None

    def scrape_html(self, url: str) -> Optional[str]:
        """Get the HTML content."""
        result = self.scrape(url, formats=["html"])
        if result and result.get("success"):
            return result.get("html", "")
        return None

    def scrape_to_file(
        self,
        url: str,
        output_path: str,
        format: str = "markdown",
    ) -> bool:
        """
        Scrape URL and save to file.

        Args:
            url: URL to scrape
            output_path: Path to save file
            format: 'markdown' or 'html'

        Returns:
            True if successful, False otherwise
        """
        content = self.scrape_markdown(url) if format == "markdown" else self.scrape_html(url)

        if content:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(content)
            logger.info(f"Saved {len(content)} chars to {output_path}")
            return True

        return False

    def crawl(
        self,
        url: str,
        max_depth: int = 1,
        max_pages: int = 10,
        allow_external: bool = False,
        poll_interval: int = 5,
        timeout: int = 300,
    ) -> Optional[List[Dict]]:
        """
        Crawl a URL and extract multiple pages.

        Args:
            url: Starting URL
            max_depth: How deep to crawl
            max_pages: Maximum pages to crawl
            allow_external: Follow external links
            poll_interval: Seconds between status checks
            timeout: Total timeout in seconds

        Returns:
            List of page data or None on failure
        """
        payload = {
            "url": url,
            "maxDepth": max_depth,
            "limit": max_pages,
            "allowExternal": allow_external,
        }

        try:
            logger.info(f"Firecrawl: Starting crawl of {url}")

            response = self.session.post(
                f"{self.base_url}/v1/crawl",
                json=payload,
                timeout=30,
            )

            if response.status_code != 200:
                logger.error(f"Crawl start failed: {response.status_code}")
                return None

            data = response.json()
            job_id = data.get("jobId")
            if not job_id:
                logger.error("No job ID returned")
                return None

            logger.info(f"Crawl job started: {job_id}")

            # Poll for completion
            start_time = time.time()
            while time.time() - start_time < timeout:
                status_response = self.session.get(
                    f"{self.base_url}/v1/crawl/status/{job_id}",
                    timeout=30,
                )

                if status_response.status_code == 200:
                    status_data = status_response.json()
                    status = status_data.get("status")

                    logger.debug(f"Crawl status: {status}")

                    if status == "completed":
                        pages = status_data.get("data", [])
                        logger.info(f"Crawl completed: {len(pages)} pages")
                        return pages
                    elif status == "failed":
                        logger.error(f"Crawl failed: {status_data.get('error')}")
                        return None

                time.sleep(poll_interval)

            logger.error("Crawl timeout")
            return None

        except Exception as e:
            logger.error(f"Crawl error: {e}")
            return None

    def batch_scrape(
        self,
        urls: List[str],
        formats: List[str] = None,
        timeout: int = 120,
    ) -> Optional[List[Dict]]:
        """
        Batch scrape multiple URLs.

        Args:
            urls: List of URLs to scrape
            formats: Content formats to extract
            timeout: Timeout per URL

        Returns:
            List of scraped results
        """
        if formats is None:
            formats = ["markdown"]

        payload = {
            "urls": urls,
            "formats": formats,
        }

        try:
            logger.info(f"Firecrawl: Batch scraping {len(urls)} URLs")

            response = self.session.post(
                f"{self.base_url}/v1/batch-scrape",
                json=payload,
                timeout=timeout * len(urls),
            )

            if response.status_code == 200:
                data = response.json()
                return data.get("data", [])
            else:
                logger.error(f"Batch scrape failed: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Batch scrape error: {e}")
            return None

    def map(self, url: str, search: str = None) -> Optional[List[str]]:
        """
        Discover URLs on a domain (sitemap alternative).

        Args:
            url: Domain to map
            search: Optional search term to filter results

        Returns:
            List of discovered URLs
        """
        payload = {"url": url}
        if search:
            payload["search"] = search

        try:
            logger.info(f"Firecrawl: Mapping {url}")

            response = self.session.post(
                f"{self.base_url}/v1/map",
                json=payload,
                timeout=60,
            )

            if response.status_code == 200:
                data = response.json()
                return data.get("links", [])
            else:
                logger.error(f"Map failed: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Map error: {e}")
            return None


def create_firecrawl_client(config: Dict = None) -> FirecrawlClient:
    """Factory function to create a configured Firecrawl client."""
    return FirecrawlClient(config)


# Convenience function for quick scraping
def scrape(url: str, base_url: str = "http://localhost:3002") -> Optional[Dict]:
    """
    Quick scrape a URL using Firecrawl.

    Args:
        url: URL to scrape
        base_url: Firecrawl instance URL

    Returns:
        Dict with scraped content or None
    """
    client = FirecrawlClient({"firecrawl": {"base_url": base_url}})
    return client.scrape(url)


if __name__ == "__main__":
    client = FirecrawlClient()

    print("Checking Firecrawl...")
    if not client.is_available():
        print("ERROR: Firecrawl is not running!")
        print()
        print("Start local Firecrawl:")
        print("  cd c:/tmp/firecrawl && docker compose up -d")
        print()
        print("Or use cloud API:")
        print("  client = FirecrawlClient({'firecrawl': {'api_key': 'fc-xxx'}})")
    else:
        print("Firecrawl is available!")

        # Test scrape
        result = client.scrape("https://example.com")
        if result and result.get("success"):
            print(f"Scrape test successful ({len(result.get('markdown', ''))} chars)")
        else:
            print("Scrape test failed")
