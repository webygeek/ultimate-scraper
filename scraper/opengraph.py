"""
OpenGraph Parser - Extract OpenGraph, Twitter Card, and meta tags.
"""
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from loguru import logger


@dataclass
class OpenGraphData:
    """OpenGraph metadata from a webpage."""
    title: str = ""
    type: str = ""
    url: str = ""
    description: str = ""
    site_name: str = ""
    image: str = ""
    images: List[str] = None
    video: str = ""
    audio: str = ""
    locale: str = ""
    alternate_locales: List[str] = None

    # Article specific
    published_time: str = ""
    modified_time: str = ""
    author: str = ""
    section: str = ""
    tags: List[str] = None

    # Video specific
    video_width: int = 0
    video_height: int = 0
    video_type: str = ""

    # Audio specific
    audio_type: str = ""

    def __post_init__(self):
        if self.images is None:
            self.images = []
        if self.alternate_locales is None:
            self.alternate_locales = []
        if self.tags is None:
            self.tags = []


class TwitterCardData:
    """Twitter Card metadata."""
    card: str = ""
    site: str = ""
    creator: str = ""
    title: str = ""
    description: str = ""
    image: str = ""
    image_alt: str = ""


class OpenGraphParser:
    """
    Extract OpenGraph, Twitter Card, and meta tags from HTML.
    """

    # OpenGraph prefixes
    PREFIXES = ["og", "twitter", "article", "book", "music", "video", "product"]

    def __init__(self):
        self.og_data: OpenGraphData = None
        self.twitter_data: TwitterCardData = None
        self.meta_data: Dict[str, str] = {}
        self.json_ld: List[Dict] = []

    def parse(self, html: str) -> Dict[str, Any]:
        """
        Parse HTML and extract all metadata.

        Returns:
            {
                "opengraph": {...},
                "twitter": {...},
                "meta": {...},
                "json_ld": [...]
            }
        """
        self.og_data = OpenGraphData()
        self.twitter_data = TwitterCardData()
        self.meta_data = {}
        self.json_ld = []

        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")

        # Parse OpenGraph
        self._parse_opengraph(soup)

        # Parse Twitter Cards
        self._parse_twitter(soup)

        # Parse meta tags
        self._parse_meta(soup)

        # Parse JSON-LD
        self._parse_json_ld(soup)

        return {
            "opengraph": self._og_to_dict(),
            "twitter": self._twitter_to_dict(),
            "meta": self.meta_data,
            "json_ld": self.json_ld,
        }

    def parse_url(self, url: str) -> Dict[str, Any]:
        """Fetch and parse a URL."""
        try:
            from ..modules.anti_detection import RequestSession

            session = RequestSession({})
            response = session.get(url)

            if response.status_code == 200:
                return self.parse(response.text)

        except Exception as e:
            logger.error(f"Failed to fetch URL: {e}")

        return {}

    def _parse_opengraph(self, soup):
        """Parse OpenGraph meta tags."""
        for meta in soup.find_all("meta"):
            property_ = meta.get("property", "")
            content = meta.get("content", "")

            if not property_:
                continue

            # Check if it's an OpenGraph tag
            if not any(property_.startswith(f"{prefix}:") for prefix in self.PREFIXES):
                continue

            # Parse property
            parts = property_.split(":")
            if len(parts) < 2:
                continue

            prefix = parts[0]
            key = ":".join(parts[1:])

            # Set values
            if prefix == "og":
                self._set_og_value(key, content)
            elif prefix == "article":
                self._set_article_value(key, content)
            elif prefix == "twitter":
                self._set_twitter_value(key, content)
            elif prefix == "video":
                if key == "image":
                    self.og_data.image = content
                elif key == "url":
                    self.og_data.video = content
            elif prefix == "music":
                if key == "image":
                    self.og_data.image = content

    def _set_og_value(self, key: str, content: str):
        """Set OpenGraph value."""
        if key == "title":
            self.og_data.title = content
        elif key == "type":
            self.og_data.type = content
        elif key == "url":
            self.og_data.url = content
        elif key == "description":
            self.og_data.description = content
        elif key == "site_name":
            self.og_data.site_name = content
        elif key == "image":
            if content:
                self.og_data.images.append(content)
                if not self.og_data.image:
                    self.og_data.image = content
        elif key == "locale":
            self.og_data.locale = content
        elif key == "video":
            self.og_data.video = content
        elif key == "audio":
            self.og_data.audio = content

    def _set_article_value(self, key: str, content: str):
        """Set article-specific OpenGraph value."""
        if key == "published_time":
            self.og_data.published_time = content
        elif key == "modified_time":
            self.og_data.modified_time = content
        elif key == "author":
            self.og_data.author = content
        elif key == "section":
            self.og_data.section = content
        elif key == "tag":
            self.og_data.tags.append(content)

    def _parse_twitter(self, soup):
        """Parse Twitter Card meta tags."""
        for meta in soup.find_all("meta"):
            name = meta.get("name", "")
            content = meta.get("content", "")

            if not name.startswith("twitter:"):
                continue

            key = name.replace("twitter:", "")

            if key == "card":
                self.twitter_data.card = content
            elif key == "site":
                self.twitter_data.site = content
            elif key == "creator":
                self.twitter_data.creator = content
            elif key == "title":
                self.twitter_data.title = content
            elif key == "description":
                self.twitter_data.description = content
            elif key == "image":
                self.twitter_data.image = content
            elif key == "image:alt":
                self.twitter_data.image_alt = content

    def _parse_meta(self, soup):
        """Parse standard meta tags."""
        for meta in soup.find_all("meta"):
            name = meta.get("name", "") or meta.get("property", "")
            content = meta.get("content", "")

            if not name or not content:
                continue

            # Skip OpenGraph/Twitter (already parsed)
            if any(name.startswith(f"{prefix}:") for prefix in self.PREFIXES):
                continue

            # Map common meta tags
            meta_map = {
                "description": "description",
                "keywords": "keywords",
                "author": "author",
                "robots": "robots",
                "generator": "generator",
                "viewport": "viewport",
                "theme-color": "theme_color",
                "color-scheme": "color_scheme",
            }

            if name.lower() in meta_map:
                self.meta_data[meta_map[name.lower()]] = content
            else:
                self.meta_data[name] = content

    def _parse_json_ld(self, soup):
        """Parse JSON-LD structured data."""
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                import json
                data = json.loads(script.string)
                if isinstance(data, dict):
                    self.json_ld.append(data)
                elif isinstance(data, list):
                    self.json_ld.extend(data)
            except:
                pass

    def _og_to_dict(self) -> Dict:
        """Convert OpenGraph data to dict."""
        return {
            "title": self.og_data.title,
            "type": self.og_data.type,
            "url": self.og_data.url,
            "description": self.og_data.description,
            "site_name": self.og_data.site_name,
            "image": self.og_data.image,
            "images": self.og_data.images,
            "video": self.og_data.video,
            "audio": self.og_data.audio,
            "locale": self.og_data.locale,
            "alternate_locales": self.og_data.alternate_locales,
            "published_time": self.og_data.published_time,
            "modified_time": self.og_data.modified_time,
            "author": self.og_data.author,
            "section": self.og_data.section,
            "tags": self.og_data.tags,
        }

    def _twitter_to_dict(self) -> Dict:
        """Convert Twitter data to dict."""
        return {
            "card": self.twitter_data.card,
            "site": self.twitter_data.site,
            "creator": self.twitter_data.creator,
            "title": self.twitter_data.title,
            "description": self.twitter_data.description,
            "image": self.twitter_data.image,
            "image_alt": self.twitter_data.image_alt,
        }

    def get_preview_data(self) -> Dict:
        """Get data needed for social media preview."""
        return {
            "title": self.og_data.title or self.twitter_data.title,
            "description": self.og_data.description or self.twitter_data.description,
            "image": self.og_data.image or self.twitter_data.image,
            "url": self.og_data.url,
            "site_name": self.og_data.site_name,
        }


def parse_opengraph(html: str) -> Dict[str, Any]:
    """
    Convenience function to parse OpenGraph data.

    Args:
        html: HTML content

    Returns:
        Parsed OpenGraph data
    """
    parser = OpenGraphParser()
    return parser.parse(html)


def get_social_preview(url: str) -> Dict[str, str]:
    """
    Get social media preview data from URL.

    Args:
        url: URL to fetch

    Returns:
        Preview data (title, description, image)
    """
    parser = OpenGraphParser()
    data = parser.parse_url(url)
    return data.get("opengraph", {}).get("title", ""), data
