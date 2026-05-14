"""
Browser Agent - Specializes in JavaScript-heavy site scraping.
"""
import time
from typing import Dict, Any, List
from loguru import logger

from .base_agent import BaseAgent, AgentResult, Task


class BrowserAgent(BaseAgent):
    """
    Specialized agent for scraping JavaScript-rendered pages.
    Uses Playwright with advanced stealth techniques.
    """

    def __init__(self, agent_id: str, config: Dict[str, Any]):
        super().__init__(agent_id, config)
        self.pages_loaded = 0

    def get_specialization(self) -> str:
        return "javascript,js_rendering,browser_automation,spa"

    def can_handle(self, task: Task) -> bool:
        """Handles JS-heavy sites."""
        js_indicators = ["react", "vue", "angular", "nextjs", "shopify", "wix"]
        url = task.url.lower()

        if any(ind in url for ind in js_indicators):
            return True

        if task.context.get("requires_js"):
            return True

        return False

    def execute_task(self, task: Task) -> AgentResult:
        """Execute browser-based scraping."""
        start_time = time.time()
        self.tasks_completed += 1

        logger.info(f"{self.name} scraping with browser: {task.url}")

        browser = None
        try:
            from ..modules.browser import BuiltInStealthBrowser

            browser = BuiltInStealthBrowser(self.config)
            browser.start()

            html = browser.navigate_and_wait(
                task.url,
                wait_selector=task.context.get("wait_selector"),
                scroll_count=task.context.get("scroll_count", 2),
            )

            if not html:
                raise Exception("Browser returned empty content")

            self.pages_loaded += 1

            # Parse data
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "lxml")

            results = self._extract_data(soup, task.selectors)

            duration = int((time.time() - start_time) * 1000)
            self.total_data_scraped += len(results)

            return AgentResult(
                success=len(results) > 0,
                task_id=task.id,
                agent_id=self.agent_id,
                data=results,
                duration_ms=duration,
                attempts=1,
                techniques_used=["browser_automation", "stealth_mode"],
            )

        except Exception as e:
            logger.error(f"Browser scrape failed: {e}")
            self.tasks_failed += 1

            return AgentResult(
                success=False,
                task_id=task.id,
                agent_id=self.agent_id,
                error=str(e),
                duration_ms=int((time.time() - start_time) * 1000),
            )

        finally:
            if browser:
                browser.close()

    def _extract_data(self, soup, selectors: Dict[str, str]) -> List[Dict]:
        """Extract data using selectors."""
        if not selectors:
            selectors = self._auto_detect(soup)

        results = []

        # Find containers
        containers = self._find_containers(soup)

        for container in containers:
            item = {}
            for field_name, selector in selectors.items():
                elem = container.select_one(selector)
                if elem:
                    if field_name == "url":
                        item[field_name] = elem.get("href", "")
                    elif field_name == "image":
                        item[field_name] = elem.get("src", "")
                    else:
                        item[field_name] = elem.get_text(strip=True)
            if item:
                results.append(item)

        return results

    def _auto_detect(self, soup) -> Dict[str, str]:
        """Auto-detect common selectors."""
        selectors = {}

        if soup.select_one("h1, h2"):
            selectors["title"] = "h1, h2"
        if soup.select_one("a[href]"):
            selectors["url"] = "a[href]"
        if soup.select_one("img"):
            selectors["image"] = "img"
        if soup.select_one("p"):
            selectors["description"] = "p"

        return selectors

    def _find_containers(self, soup) -> List:
        """Find data containers."""
        patterns = [
            "[class*='item']", "[class*='card']", "[class*='product']",
            "[class*='listing']", "[class*='result']", "article",
        ]

        for pattern in patterns:
            containers = soup.select(pattern)
            if len(containers) > 1:
                return containers

        return [soup]

    def can_help_with(self, problem: Dict[str, Any]) -> bool:
        """Can help with JS rendering problems."""
        problem_type = problem.get("problem_type", "")

        if problem_type in ["js_required", "empty_content"]:
            return True

        evidence = str(problem.get("evidence", []))
        if "empty" in evidence.lower() or "loading" in evidence.lower():
            return True

        return False

    def provide_help(self, problem: Dict[str, Any]) -> Dict[str, Any]:
        """Provide help with JS rendering."""
        return {
            "suggestions": [
                "Use Playwright browser automation",
                "Wait for content to load with wait_selector",
                "Enable stealth mode to avoid detection",
            ],
            "techniques": [
                "page.waitForSelector() before scraping",
                "Scroll to trigger lazy loading",
                "Inject anti-detection scripts",
            ],
        }

    def share_skills(self) -> List[Dict[str, Any]]:
        """Share browser-specific skills."""
        return [
            {
                "name": "JS Rendering Detection",
                "category": "rendering",
                "problem_type": "js_required",
                "solution": {
                    "method": "use_browser",
                    "wait_time": 3000,
                    "scroll": True,
                },
                "confidence": 0.9,
            },
        ]
