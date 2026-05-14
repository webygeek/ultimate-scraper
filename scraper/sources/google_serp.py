"""
Google Search Results (SERP) scraper with anti-detection.
"""
import re
import time
import random
from datetime import datetime
from typing import Optional
from bs4 import BeautifulSoup
from loguru import logger

from ..modules.browser import BrowserManager
from ..modules.anti_detection import RequestSession


class GoogleSERPScraper:
    """
    Scrapes Google Search Results overcoming common blocks.
    Uses multiple strategies: direct HTML, API simulation, and browser automation.
    """

    def __init__(self, config: dict):
        self.config = config
        self.serp_config = config.get("google_serp", {})
        self.results_per_page = self.serp_config.get("results_per_page", 10)
        self.max_pages = self.serp_config.get("max_pages", 5)
        self.country = self.serp_config.get("country", "us")
        self.language = self.serp_config.get("language", "en")

        self.browser = BrowserManager(config)
        self.session = RequestSession(config)

        self._results_cache = []

    def scrape(
        self,
        query: str,
        pages: int = 1,
        include_knowledge_graph: bool = True,
        include_people_also_ask: bool = True,
    ) -> list[dict]:
        """
        Scrape Google search results for a query.

        Args:
            query: Search query
            pages: Number of result pages to scrape
            include_knowledge_graph: Include knowledge graph data
            include_people_also_ask: Include "People also ask" section

        Returns:
            List of search result dictionaries
        """
        all_results = []
        pages = min(pages, self.max_pages)

        for page in range(pages):
            start = page * self.results_per_page
            logger.info(f"Scraping page {page + 1}/{pages} (start={start})")

            results = self._scrape_page(
                query,
                start=start,
                include_knowledge_graph=include_knowledge_graph if page == 0 else False,
                include_people_also_ask=include_people_also_ask if page == 0 else False,
            )

            all_results.extend(results)

            # Rate limiting
            if page < pages - 1:
                delay = random.uniform(5, 15)
                logger.debug(f"Waiting {delay:.1f}s before next page")
                time.sleep(delay)

        self._results_cache = all_results
        return all_results

    def _scrape_page(
        self,
        query: str,
        start: int = 0,
        include_knowledge_graph: bool = False,
        include_people_also_ask: bool = False,
    ) -> list[dict]:
        """Scrape a single page of results."""
        url = self._build_url(query, start)

        # Try different strategies
        results = []

        # Strategy 1: Browser automation (most reliable but slowest)
        if self._should_use_browser():
            results = self._scrape_with_browser(url, include_knowledge_graph, include_people_also_ask)
        else:
            # Strategy 2: Direct request with anti-detection
            results = self._scrape_with_requests(url, include_knowledge_graph, include_people_also_ask)

        # If both fail, try alternative Google domains
        if not results:
            results = self._scrape_alternative_domains(query, start)

        return results

    def _should_use_browser(self) -> bool:
        """Decide whether to use browser automation."""
        return random.random() < 0.3  # 30% of the time use browser

    def _build_url(self, query: str, start: int = 0) -> str:
        """Build Google search URL with parameters."""
        import urllib.parse

        params = {
            "q": query,
            "hl": self.language,
            "gl": self.country,
            "start": start,
            "num": self.results_per_page,
        }

        return f"https://www.google.com/search?{urllib.parse.urlencode(params)}"

    def _scrape_with_browser(
        self,
        url: str,
        include_knowledge_graph: bool,
        include_people_also_ask: bool,
    ) -> list[dict]:
        """Scrape using Playwright browser automation."""
        if not self.browser.start():
            return []

        try:
            html = self.browser.navigate_and_wait(
                url,
                wait_selector="#search",
                wait_timeout=30000,
            )

            if not html:
                return []

            return self._parse_html(html, include_knowledge_graph, include_people_also_ask)

        except Exception as e:
            logger.error(f"Browser scrape failed: {e}")
            return []
        finally:
            self.browser.close()

    def _scrape_with_requests(
        self,
        url: str,
        include_knowledge_graph: bool,
        include_people_also_ask: bool,
    ) -> list[dict]:
        """Scrape using requests with anti-detection."""
        try:
            response = self.session.get(url)
            html = response.text

            # Check for blocks
            if self._is_blocked(html):
                logger.warning("Direct request blocked, trying alternative...")
                return []

            return self._parse_html(html, include_knowledge_graph, include_people_also_ask)

        except Exception as e:
            logger.error(f"Request scrape failed: {e}")
            return []

    def _scrape_alternative_domains(self, query: str, start: int) -> list[dict]:
        """Try alternative Google domains (google.com, google.co.uk, etc.)."""
        alternative_domains = [
            "https://www.google.com",
            "https://www.google.co.uk",
            "https://www.google.de",
            "https://www.google.fr",
        ]

        random.shuffle(alternative_domains)

        for domain in alternative_domains[:2]:
            try:
                import urllib.parse
                params = urllib.parse.urlencode({
                    "q": query,
                    "hl": self.language,
                    "start": start,
                })
                url = f"{domain}/search?{params}"

                response = self.session.get(url)
                html = response.text

                if not self._is_blocked(html):
                    return self._parse_html(html, False, False)

            except Exception:
                continue

        return []

    def _is_blocked(self, html: str) -> bool:
        """Check if the response indicates we're blocked."""
        blocked_indicators = [
            "Our systems have detected unusual traffic",
            "not a robot",
            "CAPTCHA",
            "enable JavaScript",
            "unusual traffic patterns",
            "try again later",
        ]

        html_lower = html.lower()
        return any(indicator.lower() in html_lower for indicator in blocked_indicators)

    def _parse_html(
        self,
        html: str,
        include_knowledge_graph: bool,
        include_people_also_ask: bool,
    ) -> list[dict]:
        """Parse Google search results from HTML."""
        soup = BeautifulSoup(html, "lxml")
        results = []

        # Parse main search results
        for result in soup.select(".g, [data-ved], .yuRUbf"):
            try:
                parsed = self._parse_single_result(result)
                if parsed:
                    results.append(parsed)
            except Exception as e:
                logger.debug(f"Failed to parse result: {e}")

        # Parse People Also Ask
        if include_people_also_ask:
            paa_results = self._parse_people_also_ask(soup)
            results.extend(paa_results)

        # Parse Knowledge Graph
        if include_knowledge_graph:
            kg_data = self._parse_knowledge_graph(soup)
            if kg_data:
                results.append(kg_data)

        # Add metadata
        for result in results:
            result["scraped_at"] = datetime.now().isoformat()

        return results

    def _parse_single_result(self, element) -> Optional[dict]:
        """Parse a single search result."""
        try:
            # Get title and link
            title_elem = element.select_one("h3, [role='heading']")
            if not title_elem:
                return None

            title = title_elem.get_text(strip=True)

            link_elem = element.select_one("a[href]")
            if not link_elem:
                return None

            url = link_elem.get("href", "")

            # Skip if not a valid URL
            if not url or not url.startswith("http"):
                return None

            # Get snippet/description
            snippet_elem = element.select_one(".VwiC3b, .IsZvec, [data-sncf], .st")
            snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""

            # Get displayed URL
            displayed_url_elem = element.select_one(".tjvcx, .CSkcDe, cite")
            displayed_url = displayed_url_elem.get_text(strip=True) if displayed_url_elem else ""

            # Get rating if present
            rating_elem = element.select_one(".lzcfc, [aria-label*='rating']")
            rating = None
            if rating_elem:
                rating_text = rating_elem.get_text(strip=True)
                match = re.search(r"(\d+\.?\d*)", rating_text)
                if match:
                    rating = float(match.group(1))

            return {
                "type": "search_result",
                "title": title,
                "url": url,
                "displayed_url": displayed_url,
                "snippet": snippet,
                "rating": rating,
            }

        except Exception:
            return None

    def _parse_people_also_ask(self, soup) -> list[dict]:
        """Parse 'People also ask' section."""
        results = []

        for paa in soup.select(".wQiwMc, [data-q], .related-question"):
            try:
                question_elem = paa.select_one(".related-question-pair__Question, .wQiwMc")
                answer_elem = paa.select_one(".related-question-pair__Snippet")

                if question_elem:
                    question = question_elem.get_text(strip=True)
                    answer = answer_elem.get_text(strip=True) if answer_elem else ""

                    results.append({
                        "type": "people_also_ask",
                        "question": question,
                        "answer": answer,
                    })
            except Exception:
                continue

        return results

    def _parse_knowledge_graph(self, soup) -> Optional[dict]:
        """Parse knowledge graph if present."""
        kg = soup.select_one("[data-kboxid], .kp-wholepage, #knowledge-panel")
        if not kg:
            return None

        try:
            title_elem = kg.select_one("[data-ved], .kno-ecr-pt, .SPZz6b")
            title = title_elem.get_text(strip=True) if title_elem else ""

            description_elem = kg.select_one(".kno-rdesc, .aCOpRe")
            description = description_elem.get_text(strip=True) if description_elem else ""

            attributes = {}
            for attr in kg.select(".w8qArf, .kyLfmc"):
                label_elem = attr.select_one(".w8qArf, .kyLfmc")
                value_elem = attr.select_one(".rVSkhe")

                if label_elem and value_elem:
                    attributes[label_elem.get_text(strip=True)] = value_elem.get_text(strip=True)

            return {
                "type": "knowledge_graph",
                "title": title,
                "description": description,
                "attributes": attributes,
            }

        except Exception:
            return None

    def scrape_and_save(
        self,
        query: str,
        output_path: str,
        formats: list[str] = ["json", "csv", "xlsx"],
    ) -> bool:
        """
        Scrape and save results to multiple formats.

        Args:
            query: Search query
            output_path: Base path for output files
            formats: List of formats to export

        Returns:
            True if successful
        """
        from ..output import JSONFormatter, CSVFormatter, ExcelFormatter

        results = self.scrape(query)

        if not results:
            logger.warning("No results scraped")
            return False

        success = True
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_query = re.sub(r"[^\w\s-]", "", query)[:50]
        base_path = f"{output_path}/{safe_query}_{timestamp}"

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
