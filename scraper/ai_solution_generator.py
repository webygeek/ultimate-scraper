"""
LLM-Powered Solution Generator
Uses AI to generate creative solutions for novel scraping problems.
"""
import json
import time
import random
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from loguru import logger


@dataclass
class Solution:
    """Generated solution from LLM."""
    technique: str
    confidence: float
    explanation: str
    code_snippet: str = ""
    config: Dict[str, Any] = None
    reasoning_steps: List[str] = None

    def __post_init__(self):
        if self.config is None:
            self.config = {}
        if self.reasoning_steps is None:
            self.reasoning_steps = []


class LLMSolutionGenerator:
    """
    Uses LLMs to generate creative solutions for novel scraping problems.
    Supports: Ollama (local), OpenAI, Anthropic, or fallback heuristics.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.llm_config = config.get("llm", {})

        # LLM settings
        self.provider = self.llm_config.get("provider", "ollama")  # ollama, openai, anthropic
        self.model = self.llm_config.get("model", "llama3")
        self.api_key = self.llm_config.get("api_key", "")
        self.base_url = self.llm_config.get("base_url", "http://localhost:11434")

        # Cache for similar problems
        self.solution_cache: Dict[str, Solution] = {}
        self.max_cache_size = 100

        # Known solution patterns (fallback)
        self.known_patterns = self._build_pattern_library()

    def _build_pattern_library(self) -> Dict[str, List[Dict]]:
        """Build library of known solution patterns."""
        return {
            "bot_detected": [
                {
                    "technique": "rotate_user_agent",
                    "confidence": 0.8,
                    "explanation": "Rotate between different user agents",
                    "config": {"rotate_ua": True, "ua_pool_size": 10}
                },
                {
                    "technique": "use_headless_browser",
                    "confidence": 0.9,
                    "explanation": "Use headless browser with stealth mode",
                    "config": {"use_browser": True, "stealth": True}
                },
                {
                    "technique": "add_request_delay",
                    "confidence": 0.7,
                    "explanation": "Add random delays between requests",
                    "config": {"delay": 5, "jitter": 2}
                },
            ],
            "rate_limited": [
                {
                    "technique": "exponential_backoff",
                    "confidence": 0.85,
                    "explanation": "Use exponential backoff for retries",
                    "config": {"initial_delay": 10, "max_delay": 300, "multiplier": 2}
                },
                {
                    "technique": "use_proxy_rotation",
                    "confidence": 0.9,
                    "explanation": "Rotate through proxy pool",
                    "config": {"proxies": [], "rotate_on_limit": True}
                },
            ],
            "captcha": [
                {
                    "technique": "solve_math_captcha",
                    "confidence": 0.8,
                    "explanation": "Solve simple math CAPTCHAs",
                    "config": {"solve_math": True}
                },
                {
                    "technique": "use_browser_automation",
                    "confidence": 0.85,
                    "explanation": "Let browser handle CAPTCHA interaction",
                    "config": {"browser_solve": True}
                },
            ],
            "cloudflare": [
                {
                    "technique": "wait_and_click",
                    "confidence": 0.75,
                    "explanation": "Wait for challenge, click checkbox",
                    "config": {"wait_time": 5, "click_checkbox": True}
                },
                {
                    "technique": "use_browser",
                    "confidence": 0.8,
                    "explanation": "Use headless browser to bypass",
                    "config": {"browser": True, "headless": True}
                },
            ],
            "empty_content": [
                {
                    "technique": "wait_for_js",
                    "confidence": 0.9,
                    "explanation": "Wait for JavaScript to render content",
                    "config": {"wait_selector": "[class*='content']", "timeout": 10000}
                },
                {
                    "technique": "scroll_to_load",
                    "confidence": 0.85,
                    "explanation": "Scroll page to trigger lazy loading",
                    "config": {"scroll_count": 3, "scroll_delay": 1000}
                },
            ],
            "js_required": [
                {
                    "technique": "use_playwright",
                    "confidence": 0.95,
                    "explanation": "Use Playwright for JS rendering",
                    "config": {"browser": "chromium", "headless": True}
                },
            ],
        }

    async def generate_solution(self, problem: Dict[str, Any]) -> Solution:
        """
        Generate a solution for a scraping problem using LLM.
        """
        # Check cache first
        cache_key = self._get_cache_key(problem)
        if cache_key in self.solution_cache:
            logger.info("Using cached solution")
            return self.solution_cache[cache_key]

        # Try LLM if available
        if self._is_llm_available():
            try:
                solution = await self._generate_with_llm(problem)
                self._cache_solution(cache_key, solution)
                return solution
            except Exception as e:
                logger.warning(f"LLM generation failed: {e}, using fallback")

        # Fall back to pattern matching
        solution = self._generate_with_patterns(problem)
        self._cache_solution(cache_key, solution)
        return solution

    def _is_llm_available(self) -> bool:
        """Check if LLM is available."""
        if self.provider == "ollama":
            try:
                import requests
                response = requests.get(f"{self.base_url}/api/tags", timeout=5)
                return response.status_code == 200
            except:
                return False
        elif self.provider in ["openai", "anthropic"]:
            return bool(self.api_key)
        return False

    async def _generate_with_llm(self, problem: Dict[str, Any]) -> Solution:
        """Generate solution using LLM."""
        prompt = self._build_prompt(problem)

        if self.provider == "ollama":
            return await self._query_ollama(prompt)
        elif self.provider == "openai":
            return await self._query_openai(prompt)
        elif self.provider == "anthropic":
            return await self._query_anthropic(prompt)

        return self._generate_with_patterns(problem)

    def _build_prompt(self, problem: Dict[str, Any]) -> str:
        """Build prompt for LLM."""
        return f"""You are a web scraping expert. A scraper is facing this problem:

Problem Type: {problem.get('problem_type', 'unknown')}
URL: {problem.get('url', 'unknown')}
Evidence: {problem.get('evidence', [])}
Keywords: {problem.get('keywords', [])}

Generate a creative solution to overcome this scraping challenge. Consider:
1. Anti-detection techniques
2. Browser automation strategies
3. API discovery approaches
4. Human-like behavior simulation
5. Novel workarounds

Respond with JSON:
{{
    "technique": "name_of_technique",
    "confidence": 0.0-1.0,
    "explanation": "how this technique works",
    "config": {{"key": "value"}},
    "reasoning_steps": ["step1", "step2", "step3"]
}}"""

    async def _query_ollama(self, prompt: str) -> Solution:
        """Query Ollama local LLM."""
        import requests

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "num_predict": 500,
            }
        }

        response = requests.post(
            f"{self.base_url}/api/generate",
            json=payload,
            timeout=60
        )

        if response.status_code != 200:
            raise Exception(f"Ollama error: {response.status_code}")

        result = response.json()
        text = result.get("response", "")

        return self._parse_llm_response(text)

    async def _query_openai(self, prompt: str) -> Solution:
        """Query OpenAI API."""
        import requests

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model or "gpt-3.5-turbo",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": 500,
        }

        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=60
        )

        if response.status_code != 200:
            raise Exception(f"OpenAI error: {response.status_code}")

        result = response.json()
        text = result["choices"][0]["message"]["content"]

        return self._parse_llm_response(text)

    async def _query_anthropic(self, prompt: str) -> Solution:
        """Query Anthropic API."""
        import requests

        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }

        payload = {
            "model": self.model or "claude-3-haiku-20240307",
            "max_tokens": 500,
            "messages": [{"role": "user", "content": prompt}],
        }

        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=payload,
            timeout=60
        )

        if response.status_code != 200:
            raise Exception(f"Anthropic error: {response.status_code}")

        result = response.json()
        text = result["content"][0]["text"]

        return self._parse_llm_response(text)

    def _parse_llm_response(self, text: str) -> Solution:
        """Parse LLM response into Solution object."""
        try:
            # Try to extract JSON from response
            import re
            json_match = re.search(r'\{[^{}]*\}', text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return Solution(
                    technique=data.get("technique", "unknown"),
                    confidence=float(data.get("confidence", 0.5)),
                    explanation=data.get("explanation", ""),
                    config=data.get("config", {}),
                    reasoning_steps=data.get("reasoning_steps", []),
                )
        except Exception as e:
            logger.debug(f"Failed to parse LLM response: {e}")

        # Fallback: extract text-based solution
        return Solution(
            technique="llm_generated",
            confidence=0.5,
            explanation=text[:200],
            reasoning_steps=["LLM generated solution"],
        )

    def _generate_with_patterns(self, problem: Dict[str, Any]) -> Solution:
        """Generate solution using known patterns."""
        problem_type = problem.get("problem_type", "unknown")

        # Get patterns for this problem type
        patterns = self.known_patterns.get(problem_type, [])

        if patterns:
            # Try to find best matching pattern
            keywords = set(problem.get("keywords", []))

            for pattern in patterns:
                # Check keyword overlap
                if keywords:
                    # Higher confidence if keywords match
                    confidence = pattern["confidence"]
                else:
                    confidence = pattern["confidence"] * 0.8

                return Solution(
                    technique=pattern["technique"],
                    confidence=confidence,
                    explanation=pattern["explanation"],
                    config=pattern.get("config", {}),
                    reasoning_steps=[
                        f"Matched problem type: {problem_type}",
                        f"Applied technique: {pattern['technique']}",
                    ],
                )

        # No matching pattern - generate creative fallback
        return self._generate_creative_fallback(problem)

    def _generate_creative_fallback(self, problem: Dict[str, Any]) -> Solution:
        """Generate creative fallback when no pattern matches."""
        problem_type = problem.get("problem_type", "unknown")
        url = problem.get("url", "")

        techniques = []

        # Suggest browser automation for any unknown problem
        techniques.append("Use Playwright headless browser")

        # Suggest rate limiting
        techniques.append("Add randomized delays")

        # Suggest stealth mode
        techniques.append("Enable anti-fingerprinting")

        return Solution(
            technique="multi_strategy_fallback",
            confidence=0.4,  # Low confidence for unknown
            explanation=f"Unknown problem type: {problem_type}. Trying multiple strategies: {', '.join(techniques)}",
            config={
                "use_browser": True,
                "stealth": True,
                "delay": 5,
                "max_retries": 3,
            },
            reasoning_steps=[
                f"Problem type {problem_type} not in pattern library",
                "Applying multi-strategy fallback",
                "Will learn from results",
            ],
        )

    def _get_cache_key(self, problem: Dict[str, Any]) -> str:
        """Generate cache key for problem."""
        import hashlib
        key_parts = [
            problem.get("problem_type", ""),
            problem.get("url", "")[:50],
            ",".join(sorted(problem.get("keywords", [])[:5])),
        ]
        return hashlib.md5("|".join(key_parts).encode()).hexdigest()

    def _cache_solution(self, cache_key: str, solution: Solution) -> None:
        """Cache solution."""
        if len(self.solution_cache) >= self.max_cache_size:
            # Remove random entry
            to_remove = random.choice(list(self.solution_cache.keys()))
            del self.solution_cache[to_remove]

        self.solution_cache[cache_key] = solution

    def learn_from_result(self, problem: Dict[str, Any], solution: Solution, success: bool) -> None:
        """Learn from result to improve future solutions."""
        if success:
            # Add successful technique to patterns
            problem_type = problem.get("problem_type", "unknown")

            new_pattern = {
                "technique": solution.technique,
                "confidence": min(0.95, solution.confidence + 0.1),
                "explanation": solution.explanation,
                "config": solution.config,
            }

            if problem_type in self.known_patterns:
                # Add to existing patterns
                self.known_patterns[problem_type].append(new_pattern)
            else:
                # Create new category
                self.known_patterns[problem_type] = [new_pattern]

            logger.info(f"Learned new technique: {solution.technique}")

    def get_capabilities(self) -> Dict[str, Any]:
        """Get generator capabilities."""
        return {
            "provider": self.provider,
            "model": self.model,
            "llm_available": self._is_llm_available(),
            "cache_size": len(self.solution_cache),
            "patterns_count": sum(len(v) for v in self.known_patterns.values()),
        }
