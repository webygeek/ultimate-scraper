"""
Output utilities - Markdown, Screenshot, Pydantic schema.
"""
import json
import base64
import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from loguru import logger


class MarkdownConverter:
    """
    Convert HTML to clean Markdown for AI/LLM consumption.
    Inspired by Firecrawl's markdown output.
    """

    def __init__(self):
        self.strip_tags = ["script", "style", "nav", "footer", "header", "aside"]
        self.convert_tags = {
            "h1": "# {}",
            "h2": "## {}",
            "h3": "### {}",
            "h4": "#### {}",
            "h5": "##### {}",
            "h6": "###### {}",
            "p": "{}\n",
            "li": "- {}\n",
            "blockquote": "> {}\n",
            "code": "`{}`",
            "pre": "```\n{}\n```\n",
            "a": "[{}]({})",
            "strong": "**{}**",
            "em": "*{}*",
            "hr": "---\n",
        }

    def convert(self, html: str) -> str:
        """Convert HTML to Markdown."""
        from bs4 import BeautifulSoup, NavigableString, Comment

        soup = BeautifulSoup(html, "lxml")

        # Remove unwanted elements
        for tag in self.strip_tags:
            for elem in soup.find_all(tag):
                elem.decompose()

        # Remove comments
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()

        # Convert
        markdown = self._process_element(soup.body or soup)

        # Clean up
        markdown = re.sub(r'\n{3,}', '\n\n', markdown)
        markdown = re.sub(r' {2,}', ' ', markdown)
        markdown = markdown.strip()

        return markdown

    def _process_element(self, elem) -> str:
        """Process a single element recursively."""
        from bs4 import NavigableString

        parts = []

        for child in elem.children:
            if isinstance(child, NavigableString):
                text = str(child).strip()
                if text:
                    parts.append(text)
            else:
                tag_name = child.name.lower() if child.name else ""

                if tag_name == "br":
                    parts.append("\n")
                elif tag_name in self.convert_tags:
                    content = self._process_element(child)
                    if content:
                        pattern = self.convert_tags[tag_name]

                        if tag_name == "a":
                            href = child.get("href", "")
                            parts.append(pattern.format(content, href))
                        elif tag_name == "li":
                            parts.append(pattern.format(content))
                        else:
                            parts.append(pattern.format(content))
                elif tag_name == "div" or tag_name == "span":
                    parts.append(self._process_element(child))

        return " ".join(parts)


class ScreenshotCapture:
    """
    Capture screenshots of pages.
    """

    def capture(
        self,
        url: str,
        config: Dict,
        output_path: Optional[str] = None,
        full_page: bool = False,
    ) -> Dict[str, Any]:
        """
        Capture screenshot of a page.

        Args:
            url: Target URL
            config: Scraper config
            output_path: Path to save screenshot
            full_page: Capture full page or just viewport

        Returns:
            {"success": bool, "path": str, "base64": str}
        """
        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()

                # Navigate
                page.goto(url, timeout=30000)
                page.wait_for_load_state("networkidle")

                # Capture
                if output_path:
                    page.screenshot(path=output_path, full_page=full_page)
                    result = {"success": True, "path": output_path}
                else:
                    # Return base64
                    screenshot_bytes = page.screenshot(full_page=full_page)
                    base64_image = base64.b64encode(screenshot_bytes).decode()
                    result = {"success": True, "base64": base64_image}

                browser.close()
                return result

        except ImportError:
            logger.error("Playwright not installed")
            return {"success": False, "error": "Playwright not installed"}
        except Exception as e:
            logger.error(f"Screenshot failed: {e}")
            return {"success": False, "error": str(e)}

    def capture_element(
        self,
        url: str,
        selector: str,
        config: Dict,
        output_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Capture screenshot of a specific element."""
        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()

                page.goto(url, timeout=30000)
                page.wait_for_selector(selector, timeout=10000)

                element = page.wait_for_selector(selector)
                screenshot_bytes = element.screenshot()

                if output_path:
                    with open(output_path, "wb") as f:
                        f.write(screenshot_bytes)
                    result = {"success": True, "path": output_path}
                else:
                    base64_image = base64.b64encode(screenshot_bytes).decode()
                    result = {"success": True, "base64": base64_image}

                browser.close()
                return result

        except Exception as e:
            logger.error(f"Element screenshot failed: {e}")
            return {"success": False, "error": str(e)}


class PydanticOutput:
    """
    Output structured data with Pydantic validation.
    """

    def __init__(self):
        self.pydantic_available = self._check_pydantic()

    def _check_pydantic(self) -> bool:
        try:
            from pydantic import BaseModel, Field
            return True
        except ImportError:
            logger.warning("Pydantic not installed. Using dict validation only.")
            return False

    def validate(
        self,
        data: Any,
        schema: Dict,
        strict: bool = False,
    ) -> Dict[str, Any]:
        """
        Validate data against a schema.

        Args:
            data: Data to validate
            schema: Schema definition
            strict: Fail on missing fields

        Returns:
            Validated data
        """
        if self.pydantic_available:
            return self._validate_pydantic(data, schema)
        else:
            return self._validate_dict(data, schema, strict)

    def _validate_pydantic(self, data: Any, schema: Dict) -> Dict:
        """Validate using Pydantic."""
        from pydantic import BaseModel, Field, validator

        # Dynamically create model from schema
        fields = {}
        for name, spec in schema.items():
            if isinstance(spec, dict):
                field_type = spec.get("type", "str")
                default = spec.get("default")
                description = spec.get("description", "")

                # Map types
                type_map = {
                    "str": str,
                    "int": int,
                    "float": float,
                    "bool": bool,
                    "list": list,
                    "dict": dict,
                }

                py_type = type_map.get(field_type, str)
                fields[name] = (Optional[py_type], default)
            else:
                fields[name] = (str, None)

        # Create model class
        model_name = f"ScraperSchema"
        Model = type(model_name, (BaseModel,), fields)

        try:
            if isinstance(data, dict):
                return Model(**data).dict()
            elif isinstance(data, list):
                return [Model(**item).dict() for item in data]
            else:
                return data
        except Exception as e:
            logger.warning(f"Pydantic validation failed: {e}")
            return data

    def _validate_dict(self, data: Any, schema: Dict, strict: bool) -> Dict:
        """Validate using simple dict check."""
        if not isinstance(data, dict):
            return data

        validated = {}

        for key, spec in schema.items():
            if isinstance(spec, dict):
                expected_type = spec.get("type", "str")
                default = spec.get("default")

                value = data.get(key, default)

                # Type conversion
                try:
                    if expected_type == "int" and value:
                        value = int(value)
                    elif expected_type == "float" and value:
                        value = float(value)
                    elif expected_type == "bool":
                        value = bool(value)
                except (ValueError, TypeError):
                    value = default

                validated[key] = value
            else:
                validated[key] = data.get(key, spec)

        # Check for missing required fields
        if strict:
            for key, spec in schema.items():
                if isinstance(spec, dict) and spec.get("required"):
                    if key not in data:
                        logger.warning(f"Missing required field: {key}")

        return validated

    def output_with_schema(
        self,
        data: List[Dict],
        schema: Dict,
    ) -> Dict[str, Any]:
        """
        Output data with schema metadata.

        Returns:
            {"data": [...], "schema": {...}, "valid": true}
        """
        validated = [self.validate(item, schema) for item in data]

        return {
            "data": validated,
            "schema": schema,
            "count": len(validated),
        }


class DataCleaner:
    """
    Clean and normalize extracted data.
    """

    @staticmethod
    def clean_text(text: str) -> str:
        """Clean extracted text."""
        if not text:
            return ""

        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)

        # Remove special characters
        text = text.strip()

        return text

    @staticmethod
    def clean_price(price: str) -> Dict[str, Any]:
        """Parse and clean price."""
        if not price:
            return {"amount": None, "currency": "USD"}

        # Extract currency
        currency = "USD"
        currency_map = {
            "$": "USD", "€": "EUR", "£": "GBP",
            "¥": "JPY", "₹": "INR", "A$": "AUD",
        }
        for sym, curr in currency_map.items():
            if sym in price:
                currency = curr
                break

        # Extract amount
        amount_str = re.sub(r'[^\d.]', '', price)
        try:
            amount = float(amount_str)
        except ValueError:
            amount = None

        return {"amount": amount, "currency": currency}

    @staticmethod
    def clean_url(url: str, base_url: str = "") -> str:
        """Clean and normalize URL."""
        if not url:
            return ""

        # Remove fragments
        url = url.split("#")[0]

        # Make absolute
        if base_url and not url.startswith("http"):
            from urllib.parse import urljoin
            url = urljoin(base_url, url)

        return url

    @staticmethod
    def clean_email(email: str) -> str:
        """Validate and clean email."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if re.match(pattern, email.strip()):
            return email.strip().lower()
        return ""

    @staticmethod
    def clean_phone(phone: str) -> str:
        """Clean phone number."""
        digits = re.sub(r'\D', '', phone)
        if len(digits) >= 10:
            return digits[-10:]
        return digits

    @staticmethod
    def clean_date(date_str: str) -> str:
        """Parse and normalize date."""
        from datetime import datetime

        formats = [
            "%Y-%m-%d",
            "%d/%m/%Y",
            "%m/%d/%Y",
            "%B %d, %Y",
            "%b %d, %Y",
        ]

        for fmt in formats:
            try:
                dt = datetime.strptime(date_str.strip(), fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue

        return date_str.strip()
