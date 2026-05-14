"""
SERP Agent - Specializes in Google Search scraping.
"""
import time
import random
from typing import Dict, Any, List
from urllib.parse import urlparse
from loguru import logger

from .base_agent import BaseAgent, AgentResult, Task, Priority


class SERPAgent(BaseAgent):
    """
    Specialized agent for scraping Google Search Results.
    Handles SERP-specific challenges like rate limiting, CAPTCHA, and parsing.
    """

    def __init__(self, agent_id: str, config: Dict[str, Any]):
        super().__init__(agent_id, config)
        self.domains_tried = []
        self.query_cache: Dict[str, List] = {}

    def get_specialization(self) -> str:
        return "google_serp,search_results,serp_scraping"

    def can_handle(self, task: Task) -> bool:
        """This agent handles Google search tasks."""
        if task.task_type == "serp":
            return True
        if "google" in task.url.lower() or "search" in task.task_type.lower():
            return True
        return False

    def execute_task(self, task: Task) -> AgentResult:
        """Execute SERP scraping task."""
        start_time = time.time()
        self.tasks_completed += 1

        query = task.context.get("query", "")
        pages = task.context.get("pages", 1)

        logger.info(f"{self.name} scraping SERP: {query}")

        results = []
        domains = self.config.get("google_serp", {}).get("domains", [
            "https://www.google.com",
            "https://www.google.co.uk",
            "https://www.google.de",
        ])

        for page in range(pages):
            success = False
            for domain in domains:
                if domain in self.domains_tried[-3:]:
                    continue

                try:
                    page_results = self._scrape_google(domain, query, page * 10)
                    if page_results:
                        results.extend(page_results)
                        success = True
                        self.domains_tried.append(domain)
                        break

                except Exception as e:
                    logger.debug(f"Failed {domain}: {e}")
                    self.domains_tried.append(domain)

                time.sleep(random.uniform(3, 8))

            if not success:
                # Try browser if requests failed
                try:
                    page_results = self._scrape_with_browser(query, page * 10)
                    if page_results:
                        results.extend(page_results)
                        success = True
                except Exception as e:
                    logger.warning(f"Browser scrape failed: {e}")

        duration = int((time.time() - start_time) * 1000)
        self.total_data_scraped += len(results)

        return AgentResult(
            success=len(results) > 0,
            task_id=task.id,
            agent_id=self.agent_id,
            data=results,
            duration_ms=duration,
            attempts=len(self.domains_tried),
            techniques_used=["domain_rotation", "request_delay"],
        )

    def _scrape_google(self, domain: str, query: str, start: int) -> List[Dict]:
        """Scrape Google using requests."""
        from ..modules.anti_detection import RequestSession

        session = RequestSession(self.config)
        url = f"{domain}/search?q={query}&start={start}"

        response = session.get(url)
        html = response.text

        # Check for blocks
        if self._is_blocked(html):
            raise Exception("Blocked by Google")

        return self._parse_serp(html)

    def _scrape_with_browser(self, query: str, start: int) -> List[Dict]:
        """Scrape Google using browser automation."""
        from ..modules.browser import BuiltInStealthBrowser

        browser = BuiltInStealthBrowser(self.config)

        try:
            browser.start()
            url = f"https://www.google.com/search?q={query}&start={start}"
            html = browser.navigate_and_wait(url, wait_selector="#search")

            if html:
                return self._parse_serp(html)
            return []

        finally:
            browser.close()

    def _is_blocked(self, html: str) -> bool:
        """Check if blocked."""
        blocked = [
            "our systems have detected unusual traffic",
            "not a robot",
            "captcha",
            "enable javascript",
        ]
        html_lower = html.lower()
        return any(b in html_lower for b in blocked)

    def _parse_serp(self, html: str) -> List[Dict]:
        """Parse SERP HTML into structured data."""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")
        results = []

        for result in soup.select(".g, [data-ved], .yuRUbf"):
            try:
                title_elem = result.select_one("h3, [role='heading']")
                link_elem = result.select_one("a[href]")
                snippet_elem = result.select_one(".VwiC3b, .IsZvec, .st")

                if title_elem and link_elem:
                    results.append({
                        "type": "search_result",
                        "title": title_elem.get_text(strip=True),
                        "url": link_elem.get("href", ""),
                        "snippet": snippet_elem.get_text(strip=True) if snippet_elem else "",
                    })
            except Exception:
                continue

        # Parse People Also Ask
        for paa in soup.select(".wQiwMc, [data-q]"):
            try:
                question = paa.get_text(strip=True)
                if question and len(question) > 10:
                    results.append({
                        "type": "people_also_ask",
                        "question": question,
                    })
            except Exception:
                continue

        return results

    def can_help_with(self, problem: Dict[str, Any]) -> bool:
        """Can help with SERP-related problems."""
        problem_type = problem.get("problem_type", "")
        url = problem.get("url", "")

        if "serp" in problem_type.lower() or "google" in url.lower():
            return True
        if problem_type in ["rate_limited", "captcha", "bot_detected"]:
            return True
        return False

    def provide_help(self, problem: Dict[str, Any]) -> Dict[str, Any]:
        """Provide help with SERP scraping problems."""
        help_data = {
            "suggestions": [],
            "techniques": [],
        }

        problem_type = problem.get("problem_type", "")

        if problem_type == "rate_limited":
            help_data["suggestions"].append("Rotate Google domains")
            help_data["techniques"].append("Use google.co.uk, google.de instead of google.com")

        if problem_type == "captcha":
            help_data["suggestions"].append("Use browser automation")
            help_data["techniques"].append("Playwright with stealth mode")

        if problem_type == "bot_detected":
            help_data["suggestions"].append("Add longer delays between requests")
            help_data["techniques"].append("Wait 5-10 seconds between searches")

        return help_data

    def share_skills(self) -> List[Dict[str, Any]]:
        """Share SERP-specific skills."""
        return [
            {
                "name": "Google Domain Rotation",
                "category": "serp",
                "problem_type": "rate_limited",
                "solution": {
                    "method": "rotate_domains",
                    "domains": ["google.com", "google.co.uk", "google.de"],
                },
                "confidence": 0.85,
            },
        ]
