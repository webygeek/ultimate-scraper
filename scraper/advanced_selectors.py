"""
Advanced Selectors - XPath, CSS, and text-based extraction.
"""
import re
from typing import List, Optional, Dict, Any, Union
from dataclasses import dataclass
from loguru import logger


@dataclass
class ExtractedItem:
    """An extracted data item."""
    selector: str
    selector_type: str
    value: Any
    attributes: Dict[str, str] = None

    def __post_init__(self):
        if self.attributes is None:
            self.attributes = {}


class XPathSelector:
    """
    XPath selector support for advanced HTML extraction.
    """

    def __init__(self):
        self.lxml_available = self._check_lxml()

    def _check_lxml(self) -> bool:
        try:
            from lxml import etree
            return True
        except ImportError:
            logger.warning("lxml not available for XPath")
            return False

    def select(self, html: str, xpath: str) -> List[str]:
        """Select elements using XPath."""
        if not self.lxml_available:
            return []

        from lxml import etree
        from io import BytesIO

        try:
            parser = etree.HTMLParser
            tree = etree.parse(BytesIO(html.encode()), parser)

            results = tree.xpath(xpath)

            # Convert results to strings
            strings = []
            for elem in results:
                if isinstance(elem, str):
                    strings.append(elem)
                elif hasattr(elem, 'text_content'):
                    strings.append(elem.text_content().strip())
                else:
                    strings.append(str(elem))

            return strings

        except Exception as e:
            logger.debug(f"XPath error: {e}")
            return []

    def select_all(self, html: str, xpath: str) -> List[Dict]:
        """Select elements and return with attributes."""
        if not self.lxml_available:
            return []

        from lxml import etree
        from io import BytesIO

        try:
            parser = etree.HTMLParser
            tree = etree.parse(BytesIO(html.encode()), parser)

            results = tree.xpath(xpath)
            items = []

            for elem in results:
                item = {
                    "text": elem.text_content().strip() if hasattr(elem, 'text_content') else str(elem),
                    "tag": elem.tag if hasattr(elem, 'tag') else "",
                    "attributes": dict(elem.attrib) if hasattr(elem, 'attrib') else {},
                }
                items.append(item)

            return items

        except Exception as e:
            logger.debug(f"XPath error: {e}")
            return []

    # Common XPath patterns
    XPATH_PATTERNS = {
        # Links
        "all_links": "//a[@href]/@href",
        "internal_links": "//a[starts-with(@href, '/')]/@href",
        "external_links": "//a[starts-with(@href, 'http')]/@href",

        # Images
        "all_images": "//img/@src",
        "images_with_alt": "//img[@alt]/@src",

        # Text
        "headings": "//h1//text() | //h2//text() | //h3//text()",
        "paragraphs": "//p//text()",
        "all_text": "//body//text()",

        # Tables
        "table_rows": "//tr",
        "table_headers": "//th//text()",
        "table_cells": "//td//text()",

        # Lists
        "list_items": "//li//text()",

        # Forms
        "inputs": "//input/@name",
        "buttons": "//button//text()",

        # Meta
        "title": "//title/text()",
        "meta_description": "//meta[@name='description']/@content",
        "meta_keywords": "//meta[@name='keywords']/@content",
    }


class AdaptiveSelector:
    """
    Adaptive element tracking - relocates elements after website changes.
    Similar to Scrapling's adaptive parsing.
    """

    def __init__(self):
        self.tracked_elements: Dict[str, Dict] = {}

    def track(self, element_id: str, html: str, selector: str):
        """Track an element for future relocation."""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")
        elem = soup.select_one(selector)

        if elem:
            self.tracked_elements[element_id] = {
                "original_selector": selector,
                "text_hash": self._hash_text(elem.get_text()),
                "position": self._get_position(elem),
                "parent_classes": self._get_parent_classes(elem),
                "sibling_text": self._get_sibling_text(elem),
            }

    def relocate(self, new_html: str, element_id: str) -> Optional[str]:
        """Try to relocate a tracked element in new HTML."""
        from bs4 import BeautifulSoup

        if element_id not in self.tracked_elements:
            return None

        track = self.tracked_elements[element_id]
        soup = BeautifulSoup(new_html, "lxml")

        # Strategy 1: Try original selector
        elem = soup.select_one(track["original_selector"])
        if elem:
            return str(elem)

        # Strategy 2: Try position-based matching
        position = track["position"]
        elements = soup.find_all(True)  # All elements
        if position < len(elements):
            candidate = elements[position]
            if self._hash_text(candidate.get_text()) == track["text_hash"]:
                return str(candidate)

        # Strategy 3: Try parent class matching
        parent_classes = track["parent_classes"]
        if parent_classes:
            for parent_class in parent_classes:
                elems = soup.select(f".{parent_class} *")
                for elem in elems:
                    if self._hash_text(elem.get_text()) == track["text_hash"]:
                        return str(elem)

        # Strategy 4: Try text similarity
        for elem in soup.find_all(True):
            if self._hash_text(elem.get_text()) == track["text_hash"]:
                return str(elem)

        return None

    def _hash_text(self, text: str) -> str:
        """Create a hash of text for comparison."""
        import hashlib
        return hashlib.md5(text.strip().lower().encode()).hexdigest()[:8]

    def _get_position(self, elem) -> int:
        """Get element position in tree."""
        siblings = elem.parent.find_all(True, recursive=False) if elem.parent else []
        return siblings.index(elem) if elem in siblings else 0

    def _get_parent_classes(self, elem) -> List[str]:
        """Get parent element classes."""
        classes = []
        parent = elem.parent
        while parent and len(classes) < 3:
            if parent.get("class"):
                classes.extend(parent.get("class"))
            parent = parent.parent
        return classes[:5]

    def _get_sibling_text(self, elem) -> str:
        """Get text from siblings."""
        siblings = elem.parent.find_all(True, recursive=False) if elem.parent else []
        return " ".join(s.text.strip() for s in siblings[:5] if s != elem)[:100]


class LinkExtractor:
    """
    Advanced link extraction with patterns.
    """

    def __init__(self):
        self.allowed_domains = []
        self.blocked_patterns = [
            r"login", r"signup", r"register", r"signin",
            r"password", r"reset", r"auth", r"logout",
        ]

    def extract_all(self, html: str, base_url: str = "") -> List[Dict]:
        """Extract all links with metadata."""
        from bs4 import BeautifulSoup
        from urllib.parse import urljoin

        soup = BeautifulSoup(html, "lxml")
        links = []

        for a in soup.find_all("a", href=True):
            href = a.get("href", "")

            # Skip blocked patterns
            if any(re.search(p, href.lower()) for p in self.blocked_patterns):
                continue

            # Make absolute
            if base_url and not href.startswith("http"):
                href = urljoin(base_url, href)

            links.append({
                "url": href,
                "text": a.get_text(strip=True),
                "title": a.get("title", ""),
                "rel": a.get("rel", []),
            })

        return links

    def extract_by_pattern(self, html: str, pattern: str) -> List[str]:
        """Extract links matching a regex pattern."""
        links = self.extract_all(html)
        return [l["url"] for l in links if re.search(pattern, l["url"])]

    def extract_same_domain(self, html: str, base_url: str) -> List[Dict]:
        """Extract links from same domain."""
        from urllib.parse import urlparse

        if not base_url:
            return []

        base_domain = urlparse(base_url).netloc
        links = self.extract_all(html, base_url)

        return [
            l for l in links
            if urlparse(l["url"]).netloc == base_domain
        ]


class MediaExtractor:
    """
    Extract images, videos, audio, and documents.
    """

    def extract_images(
        self,
        html: str,
        base_url: str = "",
        min_size: tuple = (50, 50),
    ) -> List[Dict]:
        """Extract all images with metadata."""
        from bs4 import BeautifulSoup
        from urllib.parse import urljoin

        soup = BeautifulSoup(html, "lxml")
        images = []

        for img in soup.find_all("img"):
            src = img.get("src") or img.get("data-src") or ""

            if not src:
                continue

            # Make absolute
            if base_url and not src.startswith("http"):
                src = urljoin(base_url, src)

            # Get dimensions
            width = img.get("width")
            height = img.get("height")

            images.append({
                "url": src,
                "alt": img.get("alt", ""),
                "title": img.get("title", ""),
                "width": int(width) if width and width.isdigit() else None,
                "height": int(height) if height and height.isdigit() else None,
                "loading": img.get("loading", ""),
            })

        return images

    def extract_videos(self, html: str, base_url: str = "") -> List[Dict]:
        """Extract video sources."""
        from bs4 import BeautifulSoup
        from urllib.parse import urljoin

        soup = BeautifulSoup(html, "lxml")
        videos = []

        for video in soup.find_all("video"):
            src = video.get("src", "")
            poster = video.get("poster", "")

            # Find source elements
            sources = [s.get("src", "") for s in video.find_all("source")]

            if base_url:
                src = urljoin(base_url, src) if src else ""
                poster = urljoin(base_url, poster) if poster else ""
                sources = [urljoin(base_url, s) if s else "" for s in sources]

            videos.append({
                "url": src,
                "poster": poster,
                "sources": sources,
                "duration": video.get("duration", ""),
            })

        return videos

    def extract_files(
        self,
        html: str,
        base_url: str = "",
        extensions: List[str] = None,
    ) -> List[Dict]:
        """Extract downloadable files."""
        from bs4 import BeautifulSoup
        from urllib.parse import urljoin

        if extensions is None:
            extensions = ["pdf", "doc", "docx", "xls", "xlsx", "csv", "zip", "rar"]

        soup = BeautifulSoup(html, "lxml")
        files = []

        for a in soup.find_all("a", href=True):
            href = a.get("href", "")
            ext = href.split(".")[-1].lower() if "." in href else ""

            if ext in extensions:
                if base_url and not href.startswith("http"):
                    href = urljoin(base_url, href)

                files.append({
                    "url": href,
                    "filename": href.split("/")[-1],
                    "extension": ext,
                    "size": a.get("download", ""),
                })

        return files


class SelectorBuilder:
    """
    Build optimized CSS/XPath selectors.
    """

    @staticmethod
    def css(selector: str, **attributes) -> str:
        """Build CSS selector with attributes."""
        parts = [selector]

        for attr, value in attributes.items():
            if attr == "class_":
                parts.append(f'.{value}')
            elif attr == "id":
                parts.append(f'#{value}')
            else:
                parts.append(f'[{attr}="{value}"]')

        return "".join(parts)

    @staticmethod
    def xpath(tag: str, **attributes) -> str:
        """Build XPath selector."""
        conditions = []

        for attr, value in attributes.items():
            if attr == "text":
                conditions.append(f'contains(text(), "{value}")')
            elif attr == "class_":
                conditions.append(f'contains(@class, "{value}")')
            elif attr == "id":
                conditions.append(f'@id="{value}"')
            else:
                conditions.append(f'@{attr}="{value}"')

        condition = " and ".join(conditions) if conditions else ""
        return f"//{tag}[{condition}]" if condition else f"//{tag}"

    @staticmethod
    def similar(element_html: str, exclude_attrs: List[str] = None) -> str:
        """Build selector for similar elements."""
        from bs4 import BeautifulSoup

        if exclude_attrs is None:
            exclude_attrs = ["id", "onclick", "data-id"]

        soup = BeautifulSoup(element_html, "lxml")
        elem = soup.find(True)

        if not elem:
            return "*"

        tag = elem.name
        classes = elem.get("class", [])

        # Use tag + first class if available
        if classes:
            safe_class = None
            for c in classes:
                if not any(x in c for x in ["active", "selected", "hover"]):
                    safe_class = c
                    break
            if safe_class:
                return f"{tag}.{safe_class}"

        return tag
