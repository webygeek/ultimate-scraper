"""
Generic Agent - Fallback agent for general scraping.
"""
import time
from typing import Dict, Any, List
from loguru import logger

from .base_agent import BaseAgent, AgentResult, Task


class GenericAgent(BaseAgent):
    """
    Generic agent for scraping any website.
    Tries multiple approaches and learns from failures.
    """

    def __init__(self, agent_id: str, config: Dict[str, Any]):
        super().__init__(agent_id, config)
        self.techniques_learned: List[Dict] = []

    def get_specialization(self) -> str:
        return "general,universal,fallback,any_site"

    def can_handle(self, task: Task) -> bool:
        """Can handle any task."""
        return True  # This is the fallback agent

    def execute_task(self, task: Task) -> AgentResult:
        """Execute generic scraping with multi-strategy approach."""
        start_time = time.time()
        self.tasks_completed += 1

        logger.info(f"{self.name} scraping: {task.url}")

        attempts = []
        techniques_used = []

        # Strategy 1: Simple requests
        try:
            result = self._try_requests(task)
            if result:
                attempts.append({"technique": "requests", "success": True, "data": result})
                techniques_used.append("requests")
            else:
                attempts.append({"technique": "requests", "success": False})
        except Exception as e:
            attempts.append({"technique": "requests", "success": False, "error": str(e)})

        # Strategy 2: Browser automation (if requests failed)
        if not attempts[-1].get("success"):
            try:
                result = self._try_browser(task)
                if result:
                    attempts.append({"technique": "browser", "success": True, "data": result})
                    techniques_used.append("browser_automation")
                else:
                    attempts.append({"technique": "browser", "success": False})
            except Exception as e:
                attempts.append({"technique": "browser", "success": False, "error": str(e)})

        # Strategy 3: API detection (try to find hidden APIs)
        if not any(a.get("success") for a in attempts):
            try:
                result = self._try_api_discovery(task)
                if result:
                    attempts.append({"technique": "api", "success": True, "data": result})
                    techniques_used.append("api_discovery")
            except Exception as e:
                attempts.append({"technique": "api", "success": False, "error": str(e)})

        # Find successful attempt
        successful = next((a for a in attempts if a.get("success")), None)

        if successful:
            duration = int((time.time() - start_time) * 1000)
            self.total_data_scraped += len(successful.get("data", []))

            return AgentResult(
                success=True,
                task_id=task.id,
                agent_id=self.agent_id,
                data=successful.get("data", []),
                duration_ms=duration,
                attempts=len(attempts),
                techniques_used=techniques_used,
            )
        else:
            self.tasks_failed += 1
            return AgentResult(
                success=False,
                task_id=task.id,
                agent_id=self.agent_id,
                error="All strategies failed",
                duration_ms=int((time.time() - start_time) * 1000),
                attempts=len(attempts),
                techniques_used=techniques_used,
            )

    def _try_requests(self, task: Task) -> List[Dict]:
        """Try scraping with requests."""
        from ..modules.anti_detection import RequestSession
        from bs4 import BeautifulSoup

        session = RequestSession(self.config)
        response = session.get(task.url)
        html = response.text

        if len(html) < 500:
            return None  # Likely blocked

        soup = BeautifulSoup(html, "lxml")
        return self._extract_with_selectors(soup, task.selectors)

    def _try_browser(self, task: Task) -> List[Dict]:
        """Try scraping with browser."""
        from ..modules.browser import BuiltInStealthBrowser
        from bs4 import BeautifulSoup

        browser = BuiltInStealthBrowser(self.config)

        try:
            browser.start()
            html = browser.navigate_and_wait(task.url)
            browser.close()

            if not html or len(html) < 500:
                return None

            soup = BeautifulSoup(html, "lxml")
            return self._extract_with_selectors(soup, task.selectors)

        finally:
            browser.close()

    def _try_api_discovery(self, task: Task) -> List[Dict]:
        """Try to discover and use hidden APIs."""
        from ..modules.anti_detection import RequestSession
        import re

        session = RequestSession(self.config)
        response = session.get(task.url)
        html = response.text

        # Look for API endpoints in JavaScript
        api_patterns = [
            r'fetch\(["\']([^"\']+)["\']',
            r'axios\.get\(["\']([^"\']+)["\']',
            r'api["\']?\s*:\s*["\']([^"\']+)["\']',
            r'endpoint["\']?\s*:\s*["\']([^"\']+)["\']',
        ]

        for pattern in api_patterns:
            matches = re.findall(pattern, html)
            for api_url in matches[:3]:  # Try first 3 found
                try:
                    # Try relative URLs
                    if api_url.startswith("/"):
                        from urllib.parse import urlparse
                        parsed = urlparse(task.url)
                        api_url = f"{parsed.scheme}://{parsed.netloc}{api_url}"

                    response = session.get(api_url)
                    if response.status_code == 200:
                        import json
                        data = response.json()
                        if isinstance(data, list):
                            return data
                        if isinstance(data, dict) and "results" in data:
                            return data["results"]
                except Exception:
                    continue

        return None

    def _extract_with_selectors(self, soup, selectors: Dict[str, str]) -> List[Dict]:
        """Extract data with selectors."""
        if not selectors:
            selectors = self._auto_detect(soup)

        results = []
        containers = self._find_containers(soup)

        for container in containers:
            item = {}
            for field, selector in selectors.items():
                elem = container.select_one(selector)
                if elem:
                    if field == "url":
                        item[field] = elem.get("href", "")
                    elif field == "image":
                        item[field] = elem.get("src", "") or elem.get("data-src", "")
                    else:
                        item[field] = elem.get_text(strip=True)
            if item:
                results.append(item)

        return results

    def _auto_detect(self, soup) -> Dict[str, str]:
        """Auto-detect common patterns."""
        selectors = {}

        if soup.select_one("h1, h2"):
            selectors["title"] = "h1, h2"
        if soup.select_one("a[href]"):
            selectors["url"] = "a[href]"
        if soup.select_one("img"):
            selectors["image"] = "img"
        if soup.select_one("[class*='price']"):
            selectors["price"] = "[class*='price']"
        if soup.select_one("p"):
            selectors["description"] = "p"

        return selectors

    def _find_containers(self, soup) -> List:
        """Find data containers."""
        patterns = [
            "[class*='item']", "[class*='card']", "[class*='product']",
            "[class*='listing']", "[class*='result']", "article",
            "[class*='post']", "[class*='row']",
        ]

        for pattern in patterns:
            containers = soup.select(pattern)
            if len(containers) > 1:
                return containers

        return [soup]

    def can_help_with(self, problem: Dict[str, Any]) -> bool:
        """Can help with any problem."""
        return True  # This is the fallback

    def provide_help(self, problem: Dict[str, Any]) -> Dict[str, Any]:
        """Provide help with any problem."""
        problem_type = problem.get("problem_type", "unknown")

        suggestions = {
            "bot_detected": ["Use browser automation", "Add delays", "Try proxies"],
            "captcha": ["Use CAPTCHA agent", "Wait and retry"],
            "rate_limited": ["Increase delay", "Use proxy rotation"],
            "js_required": ["Use browser agent", "Wait for content"],
            "unknown": ["Try multiple strategies", "Check URL format"],
        }

        return {
            "suggestions": suggestions.get(problem_type, suggestions["unknown"]),
            "techniques": ["multi_strategy", "fallback", "learning"],
        }

    def share_skills(self) -> List[Dict[str, Any]]:
        """Share generic scraping skills."""
        return [
            {
                "name": "Multi-Strategy Scraping",
                "category": "general",
                "problem_type": "any",
                "solution": {
                    "method": "fallback_chain",
                    "strategies": ["requests", "browser", "api"],
                },
                "confidence": 0.7,
            },
        ]

    def _learn_from_others(self, skill: Dict[str, Any]) -> None:
        """Learn a new technique from another agent."""
        if skill not in self.techniques_learned:
            self.techniques_learned.append(skill)
            logger.info(f"{self.name} learned: {skill.get('name', 'unknown technique')}")
