"""
Self-Evolving Scraper - Main orchestrator with learning capabilities.
"""
import time
import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from loguru import logger

from .skill_db import SkillDatabase, Skill
from .skill_matcher import SkillMatcher, SkillApplicator
from .skill_generator import SkillGenerator
from .problem_analyzer import ProblemAnalyzer, Problem

from ..modules.browser import BuiltInStealthBrowser
from ..modules.anti_detection import AntiDetection, RequestSession
from ..modules.rate_limiter import AdaptiveRateLimiter
from ..modules.retry import RetryHandler, RetryConfig


@dataclass
class Attempt:
    """Record of a scraping attempt."""
    timestamp: str
    url: str
    method: str
    config: Dict[str, Any]
    success: bool
    error: Optional[str] = None
    data_count: int = 0
    duration_ms: int = 0
    skill_id: Optional[int] = None


@dataclass
class ScrapeSession:
    """A scraping session with learning."""
    url: str
    start_time: str = field(default_factory=lambda: datetime.now().isoformat())
    attempts: List[Attempt] = field(default_factory=list)
    current_config: Dict[str, Any] = field(default_factory=dict)
    learned_skills_applied: List[int] = field(default_factory=list)
    problem: Optional[Problem] = None
    successful_skill_id: Optional[int] = None

    def add_attempt(self, attempt: Attempt):
        """Add an attempt to the session."""
        self.attempts.append(attempt)

    def get_successful_attempt(self) -> Optional[Attempt]:
        """Get the last successful attempt."""
        for attempt in reversed(self.attempts):
            if attempt.success:
                return attempt
        return None

    def get_attempt_count(self) -> int:
        """Get total number of attempts."""
        return len(self.attempts)


class SelfEvolvingScraper:
    """
    Self-evolving scraper that learns from failures and improves over time.

    Workflow:
    1. Analyze problem (if any)
    2. Find matching skills from database
    3. Apply skills with increasing sophistication
    4. If no skill works, try creative solutions
    5. Learn from successful solutions
    6. Store new skills for future use
    """

    def __init__(self, config: dict):
        self.config = config

        # Initialize components
        self.skill_db = SkillDatabase()
        self.problem_analyzer = ProblemAnalyzer()
        self.skill_matcher = SkillMatcher(self.skill_db)
        self.skill_generator = SkillGenerator(self.skill_db)
        self.skill_applicator = SkillApplicator(config)

        # Scraping components
        self.anti_detection = AntiDetection(config)
        self.rate_limiter = AdaptiveRateLimiter(config)
        self.browser = None

        # Learning settings
        self.max_attempts = 10
        self.learn_on_success = True
        self.learn_on_failure = True

    def scrape(
        self,
        url: str,
        selectors: Dict[str, str] = None,
        pagination: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        Scrape a URL with self-learning capabilities.

        Returns:
            {
                "success": bool,
                "data": list,
                "session": ScrapeSession,
                "skill_used": Skill or None,
            }
        """
        session = ScrapeSession(
            url=url,
            current_config=self._get_default_config(),
        )

        logger.info(f"Starting self-evolving scrape of {url}")

        # Start attempt loop
        while session.get_attempt_count() < self.max_attempts:
            attempt = self._make_attempt(url, session, selectors, pagination)

            if attempt.success:
                logger.info(f"Success on attempt {session.get_attempt_count()}")
                session.successful_skill_id = attempt.skill_id
                return {
                    "success": True,
                    "data": self._extract_data_from_attempt(attempt),
                    "session": session,
                    "skill_used": self.skill_db.get_skill(attempt.skill_id) if attempt.skill_id else None,
                }

            # Analyze failure
            session.problem = self.problem_analyzer.analyze_response(
                url=url,
                html=attempt.error or "",
                error_message=attempt.error or "",
            )

            if session.problem:
                logger.info(f"Detected problem: {session.problem.problem_type} - {session.problem.description}")

                # Check if we've tried everything
                if session.get_attempt_count() >= 3 and not session.successful_skill_id:
                    # Try harder solutions
                    session.current_config = self._escalate_solution(session.current_config)

            # Record attempt
            session.add_attempt(attempt)

            # Small delay before retry
            time.sleep(1)

        # All attempts failed
        logger.warning(f"Failed to scrape {url} after {session.get_attempt_count()} attempts")

        # Learn from failure if significant
        if self.learn_on_failure:
            self._learn_from_failure(session)

        return {
            "success": False,
            "data": [],
            "session": session,
            "skill_used": None,
        }

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default scraping configuration."""
        return {
            "use_browser": False,
            "delay": 2,
            "headers": {},
            "proxies": [],
            "use_proxy": False,
            "stealth_mode": True,
            "solve_math_captcha": False,
            "pagination": None,
        }

    def _make_attempt(
        self,
        url: str,
        session: ScrapeSession,
        selectors: Dict[str, str],
        pagination: Dict[str, Any],
    ) -> Attempt:
        """Make a single scraping attempt."""
        start_time = time.time()
        config = session.current_config.copy()

        # Check if we have a matching skill
        skill = None
        if session.problem:
            skill = self.skill_matcher.find_best_skill(session.problem, url)
            if skill and self.skill_matcher.should_apply_skill(skill, session.get_attempt_count()):
                config = self.skill_applicator.apply_skill(skill, config)
                logger.info(f"Applying skill: {skill.name}")

        try:
            if config.get("use_browser"):
                data, html = self._scrape_with_browser(url, selectors, config)
            else:
                data, html = self._scrape_with_requests(url, selectors, config)

            duration = int((time.time() - start_time) * 1000)

            # Check if we got meaningful data
            if data and len(data) > 0:
                # Success!
                if skill:
                    self.skill_db.record_skill_usage(skill.id, True)

                return Attempt(
                    timestamp=datetime.now().isoformat(),
                    url=url,
                    method="browser" if config.get("use_browser") else "requests",
                    config=config,
                    success=True,
                    data_count=len(data),
                    duration_ms=duration,
                    skill_id=skill.id if skill else None,
                )
            else:
                # Empty response
                return Attempt(
                    timestamp=datetime.now().isoformat(),
                    url=url,
                    method="browser" if config.get("use_browser") else "requests",
                    config=config,
                    success=False,
                    error=html or "Empty response",
                    duration_ms=duration,
                    skill_id=skill.id if skill else None,
                )

        except Exception as e:
            duration = int((time.time() - start_time) * 1000)
            error_msg = str(e)

            if skill:
                self.skill_db.record_skill_usage(skill.id, False)

            return Attempt(
                timestamp=datetime.now().isoformat(),
                url=url,
                method="browser" if config.get("use_browser") else "requests",
                config=config,
                success=False,
                error=error_msg,
                duration_ms=duration,
                skill_id=skill.id if skill else None,
            )

    def _scrape_with_requests(
        self,
        url: str,
        selectors: Dict[str, str],
        config: Dict[str, Any],
    ) -> tuple:
        """Scrape using requests library."""
        session = RequestSession(self.config)

        # Apply delays
        if config.get("delay"):
            time.sleep(config["delay"])

        response = session.get(url)
        html = response.text

        # Parse data
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "lxml")
        data = self._extract_with_selectors(soup, selectors or {})

        return data, html

    def _scrape_with_browser(
        self,
        url: str,
        selectors: Dict[str, str],
        config: Dict[str, Any],
    ) -> tuple:
        """Scrape using browser automation."""
        browser = BuiltInStealthBrowser(self.config)

        try:
            browser.start()
            html = browser.navigate_and_wait(
                url,
                wait_selector=config.get("wait_selector"),
            )

            if not html:
                raise Exception("Browser returned empty content")

            # Handle Cloudflare if needed
            if config.get("browser_action") == "cloudflare_bypass":
                self._handle_cloudflare(browser)

            # Solve math CAPTCHA if needed
            if config.get("solve_math_captcha"):
                self._solve_math_captcha(browser)

            # Get final HTML
            html = browser.get_page_html() or ""

            # Parse data
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "lxml")
            data = self._extract_with_selectors(soup, selectors or {})

            return data, html

        finally:
            browser.close()

    def _extract_with_selectors(self, soup, selectors: Dict[str, str]) -> List[Dict[str, Any]]:
        """Extract data using CSS selectors."""
        if not selectors:
            # Auto-detect
            selectors = self._auto_detect_selectors(soup)

        results = []
        containers = self._find_containers(soup)

        for container in containers:
            item = {}
            for field_name, selector in selectors.items():
                elem = container.select_one(selector)
                if elem:
                    item[field_name] = elem.get_text(strip=True)
                    if field_name == "url":
                        item[field_name] = elem.get("href", "")
            if item:
                results.append(item)

        return results

    def _auto_detect_selectors(self, soup) -> Dict[str, str]:
        """Auto-detect common selectors."""
        selectors = {}

        if soup.select_one("h1, h2, h3"):
            selectors["title"] = "h1, h2, h3"
        if soup.select_one("a[href]"):
            selectors["url"] = "a[href]"
        if soup.select_one("p"):
            selectors["description"] = "p"
        if soup.select_one("img"):
            selectors["image"] = "img"

        return selectors

    def _find_containers(self, soup) -> List:
        """Find data containers."""
        container_patterns = [
            "[class*='item']", "[class*='card']", "[class*='product']",
            "[class*='listing']", "[class*='result']", "article",
        ]

        for pattern in container_patterns:
            containers = soup.select(pattern)
            if len(containers) > 1:
                return containers

        return [soup]  # Return soup as single container

    def _extract_data_from_attempt(self, attempt: Attempt) -> List[Dict]:
        """Extract actual data from successful attempt."""
        # This would parse the stored HTML/data
        return []  # Placeholder - actual implementation would parse stored content

    def _handle_cloudflare(self, browser):
        """Handle Cloudflare challenge."""
        time.sleep(3)

        try:
            # Try clicking checkbox
            checkbox = browser._page.query_selector('[type="checkbox"]') if browser._page else None
            if checkbox:
                checkbox.click()
                time.sleep(2)
        except:
            pass

    def _solve_math_captcha(self, browser):
        """Solve simple math CAPTCHA."""
        try:
            if browser._page:
                # Find math question
                question = browser._page.query_selector("[class*='challenge'], [class*='math'], [class*='captcha']")
                if question:
                    text = question.inner_text()
                    # Extract math problem
                    import re
                    match = re.search(r'(\d+)\s*([+\-x*])\s*(\d+)', text)
                    if match:
                        a, op, b = int(match.group(1)), match.group(2), int(match.group(3))
                        if op == "+":
                            result = a + b
                        elif op == "-":
                            result = a - b
                        elif op in ("x", "*"):
                            result = a * b

                        # Fill answer
                        input_field = browser._page.query_selector("input[type='text'], input[type='number']")
                        if input_field:
                            input_field.fill(str(result))
        except:
            pass

    def _escalate_solution(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Escalate to more sophisticated solutions."""
        new_config = config.copy()

        if not config.get("use_browser"):
            # First escalation: use browser
            new_config["use_browser"] = True
            new_config["stealth_mode"] = True
            logger.info("Escalating: switching to browser automation")
        elif not config.get("use_proxy"):
            # Second escalation: add proxy
            new_config["use_proxy"] = True
            logger.info("Escalating: enabling proxy rotation")
        elif not config.get("solve_math_captcha"):
            # Third escalation: solve CAPTCHA
            new_config["solve_math_captcha"] = True
            logger.info("Escalating: enabling CAPTCHA solving")
        elif config.get("delay", 2) < 10:
            # Fourth escalation: increase delay
            new_config["delay"] = min(30, config.get("delay", 2) * 2)
            logger.info(f"Escalating: increasing delay to {new_config['delay']}s")
        else:
            # Final escalation: try different approach
            new_config["try_alternative"] = True
            logger.info("Escalating: trying alternative approach")

        return new_config

    def _learn_from_failure(self, session: ScrapeSession):
        """Learn from failed attempts."""
        if not session.problem:
            return

        # Check if this is a new pattern
        existing = self.skill_db.find_by_keywords(
            session.problem.keywords[:3],
            limit=5
        )

        # If no similar skills, consider creating a "failed" record for analysis
        if not existing:
            logger.info(f"New problem pattern detected: {session.problem.problem_type}")
            logger.info(f"Keywords: {session.problem.keywords[:5]}")

            # We could create a skill with low confidence marking it as "needs work"
            # But for now, just log it for manual review

    def learn_from_success(
        self,
        session: ScrapeSession,
        url: str,
        selectors: Dict[str, str],
    ):
        """Learn from successful scrape."""
        successful = session.get_successful_attempt()
        if not successful:
            return

        # Find what worked
        solution = self._extract_solution_from_attempt(successful)

        # Generate or improve skill
        if session.problem:
            # Generate new skill
            new_skill = self.skill_generator.generate_skill_from_solution(
                problem=session.problem,
                solution=solution,
                url=url,
                success=True,
            )

            if new_skill:
                # Check if similar skill exists
                existing = self.skill_matcher.find_candidate_skills(session.problem, url)

                if existing:
                    # Improve existing skill
                    for skill in existing[:1]:
                        improved = self.skill_generator.improve_skill(
                            skill, solution, success=True
                        )
                        self.skill_db.update_skill(improved)
                        logger.info(f"Improved existing skill: {skill.name}")
                else:
                    # Add new skill
                    skill_id = self.skill_db.add_skill(new_skill)
                    logger.info(f"Learned new skill: {new_skill.name} (ID: {skill_id})")

    def _extract_solution_from_attempt(self, attempt: Attempt) -> Dict[str, Any]:
        """Extract what solution was used in successful attempt."""
        solution = {
            "method": attempt.method,
            "changes": {},
        }

        config = attempt.config

        if config.get("use_browser"):
            solution["changes"]["use_browser"] = True
        if config.get("delay", 2) > 2:
            solution["changes"]["delay"] = config["delay"]
        if config.get("use_proxy"):
            solution["changes"]["proxy"] = True
        if config.get("stealth_mode"):
            solution["applied_techniques"].append("stealth") if "applied_techniques" not in solution else solution["applied_techniques"].append("stealth")
        if config.get("solve_math_captcha"):
            solution["changes"]["solve_captcha"] = True

        return solution

    def get_learning_stats(self) -> Dict[str, Any]:
        """Get learning statistics."""
        db_stats = self.skill_db.get_statistics()

        return {
            "total_skills": db_stats.get("total_skills", 0),
            "skills_by_category": db_stats.get("skills_by_category", {}),
            "avg_confidence": db_stats.get("avg_confidence", 0),
            "avg_success_rate": db_stats.get("avg_success_rate", 0),
            "total_scrapes": db_stats.get("total_scrape_attempts", 0),
            "successful_scrapes": db_stats.get("successful_scrapes", 0),
        }

    def export_knowledge(self, filepath: str):
        """Export learned skills."""
        self.skill_db.export_skills(filepath)

    def import_knowledge(self, filepath: str):
        """Import skills from file."""
        return self.skill_db.import_skills(filepath)

    def reset_learning(self):
        """Reset learned skills (keeps built-in skills)."""
        # Delete all non-built-in skills
        with self.skill_db._get_connection() as conn:
            conn.execute("DELETE FROM skills WHERE confidence < 0.5 OR use_count < 2")
            conn.execute("DELETE FROM scrape_history")
            conn.commit()
        logger.info("Reset learned skills (kept established skills)")
