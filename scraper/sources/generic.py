"""
Generic web scraper for any website.
Handles various page types, pagination, and structured data extraction.
"""
import re
import time
import json
import random
from datetime import datetime
from typing import Optional, Callable
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from loguru import logger

from ..modules.browser import BrowserManager
from ..modules.anti_detection import RequestSession


class GenericScraper:
    """
    Universal web scraper that can handle most websites.
    Supports CSS selectors, XPath, pagination, and structured data extraction.
    """

    def __init__(self, config: dict):
        self.config = config
        self.browser = BrowserManager(config)
        self.session = RequestSession(config)
        self._visited_urls = set()

    def scrape(
        self,
        url: str,
        selectors: dict = None,
        pagination: dict = None,
        use_browser: bool = False,
        metadata: dict = None,
    ) -> list[dict]:
        """
        Scrape a URL with specified selectors.

        Args:
            url: Target URL
            selectors: Dict mapping field names to CSS selectors
            pagination: Pagination config (see _parse_pagination_config)
            use_browser: Force browser automation
            metadata: Additional metadata to include in results

        Returns:
            List of scraped records
        """
        results = []

        # Determine scraping method
        if use_browser or self._should_use_browser(url):
            results = self._scrape_with_browser(url, selectors, pagination, metadata)
        else:
            results = self._scrape_with_requests(url, selectors, pagination, metadata)

        return results

    def _should_use_browser(self, url: str) -> bool:
        """Decide if browser automation is needed."""
        js_indicators = [
            "react", "vue", "angular", "nextjs", "gatsby",
            "cloudflare", "shopify", "wix", "squarespace",
        ]

        url_lower = url.lower()
        return any(indicator in url_lower for indicator in js_indicators)

    def _scrape_with_browser(
        self,
        url: str,
        selectors: dict,
        pagination: dict,
        metadata: dict,
    ) -> list[dict]:
        """Scrape using Playwright."""
        if not self.browser.start():
            logger.error("Failed to start browser")
            return []

        results = []

        try:
            page_num = 0
            max_pages = pagination.get("max_pages", 10) if pagination else 1

            while page_num < max_pages:
                current_url = self._get_page_url(url, page_num, pagination)

                if current_url in self._visited_urls and page_num > 0:
                    break

                self._visited_urls.add(current_url)

                html = self.browser.navigate_and_wait(
                    current_url,
                    wait_selector=pagination.get("wait_selector") if pagination else None,
                    wait_timeout=30000,
                )

                if not html:
                    break

                page_results = self._parse_html(html, selectors, metadata)
                results.extend(page_results)

                # Check if there's a next page
                if not self._has_next_page(pagination):
                    break

                page_num += 1
                time.sleep(random.uniform(2, 5))

        except Exception as e:
            logger.error(f"Browser scrape failed: {e}")
        finally:
            self.browser.close()

        return results

    def _scrape_with_requests(
        self,
        url: str,
        selectors: dict,
        pagination: dict,
        metadata: dict,
    ) -> list[dict]:
        """Scrape using requests."""
        results = []

        try:
            page_num = 0
            max_pages = pagination.get("max_pages", 10) if pagination else 1

            while page_num < max_pages:
                current_url = self._get_page_url(url, page_num, pagination)

                if current_url in self._visited_urls and page_num > 0:
                    break

                self._visited_urls.add(current_url)

                response = self.session.get(current_url)
                html = response.text

                page_results = self._parse_html(html, selectors, metadata)
                results.extend(page_results)

                # Check if there's a next page
                if not self._has_next_page(pagination):
                    break

                page_num += 1
                time.sleep(random.uniform(1, 3))

        except Exception as e:
            logger.error(f"Request scrape failed: {e}")

        return results

    def _parse_html(self, html: str, selectors: dict, metadata: dict) -> list[dict]:
        """Parse HTML and extract data using selectors."""
        soup = BeautifulSoup(html, "lxml")
        results = []

        if selectors is None:
            # Try to auto-detect common patterns
            selectors = self._auto_detect_selectors(soup)

        # Try to find list containers
        containers = self._find_containers(soup, selectors)

        if containers:
            for container in containers:
                result = self._extract_fields(container, selectors, metadata)
                if result:
                    results.append(result)
        else:
            # Single page scraping
            result = self._extract_fields(soup, selectors, metadata)
            if result:
                results.append(result)

        return results

    def _auto_detect_selectors(self, soup) -> dict:
        """Auto-detect common data patterns."""
        selectors = {}

        # Common listing containers
        container_patterns = [
            "[class*='item']", "[class*='card']", "[class*='product']",
            "[class*='listing']", "[class*='result']", "article",
            "[class*='row']", "[class*='post']",
        ]

        for pattern in container_patterns:
            containers = soup.select(pattern)
            if len(containers) > 1:
                # Determine what fields are in each container
                if containers[0].select_one("h1, h2, h3"):
                    selectors["title"] = f"{pattern} h1, {pattern} h2, {pattern} h3"
                if containers[0].select_one("a[href]"):
                    selectors["url"] = f"{pattern} a[href]"
                if containers[0].select_one("img"):
                    selectors["image"] = f"{pattern} img"
                if containers[0].select_one("[class*='price']"):
                    selectors["price"] = f"{pattern} [class*='price']"
                if containers[0].select_one("[class*='desc'], [class*='text']"):
                    selectors["description"] = f"{pattern} [class*='desc'], {pattern} [class*='text']"
                break

        return selectors

    def _find_containers(self, soup, selectors: dict) -> list:
        """Find container elements that hold individual items."""
        if not selectors:
            return []

        # Try common container patterns
        container_patterns = [
            "[class*='items']", "[class*='cards']", "[class*='list']",
            "[class*='grid']", "[class*='results']", "article",
            "[class*='product']", "[class*='listing']",
        ]

        for pattern in container_patterns:
            containers = soup.select(pattern)
            if len(containers) > 1:
                return containers

        # If no containers found, return all direct children of main content area
        main = soup.select_one("main, [role='main'], #content, .content, article")
        if main:
            return main.find_all(recursive=False)[:20]

        return []

    def _extract_fields(self, element, selectors: dict, metadata: dict) -> Optional[dict]:
        """Extract fields from an element using selectors."""
        result = {}

        for field_name, selector in selectors.items():
            elem = element.select_one(selector)
            if elem:
                if field_name == "url":
                    result[field_name] = self._extract_url(elem)
                elif field_name == "image":
                    result[field_name] = self._extract_image(elem)
                elif field_name == "price":
                    result[field_name] = self._extract_price(elem)
                elif field_name == "text":
                    result[field_name] = self._extract_text(elem)
                else:
                    result[field_name] = self._extract_text(elem)

        # Add URL if found in element
        if "url" not in result:
            link = element.select_one("a[href]")
            if link:
                result["url"] = self._extract_url(link)

        # Add metadata
        if metadata:
            result["_metadata"] = metadata

        # Add timestamp
        result["_scraped_at"] = datetime.now().isoformat()

        return result if result else None

    def _extract_url(self, element) -> str:
        """Extract URL from element."""
        if element.name == "a":
            href = element.get("href", "")
        else:
            href = element.get("href", "")

        if href.startswith("//"):
            href = "https:" + href
        elif href.startswith("/"):
            href = "https://" + urlparse("").netloc + href  # Would need base URL

        return href

    def _extract_image(self, element) -> str:
        """Extract image URL."""
        if element.name == "img":
            return element.get("src") or element.get("data-src", "")
        return element.get("src") or element.get("data-src", "")

    def _extract_price(self, element) -> Optional[float]:
        """Extract price value."""
        text = element.get_text(strip=True)
        match = re.search(r"[\d,]+\.?\d*", text.replace(",", ""))
        if match:
            return float(match.group().replace(",", ""))
        return None

    def _extract_text(self, element) -> str:
        """Extract clean text from element."""
        # Remove script and style tags
        for tag in element.find_all(["script", "style", "noscript"]):
            tag.decompose()

        text = element.get_text(separator=" ", strip=True)
        # Clean up whitespace
        text = re.sub(r"\s+", " ", text)
        return text

    def _get_page_url(self, base_url: str, page_num: int, pagination: dict) -> str:
        """Generate URL for specific page number."""
        if page_num == 0:
            return base_url

        if pagination is None:
            return base_url

        pagination_type = pagination.get("type", "param")

        if pagination_type == "param":
            param = pagination.get("param", "page")
            separator = "?" if "?" not in base_url else "&"
            return f"{base_url}{separator}{param}={page_num + 1}"

        elif pagination_type == "offset":
            param = pagination.get("param", "offset")
            limit = pagination.get("limit", 20)
            offset = page_num * limit
            separator = "?" if "?" not in base_url else "&"
            return f"{base_url}{separator}{param}={offset}"

        elif pagination_type == "next_button":
            # This requires browser automation
            return base_url

        return base_url

    def _has_next_page(self, pagination: dict) -> bool:
        """Check if pagination config indicates more pages available."""
        if pagination is None:
            return False

        max_pages = pagination.get("max_pages", 10)
        return pagination.get("_current_page", 0) < max_pages - 1

    def scrape_with_sitemap(self, sitemap_url: str, selectors: dict) -> list[dict]:
        """Scrape all URLs from a sitemap."""
        results = []

        try:
            response = self.session.get(sitemap_url)
            soup = BeautifulSoup(response.text, "lxml")

            urls = []
            for loc in soup.select("loc"):
                url = loc.get_text(strip=True)
                if url and not self._is_excluded(url):
                    urls.append(url)

            logger.info(f"Found {len(urls)} URLs in sitemap")

            for url in urls[:pagination.get("max_urls", 100)]:
                try:
                    page_results = self.scrape(url, selectors)
                    results.extend(page_results)
                    time.sleep(random.uniform(1, 3))
                except Exception as e:
                    logger.debug(f"Failed to scrape {url}: {e}")

        except Exception as e:
            logger.error(f"Sitemap scrape failed: {e}")

        return results

    def _is_excluded(self, url: str) -> bool:
        """Check if URL should be excluded."""
        excluded_patterns = [
            "/tag/", "/category/", "/author/", "/page/",
            ".xml", ".pdf", ".jpg", ".png",
        ]
        return any(pattern in url.lower() for pattern in excluded_patterns)

    def scrape_json_ld(
        self,
        url: str,
        schema_type: Optional[str] = None,
    ) -> list[dict]:
        """Scrape JSON-LD structured data from a page."""
        try:
            response = self.session.get(url)
            soup = BeautifulSoup(response.text, "lxml")

            results = []
            for script in soup.select("script[type='application/ld+json']"):
                try:
                    data = json.loads(script.string)
                    if isinstance(data, list):
                        results.extend(data)
                    else:
                        results.append(data)
                except (json.JSONDecodeError, TypeError):
                    continue

            # Filter by schema type if specified
            if schema_type:
                results = [
                    r for r in results
                    if r.get("@type") == schema_type
                    or (isinstance(r.get("@type"), list) and schema_type in r["@type"])
                ]

            return results

        except Exception as e:
            logger.error(f"JSON-LD scrape failed: {e}")
            return []

    def scrape_and_save(
        self,
        url: str,
        output_path: str,
        selectors: dict = None,
        pagination: dict = None,
        formats: list = None,
    ) -> bool:
        """Scrape and save to multiple formats."""
        from ..output import JSONFormatter, CSVFormatter, ExcelFormatter

        if formats is None:
            formats = ["json", "csv", "xlsx"]

        results = self.scrape(url, selectors, pagination)

        if not results:
            logger.warning("No results scraped")
            return False

        success = True
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        parsed = urlparse(url)
        safe_name = re.sub(r"[^\w\s-]", "", parsed.netloc)[:50]
        base_path = f"{output_path}/{safe_name}_{timestamp}"

        json_formatter = JSONFormatter(self.config)
        csv_formatter = CSVFormatter(self.config)
        excel_formatter = ExcelFormatter(self.config)

        if "json" in formats:
            if not json_formatter.save(results, f"{base_path}.json"):
                success = False

        if "csv" in formats:
            if not csv_formatter.save(results, f"{base_path}.csv"):
                success = False

        if "xlsx" in formats:
            if not excel_formatter.save(results, f"{base_path}.xlsx"):
                success = False

        return success
