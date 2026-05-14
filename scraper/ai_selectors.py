"""
AI Selector Generator
Generates CSS selectors using AI or heuristics.
"""
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from loguru import logger


@dataclass
class SelectorCandidate:
    """A potential CSS selector."""
    selector: str
    confidence: float
    specificity: int
    field_name: str


class SelectorGenerator:
    """
    Generates CSS selectors for data extraction.
    Uses pattern recognition and heuristics.
    """

    def __init__(self):
        # Common patterns for different data types
        self.patterns = {
            "title": [
                "h1", "h2", "[class*='title']", "[class*='heading']",
                "[class*='name']", "[id*='title']", ".title", "#title",
            ],
            "price": [
                "[class*='price']", "[class*='cost']", "[class*='amount']",
                "[id*='price']", ".price", "[data-price]", "[itemprop='price']",
            ],
            "description": [
                "p", "[class*='desc']", "[class*='text']", "[class*='content']",
                "[class*='summary']", ".description", "article p",
            ],
            "image": [
                "img", "[class*='image']", "[class*='photo']", "[class*='picture']",
                "[class*='thumbnail']", "picture img", "[data-src]",
            ],
            "url": [
                "a", "a[href]", "[class*='link']", "[class*='url']",
            ],
            "rating": [
                "[class*='rating']", "[class*='star']", "[class*='review']",
                "[itemprop='rating']", ".stars", "[data-rating]",
            ],
            "date": [
                "[class*='date']", "[class*='time']", "[class*='posted']",
                "[datetime]", "[itemprop='datePublished']",
            ],
            "author": [
                "[class*='author']", "[class*='by']", "[class*='writer']",
                "[rel='author']", "[itemprop='author']", ".author",
            ],
        }

    def generate_from_examples(
        self,
        html_samples: List[str],
        target_fields: Dict[str, str],
    ) -> Dict[str, str]:
        """
        Generate selectors from HTML examples and field names.

        Args:
            html_samples: List of HTML snippets
            target_fields: Dict mapping field names to example values

        Returns:
            Dict mapping field names to generated selectors
        """
        selectors = {}

        for field_name, example_value in target_fields.items():
            selector = self._find_selector_for_value(html_samples, example_value)
            if selector:
                selectors[field_name] = selector
                logger.info(f"Generated selector for '{field_name}': {selector}")

        return selectors

    def generate_from_labels(
        self,
        html: str,
        labels: List[str],
    ) -> Dict[str, str]:
        """
        Generate selectors based on field labels.

        Args:
            html: HTML content
            labels: List of label texts to find

        Returns:
            Dict mapping labels to selectors
        """
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")
        selectors = {}

        for label_text in labels:
            selector = self._find_field_for_label(soup, label_text)
            if selector:
                selectors[label_text] = selector

        return selectors

    def _find_selector_for_value(
        self,
        samples: List[str],
        value: str,
    ) -> Optional[str]:
        """Find selector that matches a specific value."""
        from bs4 import BeautifulSoup

        # Clean value
        value_clean = re.sub(r'\s+', ' ', value).strip()[:100]

        for sample in samples:
            try:
                soup = BeautifulSoup(sample, "lxml")

                # Search for exact text match
                for elem in soup.find_all(string=re.compile(re.escape(value_clean), re.I)):
                    parent = elem.parent
                    if parent:
                        selector = self._element_to_selector(parent)
                        if selector:
                            return selector

            except Exception:
                continue

        # Fall back to pattern matching
        for field_type, patterns in self.patterns.items():
            for pattern in patterns:
                if self._pattern_matches_value(samples, pattern, value):
                    return pattern

        return None

    def _find_field_for_label(self, soup, label_text: str) -> Optional[str]:
        """Find the input/element associated with a label."""
        # Try <label> with for attribute
        label = soup.find("label", string=re.compile(label_text, re.I))
        if label and label.get("for"):
            input_id = label["for"]
            return f"#{input_id}, [id='{input_id}']"

        # Try <label> containing input
        label = soup.find("label", string=re.compile(label_text, re.I))
        if label:
            input_elem = label.find(["input", "select", "textarea"])
            if input_elem:
                return self._element_to_selector(input_elem)

        # Try adjacent elements
        for elem in soup.find_all(string=re.compile(label_text, re.I)):
            # Check for input after label
            sibling = elem.find_next_sibling()
            if sibling and sibling.name in ["input", "select", "textarea"]:
                return self._element_to_selector(sibling)

            # Check for parent form group
            parent = elem.find_parent(["div", "span", "p"])
            if parent:
                input_elem = parent.find(["input", "select", "textarea"])
                if input_elem:
                    return self._element_to_selector(input_elem)

        return None

    def _element_to_selector(self, elem) -> str:
        """Convert BeautifulSoup element to CSS selector."""
        if not elem:
            return ""

        parts = []

        # Tag name
        tag = elem.name
        if tag:
            parts.append(tag)

        # ID
        if elem.get("id"):
            parts.append(f"#{elem['id']}")
            return " ".join(reversed(parts))

        # Class
        classes = elem.get("class", [])
        if classes:
            class_str = ".".join(c for c in classes if c)
            parts.append(f".{class_str}")

        return " ".join(parts) or tag

    def _pattern_matches_value(
        self,
        samples: List[str],
        pattern: str,
        value: str,
    ) -> bool:
        """Check if a pattern matches a value in samples."""
        from bs4 import BeautifulSoup

        for sample in samples:
            try:
                soup = BeautifulSoup(sample, "lxml")
                elems = soup.select(pattern)

                for elem in elems:
                    elem_text = elem.get_text(strip=True)
                    if value.lower() in elem_text.lower():
                        return True

            except Exception:
                continue

        return False

    def generate_from_page_structure(
        self,
        html: str,
        container_selector: str,
    ) -> Dict[str, str]:
        """
        Generate selectors by analyzing page structure.

        Args:
            html: HTML content
            container_selector: Selector for item container

        Returns:
            Dict of generated selectors
        """
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")
        containers = soup.select(container_selector)

        if not containers:
            return {}

        container = containers[0]
        selectors = {}

        # Analyze children
        children = list(container.children)

        # Common patterns
        patterns = [
            ("title", ["h1", "h2", "h3", "[class*='title']", "[class*='name']"]),
            ("description", ["p", "[class*='desc']", "[class*='text']"]),
            ("price", ["[class*='price']", "[class*='cost']"]),
            ("image", ["img", "[class*='image']"]),
            ("url", ["a[href]"]),
        ]

        for field_name, field_patterns in patterns:
            for pattern in field_patterns:
                elems = container.select(pattern)
                if elems:
                    first = elems[0]
                    selector = self._element_to_selector(first)
                    if selector:
                        selectors[field_name] = selector
                        break

        return selectors

    def improve_selector(
        self,
        selector: str,
        html: str,
        expected_values: List[str],
    ) -> str:
        """
        Improve a selector to be more specific.

        Args:
            selector: Current selector
            html: HTML content
            expected_values: Values that should be matched

        Returns:
            Improved selector
        """
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")

        try:
            elems = soup.select(selector)
        except Exception:
            return selector

        if not elems:
            return selector

        # Check if we match expected values
        matched = 0
        for elem in elems:
            text = elem.get_text(strip=True)
            for value in expected_values:
                if value.lower() in text.lower():
                    matched += 1
                    break

        # If too broad, try to narrow down
        if len(elems) > len(expected_values) * 2:
            # Try adding specificity
            for elem in elems[:5]:
                parent = elem.parent
                if parent and parent.get("class"):
                    new_selector = f"{self._element_to_selector(parent)} {selector}"
                    try:
                        new_elems = soup.select(new_selector)
                        if len(new_elems) <= len(expected_values):
                            return new_selector
                    except:
                        pass

        return selector


class AISelectorGenerator:
    """
    AI-powered selector generation using LLM.
    Falls back to heuristic generation if no LLM available.
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.heuristic = SelectorGenerator()

        # LLM settings
        self.llm_config = config.get("llm", {}) if config else {}
        self.provider = self.llm_config.get("provider", "ollama")
        self.model = self.llm_config.get("model", "llama3")
        self.base_url = self.llm_config.get("base_url", "http://localhost:11434")

    def _is_llm_available(self) -> bool:
        """Check if LLM is available."""
        if self.provider != "ollama":
            return False

        try:
            import requests
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except:
            return False

    async def generate_selectors(
        self,
        html: str,
        field_names: List[str],
        examples: Dict[str, str] = None,
    ) -> Dict[str, str]:
        """
        Generate selectors using AI.

        Args:
            html: HTML content
            field_names: Names of fields to extract
            examples: Optional examples for each field

        Returns:
            Dict mapping field names to CSS selectors
        """
        # Try LLM first
        if self._is_llm_available():
            try:
                return await self._generate_with_llm(html, field_names, examples)
            except Exception as e:
                logger.warning(f"LLM selector generation failed: {e}")

        # Fall back to heuristics
        logger.info("Using heuristic selector generation")
        return self._generate_heuristic(html, field_names, examples)

    async def _generate_with_llm(
        self,
        html: str,
        field_names: List[str],
        examples: Dict[str, str],
    ) -> Dict[str, str]:
        """Generate selectors using LLM."""
        import requests

        # Truncate HTML for prompt
        html_short = html[:5000]

        prompt = f"""Analyze this HTML and generate CSS selectors for the following fields:

Fields to extract: {', '.join(field_names)}

Examples:
{json.dumps(examples, indent=2) if examples else 'None provided'}

HTML (first 5000 chars):
```html
{html_short}
```

Generate CSS selectors that will correctly select the data for each field.
Return as JSON:
{{
    "field_name": "css.selector",
    ...
}}

Rules:
- Use specific selectors (e.g., ".product-title" not just "h2")
- Avoid very generic selectors
- Consider class names that match the field purpose
- If a field has multiple possible selectors, pick the most specific one
"""

        response = requests.post(
            f"{self.base_url}/api/generate",
            json={
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.3, "num_predict": 500},
            },
            timeout=60,
        )

        if response.status_code != 200:
            raise Exception(f"LLM error: {response.status_code}")

        result = response.json()
        text = result.get("response", "")

        # Parse JSON from response
        try:
            # Find JSON in response
            json_match = re.search(r'\{[^{}]*\}', text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except Exception as e:
            logger.debug(f"Failed to parse LLM response: {e}")

        return {}

    def _generate_heuristic(
        self,
        html: str,
        field_names: List[str],
        examples: Dict[str, str],
    ) -> Dict[str, str]:
        """Generate selectors using heuristics."""
        selectors = {}

        for field in field_names:
            field_lower = field.lower()

            # Direct match
            if field_lower in self.heuristic.patterns:
                patterns = self.heuristic.patterns[field_lower]
                for pattern in patterns:
                    if pattern in html:
                        selectors[field] = pattern
                        break

            # Semantic match
            if field not in selectors:
                for pattern_type, patterns in self.heuristic.patterns.items():
                    if pattern_type in field_lower or field_lower in pattern_type:
                        for pattern in patterns:
                            if pattern in html:
                                selectors[field] = pattern
                                break

        return selectors


# JSON import for prompt
import json
