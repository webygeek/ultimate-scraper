"""
Problem Analyzer - Analyzes scraping failures and extracts problem signatures.
"""
import re
import hashlib
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse
from loguru import logger


@dataclass
class Problem:
    """Represents a detected scraping problem."""
    problem_type: str
    severity: str  # "low", "medium", "high", "critical"
    description: str
    evidence: List[str]  # Evidence found in response
    keywords: List[str]
    signatures: List[str]  # For skill matching
    suggested_approach: str = ""

    def to_dict(self) -> dict:
        return {
            "problem_type": self.problem_type,
            "severity": self.severity,
            "description": self.description,
            "evidence": self.evidence,
            "keywords": self.keywords,
            "signatures": self.signatures,
            "suggested_approach": self.suggested_approach,
        }


class ProblemAnalyzer:
    """
    Analyzes HTTP responses and page content to identify scraping problems.
    """

    # Known problem patterns
    BOT_DETECTION_PATTERNS = {
        "pattern": [
            r"access denied",
            r"blocked",
            r"forbidden",
            r"403",
            r"please verify you are a human",
            r"i am not a robot",
            r"unusual traffic",
            r"suspicious activity",
            r"automated requests",
            r"captcha",
        ],
        "severity": "critical",
        "type": "bot_detected",
    }

    CLOUDFLARE_PATTERNS = {
        "pattern": [
            r"cloudflare",
            r"checking your browser",
            r"one more step",
            r"please wait",
            r"ray id",
            r"cf-.*ray",
            r"__cf.*ch.*ku",
        ],
        "severity": "high",
        "type": "cloudflare",
    }

    RATE_LIMIT_PATTERNS = {
        "pattern": [
            r"429",
            r"too many requests",
            r"rate limit",
            r"rate exceeded",
            r"try again later",
            r"slow down",
        ],
        "severity": "high",
        "type": "rate_limited",
    }

    CAPTCHA_PATTERNS = {
        "pattern": [
            r"captcha",
            r"recaptcha",
            r"hcaptcha",
            r"prove you are human",
            r"verify.*human",
            r"security check",
            r"enter the characters",
        ],
        "severity": "high",
        "type": "captcha",
    }

    JS_RENDER_PATTERNS = {
        "pattern": [
            r"<body>\s*</body>",
            r"loading",
            r"spa-init",
            r"ng-app",
            r"react-root",
            r"vue-app",
            r"ember-app",
        ],
        "severity": "medium",
        "type": "js_required",
    }

    AUTH_REQUIRED_PATTERNS = {
        "pattern": [
            r"login",
            r"sign in",
            r"authenticate",
            r"session expired",
            r"please log in",
        ],
        "severity": "high",
        "type": "auth_required",
    }

    EMPTY_CONTENT_PATTERNS = {
        "pattern": [
            r"<html>\s*</html>",
            r"<body>\s*</body>",
            r"no results found",
            r"0 results",
            r"nothing found",
        ],
        "severity": "medium",
        "type": "empty_content",
    }

    ALL_PATTERNS = [
        BOT_DETECTION_PATTERNS,
        CLOUDFLARE_PATTERNS,
        RATE_LIMIT_PATTERNS,
        CAPTCHA_PATTERNS,
        JS_RENDER_PATTERNS,
        AUTH_REQUIRED_PATTERNS,
        EMPTY_CONTENT_PATTERNS,
    ]

    def __init__(self):
        self.current_url = ""
        self.current_domain = ""

    def analyze_response(
        self,
        url: str,
        html: str = "",
        status_code: int = 0,
        headers: dict = None,
        error_message: str = "",
    ) -> Optional[Problem]:
        """
        Analyze a response and identify the problem.

        Args:
            url: The URL that was scraped
            html: Response HTML content
            status_code: HTTP status code
            headers: Response headers
            error_message: Any error message

        Returns:
            Problem object if a problem was detected, None otherwise
        """
        self.current_url = url
        self.current_domain = urlparse(url).netloc
        headers = headers or {}
        html = html or ""

        # Combine all text for analysis
        analysis_text = " ".join([
            html.lower(),
            str(status_code),
            str(headers).lower(),
            error_message.lower(),
        ])

        # Check each pattern category
        for pattern_group in self.ALL_PATTERNS:
            matches = self._check_patterns(analysis_text, pattern_group["pattern"])
            if matches:
                return self._create_problem(
                    pattern_group["type"],
                    pattern_group["severity"],
                    matches,
                    url,
                    html,
                )

        # Check for unknown errors
        if status_code >= 400:
            return Problem(
                problem_type="http_error",
                severity="high" if status_code < 500 else "medium",
                description=f"HTTP {status_code} error",
                evidence=[f"Status code: {status_code}"],
                keywords=[str(status_code)],
                signatures=[f"http_{status_code}"],
            )

        if error_message:
            return Problem(
                problem_type="request_error",
                severity="medium",
                description=error_message[:200],
                evidence=[error_message[:500]],
                keywords=self._extract_keywords(error_message),
                signatures=["request_error"],
            )

        # Check for empty or minimal content
        if len(html) < 500 and "<html" in html.lower():
            return Problem(
                problem_type="minimal_content",
                severity="low",
                description="Response contains minimal content",
                evidence=[f"HTML length: {len(html)}"],
                keywords=["minimal", "short"],
                signatures=["minimal_content"],
            )

        return None

    def _check_patterns(self, text: str, patterns: List[str]) -> List[str]:
        """Check which patterns match in the text."""
        matches = []
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                matches.append(pattern)
        return matches

    def _create_problem(
        self,
        problem_type: str,
        severity: str,
        matched_patterns: List[str],
        url: str,
        html: str,
    ) -> Problem:
        """Create a Problem object with all relevant information."""
        evidence = matched_patterns.copy()

        # Add domain info
        evidence.append(f"Domain: {self.current_domain}")

        # Add specific evidence based on problem type
        if problem_type == "cloudflare":
            evidence.extend(self._extract_cloudflare_evidence(html))
        elif problem_type == "rate_limited":
            evidence.extend(self._extract_rate_limit_evidence(html, headers))
        elif problem_type == "captcha":
            evidence.extend(self._extract_captcha_evidence(html))

        # Generate keywords for skill matching
        keywords = self._generate_keywords(problem_type, matched_patterns, url)

        # Generate signatures
        signatures = self._generate_signatures(problem_type, url, matched_patterns)

        # Get suggested approach
        approach = self._get_suggested_approach(problem_type, html)

        return Problem(
            problem_type=problem_type,
            severity=severity,
            description=self._get_problem_description(problem_type),
            evidence=evidence[:10],  # Limit evidence
            keywords=keywords,
            signatures=signatures,
            suggested_approach=approach,
        )

    def _extract_cloudflare_evidence(self, html: str) -> List[str]:
        """Extract Cloudflare-specific evidence."""
        evidence = []
        if "checking your browser" in html.lower():
            evidence.append("Browser check challenge detected")
        if re.search(r"ray.?id", html, re.IGNORECASE):
            match = re.search(r"ray.?id[:\s]*([a-z0-9]+)", html, re.IGNORECASE)
            if match:
                evidence.append(f"Ray ID: {match.group(1)[:16]}")
        if re.search(r"(__cf_|cf_|cloudflare)", html.lower()):
            evidence.append("Cloudflare cookies expected")
        return evidence

    def _extract_rate_limit_evidence(self, html: str, headers: dict) -> List[str]:
        """Extract rate limit evidence."""
        evidence = []
        if "retry-after" in headers:
            evidence.append(f"Retry-After: {headers['retry-after']}")
        retry_match = re.search(r"retry.?after[:\s]*(\d+)", html, re.IGNORECASE)
        if retry_match:
            evidence.append(f"Server suggested retry: {retry_match.group(1)}s")
        return evidence

    def _extract_captcha_evidence(self, html: str) -> List[str]:
        """Extract CAPTCHA evidence."""
        evidence = []
        if "data-sitekey" in html:
            match = re.search(r'data-sitekey=["\']([^"\']+)["\']', html)
            if match:
                evidence.append(f"Site key found: {match.group(1)[:32]}...")
        if "grecaptcha" in html:
            evidence.append("Google reCAPTCHA detected")
        if "hcaptcha" in html:
            evidence.append("hCaptcha detected")
        return evidence

    def _generate_keywords(
        self,
        problem_type: str,
        matched_patterns: List[str],
        url: str,
    ) -> List[str]:
        """Generate keywords for skill matching."""
        keywords = [problem_type]

        # Add domain keywords
        domain_parts = self.current_domain.split(".")
        if len(domain_parts) >= 2:
            keywords.append(domain_parts[-2])  # e.g., "google" from "google.com"

        # Add matched pattern keywords
        for pattern in matched_patterns:
            words = re.findall(r"[a-z]+", pattern.lower())
            keywords.extend(words[:3])

        # Remove duplicates and return
        return list(set(keywords))[:20]

    def _generate_signatures(
        self,
        problem_type: str,
        url: str,
        matched_patterns: List[str],
    ) -> List[str]:
        """Generate unique signatures for this problem."""
        signatures = [problem_type]

        # Domain-based signature
        domain_hash = hashlib.md5(self.current_domain.encode()).hexdigest()[:8]
        signatures.append(f"{problem_type}_{domain_hash}")

        # URL pattern signature
        url_path = urlparse(url).path
        if url_path:
            path_hash = hashlib.md5(url_path.encode()).hexdigest()[:8]
            signatures.append(f"{problem_type}_{path_hash}")

        return signatures

    def _get_problem_description(self, problem_type: str) -> str:
        """Get human-readable description of problem type."""
        descriptions = {
            "bot_detected": "Bot detection triggered - site identified automated access",
            "cloudflare": "Cloudflare protection challenge detected",
            "rate_limited": "Rate limit exceeded - too many requests",
            "captcha": "CAPTCHA challenge detected",
            "js_required": "JavaScript rendering required for content",
            "auth_required": "Authentication required",
            "empty_content": "Content is empty or minimal",
            "http_error": "HTTP error occurred",
            "request_error": "Request failed",
        }
        return descriptions.get(problem_type, f"Unknown problem: {problem_type}")

    def _get_suggested_approach(self, problem_type: str, html: str) -> str:
        """Get suggested approach for this problem."""
        approaches = {
            "bot_detected": "Use headless browser with stealth mode, rotate proxies, add delays",
            "cloudflare": "Wait for challenge completion, use browser automation",
            "rate_limited": "Increase delay between requests, use proxies, wait for cooldown",
            "captcha": "Solve CAPTCHA automatically if simple, or prompt user",
            "js_required": "Switch to browser automation (Playwright)",
            "auth_required": "Implement authentication or use session cookies",
            "empty_content": "Check if JavaScript is needed, try alternative URL patterns",
            "http_error": "Retry with backoff, check if URL is valid",
        }

        # Check if we can solve simple CAPTCHAs
        if problem_type == "captcha":
            if self._can_solve_simple_captcha(html):
                return "SIMPLE_SOLVE: Try built-in simple CAPTCHA solver"

        return approaches.get(problem_type, "Try alternative scraping approach")

    def _can_solve_simple_captcha(self, html: str) -> bool:
        """Check if this is a simple CAPTCHA we can solve."""
        # Simple math CAPTCHA
        if re.search(r"what is \d+ [\+\-\*x] \d+", html, re.IGNORECASE):
            return True

        # Simple text CAPTCHA
        if "enter the letters" in html.lower() or "type the characters" in html.lower():
            # Check if it's not heavily distorted
            if "distorted" not in html.lower() and "complex" not in html.lower():
                return True

        return False

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract meaningful keywords from text."""
        # Remove common words
        stop_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
            "of", "with", "by", "from", "as", "is", "was", "are", "were", "be",
            "been", "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "should", "could", "may", "might", "must", "can", "this",
            "that", "these", "those", "i", "you", "he", "she", "it", "we", "they",
        }

        words = re.findall(r"[a-z]+", text.lower())
        keywords = [w for w in words if len(w) > 3 and w not in stop_words]

        return list(set(keywords))[:10]

    def detect_problem_type_from_html(self, html: str) -> str:
        """Quick detection of problem type from HTML alone."""
        html_lower = html.lower()

        checks = [
            ("cloudflare", ["cloudflare", "checking your browser"]),
            ("captcha", ["captcha", "recaptcha", "prove you are human"]),
            ("bot_detected", ["access denied", "blocked", "forbidden"]),
            ("rate_limited", ["429", "too many requests"]),
            ("js_required", ["<body> </body>", "loading"]),
        ]

        for problem_type, patterns in checks:
            if any(p in html_lower for p in patterns):
                return problem_type

        return "unknown"
