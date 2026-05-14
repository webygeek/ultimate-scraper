"""
Self-Evolving Scraper - Uses learned skills to adapt to challenges.
"""
import json
import time
from typing import Dict, List, Optional, Any, Callable
from urllib.parse import urlparse
from loguru import logger

from .skills.scraper_skills import (
    ScraperSkillsDB,
    ScrapingTechnique,
    WebsiteProfile,
    init_skills_db,
    DEFAULT_TECHNIQUES,
)


class ChallengeDetector:
    """Detect what challenge is blocking scraping."""

    CLOUD_FLARE_SIGNATURES = [
        "Just a moment...",
        "Checking your browser",
        "Cloudflare",
        "Attention Required",
        "cf-challenge",
    ]

    ANTI_BOT_SIGNATURES = [
        "Access Denied",
        "Forbidden",
        "403",
        "blocked",
        "bot detected",
        "suspicious activity",
    ]

    LAZY_LOAD_SIGNATURES = [
        "loading",
        "show more",
        "load more",
        "infinite",
        "pagination",
    ]

    def detect(self, html: str, title: str = "", status_code: int = 200) -> Dict[str, Any]:
        """Detect challenges in the response."""
        challenges = {
            "cloudflare": False,
            "antibot": False,
            "lazy_load": False,
            "requires_auth": False,
            "captcha": False,
            "rate_limited": False,
        }

        content = html + title

        # Check for Cloudflare
        for sig in self.CLOUD_FLARE_SIGNATURES:
            if sig.lower() in content.lower():
                challenges["cloudflare"] = True

        # Check for anti-bot
        if status_code == 403 or status_code == 429:
            challenges["antibot"] = True
        for sig in self.ANTI_BOT_SIGNATURES:
            if sig.lower() in content.lower():
                challenges["antibot"] = True

        # Check for captcha
        if "captcha" in content.lower() or "verify" in content.lower():
            if "human" in content.lower():
                challenges["captcha"] = True

        # Rate limiting
        if status_code == 429:
            challenges["rate_limited"] = True

        return challenges


class EvolutionStrategy:
    """Strategies for overcoming challenges."""

    STRATEGIES = {
        "cloudflare": [
            {
                "name": "Stealth Browser",
                "technique_type": "bypass",
                "method": "playwright_stealth",
                "wait_time": 15,
            },
            {
                "name": "Rotate User Agent",
                "technique_type": "bypass",
                "method": "ua_rotate",
                "wait_time": 5,
            },
            {
                "name": "Wait and Retry",
                "technique_type": "retry",
                "method": "wait_retry",
                "wait_time": 30,
            },
        ],
        "antibot": [
            {
                "name": "Proxy Rotation",
                "technique_type": "proxy",
                "method": "proxy_rotate",
                "wait_time": 10,
            },
            {
                "name": "Stealth Mode",
                "technique_type": "bypass",
                "method": "stealth_mode",
                "wait_time": 10,
            },
            {
                "name": "Human Behavior",
                "technique_type": "bypass",
                "method": "human_behavior",
                "wait_time": 15,
            },
        ],
        "lazy_load": [
            {
                "name": "Scroll Pattern",
                "technique_type": "browser",
                "method": "scroll_pattern",
                "wait_time": 20,
            },
            {
                "name": "Click Load More",
                "technique_type": "browser",
                "method": "click_load_more",
                "wait_time": 10,
            },
            {
                "name": "API Discovery",
                "technique_type": "api",
                "method": "api_intercept",
                "wait_time": 5,
            },
        ],
        "captcha": [
            {
                "name": "Wait and Retry",
                "technique_type": "retry",
                "method": "wait_retry",
                "wait_time": 60,
            },
        ],
    }

    @classmethod
    def get_strategy(cls, challenge: str) -> List[Dict]:
        """Get strategies for a challenge."""
        return cls.STRATEGIES.get(challenge, [])


class SelfEvolvingScraper:
    """
    Self-evolving scraper that learns from challenges.
    """

    def __init__(self, db_path: str = "data/scraper_skills.db"):
        self.db = init_skills_db(db_path)
        self.detector = ChallengeDetector()
        self.strategy = EvolutionStrategy()

    def detect_challenges(self, html: str, title: str = "", status_code: int = 200) -> Dict[str, Any]:
        """Detect challenges in response."""
        return self.detector.detect(html, title, status_code)

    def get_techniques(self, domain: str) -> List[ScrapingTechnique]:
        """Get learned techniques for a domain."""
        return self.db.get_techniques_for_website(domain)

    def save_technique(
        self,
        domain: str,
        challenge: str,
        technique_type: str,
        method: str,
        code_snippet: str = "",
        success: bool = True,
        tags: List[str] = None,
    ):
        """Save a technique that worked or failed."""
        technique = ScrapingTechnique(
            name=f"{method} for {challenge}",
            description=f"Technique to overcome {challenge}",
            website=domain,
            website_domain=domain,
            technique_type=technique_type,
            method=method,
            code_snippet=code_snippet,
            challenge=challenge,
            solution=f"Used {method}",
            success_rate=1.0 if success else 0.0,
            tags=tags or [challenge, technique_type],
        )
        self.db.add_technique(technique)

    def evolve(
        self,
        website: str,
        challenges: Dict[str, bool],
        current_method: str,
        success: bool,
    ) -> Optional[str]:
        """
        Evolve strategy based on challenges and results.
        Returns next technique to try.
        """
        domain = urlparse(website).netloc

        # Log this evolution attempt
        self.db.log_evolution(
            website=domain,
            challenge=json.dumps(challenges),
            attempts=1,
            technique=current_method,
            success=success,
        )

        if success:
            # Save this technique as working
            for challenge, detected in challenges.items():
                if detected:
                    self.save_technique(
                        domain=domain,
                        challenge=challenge,
                        technique_type="browser",
                        method=current_method,
                        success=True,
                    )

            # Update website profile
            profile = self.db.get_website_profile(domain)
            if profile:
                profile.best_method = current_method
                profile.best_success_rate = 1.0
                profile.working_techniques.append(current_method)
                profile.test_count += 1
                self.db.update_website_profile(profile)
            return None

        # Find next technique to try
        for challenge, detected in challenges.items():
            if detected:
                strategies = self.strategy.get_strategy(challenge)
                for i, strategy in enumerate(strategies):
                    if strategy["method"] != current_method:
                        # Save failed technique
                        self.save_technique(
                            domain=domain,
                            challenge=challenge,
                            technique_type=strategy["technique_type"],
                            method=strategy["method"],
                            success=False,
                        )
                        return strategy["method"]

        return None

    def get_best_approach(self, website: str) -> Optional[str]:
        """Get the best known approach for a website."""
        domain = urlparse(website).netloc
        techniques = self.db.get_techniques_for_website(domain)

        # Find highest success rate technique
        best = None
        best_rate = 0
        for t in techniques:
            if t.success_rate > best_rate and t.success_rate > 0.5:
                best = t
                best_rate = t.success_rate

        return best.method if best else None

    def learn_from_attempt(
        self,
        website: str,
        method: str,
        challenges: Dict[str, bool],
        success: bool,
        data_extracted: int = 0,
    ):
        """Learn from a scraping attempt."""
        domain = urlparse(website).netloc

        # Check if this website has a profile
        profile = self.db.get_website_profile(domain)
        if not profile:
            profile = WebsiteProfile(domain=domain)
            profile.created_at = datetime.now().isoformat()

        # Update profile
        profile.last_tested = datetime.now().isoformat()
        profile.test_count += 1

        for challenge, detected in challenges.items():
            if detected:
                if challenge == "cloudflare":
                    profile.has_cloudflare = True
                elif challenge == "antibot":
                    profile.has_antibot = True
                elif challenge == "lazy_load":
                    profile.uses_lazy_load = True

        if success:
            profile.best_method = method
            profile.best_success_rate = min(profile.best_success_rate + 0.1, 1.0)
            if method not in profile.working_techniques:
                profile.working_techniques.append(method)
        else:
            if method not in profile.failed_techniques:
                profile.failed_techniques.append(method)
            profile.best_success_rate = max(profile.best_success_rate - 0.1, 0)

        self.db.update_website_profile(profile)

        # Save technique
        for challenge, detected in challenges.items():
            if detected:
                self.save_technique(
                    domain=domain,
                    challenge=challenge,
                    technique_type="browser",
                    method=method,
                    success=success,
                    tags=[challenge, "evolved"],
                )

    def get_suggestions(self, domain: str) -> List[str]:
        """Get technique suggestions for a domain."""
        suggestions = []

        # Check website profile
        profile = self.db.get_website_profile(domain)
        if profile:
            if profile.has_cloudflare:
                suggestions.append("Use stealth browser mode for Cloudflare")
            if profile.has_antibot:
                suggestions.append("Try proxy rotation")
            if profile.uses_lazy_load:
                suggestions.append("Use scroll pattern to trigger lazy loading")

        # Get working techniques
        techniques = self.db.get_techniques_for_website(domain)
        working = [t for t in techniques if t.success_rate > 0.7]
        if working:
            suggestions.append(f"Previously worked: {working[0].method}")

        return suggestions

    def get_stats(self) -> Dict:
        """Get evolution statistics."""
        return self.db.get_stats()


def create_self_evolving_scraper(db_path: str = "data/scraper_skills.db") -> SelfEvolvingScraper:
    """Create a self-evolving scraper."""
    return SelfEvolvingScraper(db_path)
