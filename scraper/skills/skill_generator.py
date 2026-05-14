"""
Skill Generator - Creates new skills from successfully solved problems.
"""
import json
import re
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional
from urllib.parse import urlparse

from .skill_db import SkillDatabase, Skill
from .problem_analyzer import Problem
from loguru import logger


class SkillGenerator:
    """
    Generates new skills from solved problems.
    Analyzes what worked and creates reusable skill definitions.
    """

    def __init__(self, skill_db: SkillDatabase):
        self.skill_db = skill_db

    def generate_skill_from_solution(
        self,
        problem: Problem,
        solution: Dict[str, Any],
        url: str,
        success: bool,
    ) -> Optional[Skill]:
        """
        Generate a new skill from a successful solution.

        Args:
            problem: The original problem
            solution: The solution that worked (what we changed)
            url: The URL where it worked
            success: Whether the solution was successful

        Returns:
            New Skill object or None
        """
        if not success:
            return None

        skill = Skill()

        # Determine skill properties from solution
        skill.name = self._generate_skill_name(problem, solution, url)
        skill.description = self._generate_description(problem, solution)
        skill.category = self._get_category(solution)
        skill.problem_type = problem.problem_type
        skill.error_keywords = ",".join(problem.keywords[:10])
        skill.tags = self._generate_tags(problem, solution, url)

        # Generate solution info
        skill.solution_type = self._determine_solution_type(solution)
        skill.solution_config = json.dumps(self._extract_solution_config(solution))

        # Domain pattern
        if url:
            skill.site_pattern = self._extract_domain_pattern(url)
            skill.site_pattern_hash = hashlib.md5(skill.site_pattern.encode()).hexdigest()[:16]

        # Signatures
        skill.problem_signature = self._generate_signature(problem)
        skill.response_patterns = ",".join(problem.signatures[:5])

        # Initial metrics
        skill.success_rate = 1.0
        skill.use_count = 1
        skill.success_count = 1
        skill.confidence = 0.6  # Start moderate, increase with use

        skill.created_at = datetime.now().isoformat()
        skill.updated_at = skill.created_at
        skill.last_used_at = skill.created_at

        return skill

    def _generate_skill_name(
        self,
        problem: Problem,
        solution: Dict[str, Any],
        url: str,
    ) -> str:
        """Generate a descriptive name for the skill."""
        parts = []

        # Problem type
        problem_names = {
            "bot_detected": "Bot Detection Bypass",
            "cloudflare": "Cloudflare Challenge",
            "rate_limited": "Rate Limit Handler",
            "captcha": "CAPTCHA Solver",
            "js_required": "JS Render Fix",
            "auth_required": "Auth Handler",
            "empty_content": "Empty Content Fix",
        }
        parts.append(problem_names.get(problem.problem_type, problem.problem_type.replace("_", " ").title()))

        # Domain hint
        if url:
            domain = urlparse(url).netloc
            main_domain = domain.split(".")[-2] if "." in domain else domain
            if main_domain not in ["com", "org", "net", "io"]:
                parts.append(f"for {main_domain}")

        # Solution hint
        solution_hints = {
            "use_browser": "Browser Method",
            "add_delay": "Delayed Approach",
            "rotate_proxy": "Proxy Method",
            "solve_captcha": "Auto-Solve",
        }
        if solution.get("method"):
            parts.append(solution_hints.get(solution["method"], ""))

        return " - ".join(parts) if parts else f"Learned Skill for {problem.problem_type}"

    def _generate_description(
        self,
        problem: Problem,
        solution: Dict[str, Any],
    ) -> str:
        """Generate a description of what this skill does."""
        desc_parts = []

        desc_parts.append(problem.description)

        if solution:
            method = solution.get("method", "custom")
            changes = solution.get("changes", {})

            if "delay" in changes:
                desc_parts.append(f"Applied {changes['delay']}s delay.")
            if "use_browser" in changes:
                desc_parts.append("Used headless browser.")
            if "proxy" in changes:
                desc_parts.append("Rotated proxies.")
            if "solve_captcha" in changes:
                desc_parts.append("Auto-solved CAPTCHA.")

        return " ".join(desc_parts)

    def _generate_tags(
        self,
        problem: Problem,
        solution: Dict[str, Any],
        url: str,
    ) -> str:
        """Generate tags for the skill."""
        tags = set()

        # Add problem keywords
        tags.update(problem.keywords[:5])

        # Add solution method tags
        if solution:
            method = solution.get("method", "")
            tags.add(method)
            tags.update(solution.get("applied_techniques", []))

        # Add domain tags
        if url:
            domain = urlparse(url).netloc
            parts = domain.replace(".com", "").replace(".org", "").replace(".net", "").split(".")
            tags.update(parts[:2])

        return ",".join(list(tags)[:15])

    def _determine_solution_type(self, solution: Dict[str, Any]) -> str:
        """Determine the solution type from solution details."""
        if not solution:
            return "custom"

        changes = solution.get("changes", {})

        type_mapping = {
            "use_browser": "use_browser",
            "browser": "use_browser",
            "headless": "use_browser",
            "delay": "adaptive_delay",
            "wait": "adaptive_delay",
            "proxy": "rotate_proxy",
            "proxies": "rotate_proxy",
            "captcha": "solve_captcha",
            "solve_captcha": "solve_captcha",
            "pagination": "url_param_pagination",
            "json_ld": "json_ld_parser",
            "cloudflare": "cloudflare_wait_and_click",
        }

        for key, value in changes.items():
            if key in type_mapping:
                return type_mapping[key]
            if key in type_mapping.values():
                return key

        return "custom"

    def _extract_solution_config(self, solution: Dict[str, Any]) -> Dict[str, Any]:
        """Extract configuration from solution."""
        config = {}

        if not solution:
            return config

        changes = solution.get("changes", {})

        if "delay" in changes:
            config["delay"] = changes["delay"]

        if "use_browser" in changes or "browser" in changes:
            config["browser_wait"] = changes.get("browser_wait", 3000)
            config["scroll_after_load"] = True

        if "proxy" in changes:
            config["rotate_on_block"] = True

        if "pagination" in changes:
            config["param_name"] = changes.get("pagination_param", "page")
            config["start"] = 1
            config["increment"] = 1

        return config

    def _get_category(self, solution: Dict[str, Any]) -> str:
        """Get category from solution."""
        if not solution:
            return "general"

        changes = solution.get("changes", {})

        if any(k in changes for k in ["use_browser", "browser", "headless"]):
            return "rendering"
        if any(k in changes for k in ["delay", "wait", "rate_limit"]):
            return "rate_limiting"
        if any(k in changes for k in ["proxy", "proxies"]):
            return "proxy"
        if any(k in changes for k in ["captcha", "solve_captcha"]):
            return "captcha"
        if "pagination" in changes:
            return "pagination"

        return "general"

    def _generate_signature(self, problem: Problem) -> str:
        """Generate unique signature for this problem pattern."""
        components = [
            problem.problem_type,
            ",".join(sorted(problem.keywords[:5])),
        ]
        return hashlib.md5("|".join(components).encode()).hexdigest()[:16]

    def _extract_domain_pattern(self, url: str) -> str:
        """Extract domain pattern from URL."""
        domain = urlparse(url).netloc
        # Replace numbers with wildcard pattern
        pattern = re.sub(r'\d+', '*', domain)
        return pattern

    def improve_skill(
        self,
        skill: Skill,
        solution: Dict[str, Any],
        success: bool,
    ) -> Skill:
        """
        Improve an existing skill based on new solution data.

        Updates confidence, success rate, and tags.
        """
        # Update success metrics
        skill.use_count += 1
        if success:
            skill.success_count += 1

        # Calculate new success rate
        skill.success_rate = skill.success_count / skill.use_count

        # Update confidence
        if success:
            # Increase confidence for successful use
            skill.confidence = min(1.0, skill.confidence + 0.1)
        else:
            # Decrease confidence for failure
            skill.confidence = max(0.1, skill.confidence - 0.15)

        # Update tags if new keywords found
        if solution:
            new_tags = solution.get("applied_techniques", [])
            existing_tags = set(skill.tags.split(","))
            existing_tags.update(new_tags)
            skill.tags = ",".join(list(existing_tags)[:15])

        skill.updated_at = datetime.now().isoformat()
        skill.last_used_at = skill.updated_at

        return skill

    def merge_skills(self, skills: list[Skill]) -> Optional[Skill]:
        """
        Merge similar skills into a more general one.

        Used when multiple skills solve similar problems.
        """
        if not skills:
            return None

        if len(skills) == 1:
            return skills[0]

        # Create merged skill
        merged = Skill()
        merged.name = f"Merged Skill ({len(skills)} sources)"
        merged.description = "; ".join(s.description for s in skills[:3])

        # Combine keywords
        all_keywords = set()
        for s in skills:
            all_keywords.update(s.error_keywords.split(","))
        merged.error_keywords = ",".join(list(all_keywords)[:20])

        # Combine tags
        all_tags = set()
        for s in skills:
            all_tags.update(s.tags.split(","))
        merged.tags = ",".join(list(all_tags)[:20])

        # Use highest confidence
        merged.confidence = max(s.confidence for s in skills)

        # Average success rate
        merged.success_rate = sum(s.success_rate for s in skills) / len(skills)

        # Most common problem type
        problem_types = [s.problem_type for s in skills]
        merged.problem_type = max(set(problem_types), key=problem_types.count)

        merged.created_at = datetime.now().isoformat()
        merged.updated_at = merged.created_at

        return merged

    def analyze_and_generate(
        self,
        problem: Problem,
        attempt_log: list,
        url: str,
    ) -> Optional[Skill]:
        """
        Analyze attempt history and generate improved skill.

        Args:
            problem: The problem that was solved
            attempt_log: List of attempts with their solutions
            url: Target URL

        Returns:
            Improved skill or None
        """
        if not attempt_log:
            return None

        # Find successful attempt
        successful = [a for a in attempt_log if a.get("success")]
        if not successful:
            return None

        # Get the successful solution
        best_solution = successful[-1]  # Last successful

        return self.generate_skill_from_solution(
            problem=problem,
            solution=best_solution.get("solution", {}),
            url=url,
            success=True,
        )
