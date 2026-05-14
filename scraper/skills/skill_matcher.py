"""
Skill Matcher - Finds relevant skills for new problems using fuzzy matching.
"""
import difflib
from typing import List, Optional, Dict, Any
from urllib.parse import urlparse

from .skill_db import SkillDatabase, Skill
from .problem_analyzer import Problem
from loguru import logger


class SkillMatcher:
    """
    Matches problems to existing skills using multiple strategies:
    1. Exact keyword matching
    2. Fuzzy matching
    3. Domain-specific matching
    4. Problem type matching
    """

    def __init__(self, skill_db: SkillDatabase):
        self.skill_db = skill_db

    def find_best_skill(self, problem: Problem, url: str = "") -> Optional[Skill]:
        """
        Find the best matching skill for a problem.

        Args:
            problem: The problem to solve
            url: Optional URL for context

        Returns:
            Best matching Skill or None
        """
        candidates = self.find_candidate_skills(problem, url)
        if not candidates:
            return None

        # Score and rank candidates
        scored = []
        for skill in candidates:
            score = self._calculate_match_score(problem, skill, url)
            scored.append((score, skill))

        # Return highest scoring skill
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[0][1] if scored else None

    def find_candidate_skills(self, problem: Problem, url: str = "") -> List[Skill]:
        """
        Find all candidate skills that might solve this problem.
        """
        candidates = set()

        # 1. Match by problem type
        by_type = self.skill_db.find_skills(problem_type=problem.problem_type)
        candidates.update(by_type)

        # 2. Match by keywords
        for keyword in problem.keywords[:5]:
            by_keywords = self.skill_db.find_by_keywords([keyword], limit=5)
            candidates.update(by_keywords)

        # 3. Match by domain
        if url:
            domain = urlparse(url).netloc
            by_domain = self.skill_db.find_skills(site_pattern=domain)
            candidates.update(by_domain)

        # 4. Match by category
        category = self._get_category_for_problem(problem.problem_type)
        if category:
            by_category = self.skill_db.find_skills(category=category, min_confidence=0.5)
            candidates.update(by_category)

        return list(candidates)

    def _calculate_match_score(self, problem: Problem, skill: Skill, url: str) -> float:
        """
        Calculate match score between problem and skill (0.0 to 1.0).
        """
        score = 0.0

        # Problem type match (highest weight)
        if problem.problem_type == skill.problem_type:
            score += 0.4

        # Keyword overlap
        skill_keywords = set(skill.error_keywords.split(",") + skill.tags.split(","))
        problem_keywords = set(problem.keywords)
        overlap = len(skill_keywords & problem_keywords)
        if skill_keywords:
            score += min(0.2, overlap * 0.05)

        # Domain match (if applicable)
        if url:
            domain = urlparse(url).netloc
            if skill.site_pattern and domain.endswith(skill.site_pattern.replace("*", "")):
                score += 0.2

        # Confidence and success rate
        score += skill.confidence * 0.15
        score += skill.success_rate * 0.15

        # Fuzzy matching on keywords
        for kw in problem.keywords:
            if skill.error_keywords and kw in skill.error_keywords:
                score += 0.05
            if skill.tags and kw in skill.tags:
                score += 0.03

        return min(1.0, score)

    def _get_category_for_problem(self, problem_type: str) -> Optional[str]:
        """Get category for a problem type."""
        mapping = {
            "bot_detected": "anti_detection",
            "cloudflare": "protection",
            "rate_limited": "rate_limiting",
            "captcha": "captcha",
            "js_required": "rendering",
            "auth_required": "authentication",
            "empty_content": "data_extraction",
            "http_error": "network",
        }
        return mapping.get(problem_type)

    def get_solution_config(self, skill: Skill) -> Dict[str, Any]:
        """Get solution configuration from skill."""
        import json
        try:
            return json.loads(skill.solution_config)
        except (json.JSONDecodeError, TypeError):
            return {}

    def should_apply_skill(self, skill: Skill, current_attempts: int) -> bool:
        """
        Determine if we should try this skill based on past attempts.
        """
        # If skill has high confidence, always try
        if skill.confidence >= 0.8:
            return True

        # If we've tried many times without success, try new skills
        if current_attempts >= 3:
            return True

        # Don't retry failed skills
        if skill.success_rate < 0.3:
            return False

        return True


class SkillApplicator:
    """
    Applies a skill's solution to a scraping attempt.
    """

    def __init__(self, config: dict):
        self.config = config

    def apply_skill(
        self,
        skill: Skill,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Apply a skill's solution and return modified context.

        Returns modified context with new configuration.
        """
        solution_type = skill.solution_type
        solution_config = self._get_solution_config(skill)

        if solution_type == "cloudflare_wait_and_click":
            return self._apply_cloudflare_solution(context, solution_config)

        elif solution_type == "adaptive_delay":
            return self._apply_delay_solution(context, solution_config)

        elif solution_type == "math_solver":
            return self._apply_math_solver(context, solution_config)

        elif solution_type == "url_param_pagination":
            return self._apply_pagination_solution(context, solution_config)

        elif solution_type == "use_browser":
            return self._apply_browser_solution(context, solution_config)

        elif solution_type == "json_ld_parser":
            return self._apply_json_ld_solution(context, solution_config)

        elif solution_type == "rotate_proxy":
            return self._apply_proxy_solution(context, solution_config)

        elif solution_type == "solve_captcha":
            return self._apply_captcha_solution(context, solution_config)

        else:
            logger.warning(f"Unknown solution type: {solution_type}")
            return context

    def _get_solution_config(self, skill: Skill) -> Dict[str, Any]:
        """Parse solution configuration."""
        import json
        try:
            return json.loads(skill.solution_config)
        except:
            return {}

    def _apply_cloudflare_solution(
        self,
        context: Dict[str, Any],
        config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Apply Cloudflare bypass solution."""
        context["wait_time"] = config.get("wait_time", 5)
        context["click_checkbox"] = config.get("click_checkbox", True)
        context["use_browser"] = True
        context["stealth_mode"] = True
        context["browser_action"] = "cloudflare_bypass"
        return context

    def _apply_delay_solution(
        self,
        context: Dict[str, Any],
        config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Apply adaptive delay solution."""
        multiplier = config.get("delay_multiplier", 2.0)
        context["delay_multiplier"] = multiplier
        context["max_delay"] = config.get("max_delay", 60)
        context["respect_retry_after"] = True
        return context

    def _apply_math_solver(
        self,
        context: Dict[str, Any],
        config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Apply math CAPTCHA solver."""
        context["solve_math_captcha"] = True
        context["allowed_operations"] = config.get("allowed_ops", ["+", "-", "x", "/"])
        return context

    def _apply_pagination_solution(
        self,
        context: Dict[str, Any],
        config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Apply pagination solution."""
        context["pagination"] = {
            "type": "param",
            "param_name": config.get("param_name", "page"),
            "start": config.get("start", 1),
            "increment": config.get("increment", 1),
            "max_pages": config.get("max_pages", 10),
        }
        return context

    def _apply_browser_solution(
        self,
        context: Dict[str, Any],
        config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Apply browser automation solution."""
        context["use_browser"] = True
        context["browser_wait"] = config.get("browser_wait", 3000)
        context["scroll_after_load"] = config.get("scroll_after_load", True)
        context["stealth_mode"] = True
        return context

    def _apply_json_ld_solution(
        self,
        context: Dict[str, Any],
        config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Apply JSON-LD extraction solution."""
        context["extract_json_ld"] = True
        context["schema_types"] = config.get("schema_types", ["Product", "Article", "Event"])
        return context

    def _apply_proxy_solution(
        self,
        context: Dict[str, Any],
        config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Apply proxy rotation solution."""
        context["use_proxy"] = True
        context["proxy_rotation"] = True
        context["rotate_on_block"] = True
        return context

    def _apply_captcha_solution(
        self,
        context: Dict[str, Any],
        config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Apply CAPTCHA solving solution."""
        context["solve_captcha"] = True
        context["captcha_types"] = config.get("types", ["image", "text"])
        return context
