"""
CAPTCHA Agent - Specializes in solving CAPTCHAs.
"""
import re
import time
from typing import Dict, Any, List, Optional
from loguru import logger

from .base_agent import BaseAgent, AgentResult, Task


class CaptchaAgent(BaseAgent):
    """
    Specialized agent for detecting and solving CAPTCHAs.
    Uses built-in solvers and various bypass techniques.
    """

    def __init__(self, agent_id: str, config: Dict[str, Any]):
        super().__init__(agent_id, config)
        self.captchas_solved = 0
        self.captchas_failed = 0

    def get_specialization(self) -> str:
        return "captcha,solving,bypass,challenge"

    def can_handle(self, task: Task) -> bool:
        """Handles CAPTCHA-related tasks."""
        if task.task_type == "captcha":
            return True

        context = task.context or {}
        if context.get("has_captcha"):
            return True

        return False

    def execute_task(self, task: Task) -> AgentResult:
        """Execute CAPTCHA solving task."""
        start_time = time.time()
        self.tasks_completed += 1

        logger.info(f"{self.name} solving CAPTCHA for: {task.url}")

        captcha_type = task.context.get("captcha_type", "auto")
        html = task.context.get("html", "")
        site_key = task.context.get("site_key", "")

        # Try different solving methods
        solution = None

        if captcha_type in ["math", "auto"]:
            solution = self._solve_math_captcha(html)
            if solution:
                self.captchas_solved += 1

        if not solution and captcha_type in ["text", "auto"]:
            solution = self._solve_text_captcha(html)
            if solution:
                self.captchas_solved += 1

        if not solution and captcha_type in ["checkbox", "auto"]:
            solution = self._solve_checkbox(html)
            if solution:
                self.captchas_solved += 1

        if not solution:
            self.captchas_failed += 1
            return AgentResult(
                success=False,
                task_id=task.id,
                agent_id=self.agent_id,
                error="Could not solve CAPTCHA",
                duration_ms=int((time.time() - start_time) * 1000),
                techniques_used=["captcha_detection"],
            )

        duration = int((time.time() - start_time) * 1000)

        return AgentResult(
            success=True,
            task_id=task.id,
            agent_id=self.agent_id,
            data=[{"solution": solution}],
            duration_ms=duration,
            techniques_used=["captcha_solving", captcha_type],
        )

    def _solve_math_captcha(self, html: str) -> Optional[str]:
        """Solve math-based CAPTCHA."""
        patterns = [
            r"(\d+)\s*([+\-x*])\s*(\d+)",
            r"what is (\d+)\s*([+\-])\s*(\d+)",
            r"(\d+)\s*(plus|minus|times)\s*(\d+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                groups = match.groups()
                if len(groups) == 3:
                    a, op, b = groups[0], groups[1].lower(), groups[2]

                    try:
                        a, b = int(a), int(b)
                        op = op.strip()

                        if op in ["+", "plus"]:
                            return str(a + b)
                        elif op in ["-", "minus"]:
                            return str(a - b)
                        elif op in ["x", "*", "times"]:
                            return str(a * b)
                    except ValueError:
                        continue

        return None

    def _solve_text_captcha(self, html: str) -> Optional[str]:
        """Solve text-based CAPTCHA."""
        # Simple text patterns
        text = html.lower()

        # Color questions
        colors = ["red", "blue", "green", "yellow", "orange", "purple"]
        for color in colors:
            if f"select the {color}" in text or f"click the {color}" in text:
                return color

        # Number questions
        number_match = re.search(r"what is the (\d+)(?:st|nd|rd|th)", text)
        if number_match:
            return number_match.group(1)

        # Simple math (already covered but check here too)
        math_match = re.search(r"(\d+)\s*\+\s*(\d+)", text)
        if math_match:
            return str(int(math_match.group(1)) + int(math_match.group(2)))

        return None

    def _solve_checkbox(self, html: str) -> Optional[str]:
        """Solve checkbox CAPTCHA (I'm not a robot)."""
        if "checkbox" in html.lower() or "i am not a robot" in html.lower():
            return "click_checkbox"
        return None

    def detect_captcha(self, html: str) -> Dict[str, Any]:
        """Detect CAPTCHA type from HTML."""
        html_lower = html.lower()

        result = {
            "detected": False,
            "type": None,
            "site_key": None,
            "difficulty": "unknown",
        }

        if "recaptcha" in html_lower or "grecaptcha" in html_lower:
            result["detected"] = True
            result["type"] = "recaptcha"
            match = re.search(r'data-sitekey=["\']([^"\']+)["\']', html)
            if match:
                result["site_key"] = match.group(1)
            result["difficulty"] = "hard"  # Hard to solve without external service

        elif "hcaptcha" in html_lower:
            result["detected"] = True
            result["type"] = "hcaptcha"
            result["difficulty"] = "hard"

        elif "math" in html_lower or "calculate" in html_lower:
            result["detected"] = True
            result["type"] = "math"
            result["difficulty"] = "easy"

        elif "captcha" in html_lower:
            result["detected"] = True
            result["type"] = "text"
            result["difficulty"] = "medium"

        elif "cloudflare" in html_lower:
            result["detected"] = True
            result["type"] = "cloudflare"
            result["difficulty"] = "medium"

        return result

    def can_help_with(self, problem: Dict[str, Any]) -> bool:
        """Can help with CAPTCHA problems."""
        problem_type = problem.get("problem_type", "")
        return problem_type in ["captcha", "cloudflare"]

    def provide_help(self, problem: Dict[str, Any]) -> Dict[str, Any]:
        """Provide help with CAPTCHAs."""
        return {
            "suggestions": [
                "Use built-in math CAPTCHA solver",
                "Wait for Cloudflare challenge to complete",
                "Click checkbox CAPTCHA automatically",
            ],
            "techniques": [
                "Regex extraction for math problems",
                "Pattern matching for text CAPTCHAs",
                "Browser automation for Cloudflare",
            ],
        }

    def share_skills(self) -> List[Dict[str, Any]]:
        """Share CAPTCHA-solving skills."""
        return [
            {
                "name": "Math CAPTCHA Solver",
                "category": "captcha",
                "problem_type": "math_captcha",
                "solution": {
                    "method": "regex_math",
                    "operations": ["+", "-", "x", "*"],
                },
                "confidence": 0.8,
            },
            {
                "name": "Cloudflare Challenge Handler",
                "category": "protection",
                "problem_type": "cloudflare",
                "solution": {
                    "method": "wait_and_click",
                    "wait_time": 5,
                },
                "confidence": 0.75,
            },
        ]
