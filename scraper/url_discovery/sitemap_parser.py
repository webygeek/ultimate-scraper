"""
Sitemap Parser - Parse and discover URLs from XML sitemaps.
"""
import xml.etree.ElementTree as ET
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse
from loguru import logger


@dataclass
class SitemapEntry:
    """An entry from a sitemap."""
    url: str
    lastmod: str = ""
    changefreq: str = ""
    priority: float = 0.0
    images: List[str] = None
    type: str = "url"

    def __post_init__(self):
        if self.images is None:
            self.images = []


class SitemapParser:
    """
    Parse XML sitemaps and sitemap indexes.
    Supports standard sitemaps, video sitemaps, news sitemaps, and image sitemaps.
    """

    # XML namespaces
    NAMESPACES = {
        "sm": "http://www.sitemaps.org/schemas/sitemap/0.9",
        "smi": "http://siocon.com/sitemap-image/1.0",
        "news": "http://www.google.com/schemas/sitemap-news/0.9",
        "video": "http://www.google.com/schemas/sitemap-video/1.1",
        "image": "http://www.google.com/schemas/sitemap-image/1.1",
    }

    def __init__(self):
        self.urls: List[SitemapEntry] = []

    def parse(self, xml_content: str) -> List[SitemapEntry]:
        """
        Parse sitemap XML content.

        Args:
            xml_content: Raw XML string

        Returns:
            List of SitemapEntry objects
        """
        self.urls = []

        try:
            # Remove XML declaration for compatibility
            if xml_content.startswith("<?xml"):
                xml_content = re.sub(r'<\?xml[^?]*\?>', '', xml_content)

            root = ET.fromstring(xml_content)

            # Check if sitemap index
            if root.tag.endswith("sitemapindex"):
                return self._parse_index(root)
            else:
                return self._parse_sitemap(root)

        except ET.ParseError as e:
            logger.error(f"Sitemap parse error: {e}")
            return []

    def parse_url(self, url: str, timeout: int = 30) -> List[SitemapEntry]:
        """
        Fetch and parse a sitemap URL.

        Args:
            url: Sitemap URL
            timeout: Request timeout

        Returns:
            List of SitemapEntry objects
        """
        try:
            import requests

            response = requests.get(url, timeout=timeout)
            response.raise_for_status()

            entries = self.parse(response.text)

            # Set base URL for relative URLs
            for entry in entries:
                if entry.url and not entry.url.startswith("http"):
                    entry.url = urljoin(url, entry.url)

            return entries

        except Exception as e:
            logger.error(f"Failed to fetch sitemap: {e}")
            return []

    def parse_robots_txt(self, robots_url: str) -> List[str]:
        """
        Extract sitemap URLs from robots.txt.

        Args:
            robots_url: URL of robots.txt file

        Returns:
            List of sitemap URLs
        """
        sitemaps = []

        try:
            import requests

            response = requests.get(robots_url, timeout=10)
            response.raise_for_status()

            for line in response.text.split("\n"):
                line = line.strip().lower()
                if line.startswith("sitemap:"):
                    sitemap_url = line.split(":", 1)[1].strip()
                    sitemaps.append(sitemap_url)

        except Exception as e:
            logger.error(f"Failed to fetch robots.txt: {e}")

        return sitemaps

    def discover_sitemaps(self, base_url: str) -> List[str]:
        """
        Discover sitemap URLs for a site.

        Args:
            base_url: Base URL of the website

        Returns:
            List of discovered sitemap URLs
        """
        sitemaps = []

        # Common sitemap locations
        candidates = [
            f"{base_url.rstrip('/')}/sitemap.xml",
            f"{base_url.rstrip('/')}/sitemap_index.xml",
            f"{base_url.rstrip('/')}/wp-sitemap.xml",  # WordPress
            f"{base_url.rstrip('/')}/sitemap-index.xml",
            f"{base_url.rstrip('/')}/sitemap/sitemap.xml",
            f"{base_url.rstrip('/')}/sitemap.xml.gz",
        ]

        for url in candidates:
            try:
                import requests
                response = requests.head(url, timeout=5, allow_redirects=True)
                if response.status_code == 200:
                    sitemaps.append(url)
                    logger.debug(f"Found sitemap: {url}")
            except:
                pass

        # Also check robots.txt
        robots_url = f"{base_url.rstrip('/')}/robots.txt"
        robots_sitemaps = self.parse_robots_txt(robots_url)
        sitemaps.extend(robots_sitemaps)

        return list(set(sitemaps))  # Remove duplicates

    def _parse_index(self, root) -> List[SitemapEntry]:
        """Parse a sitemap index."""
        entries = []

        for sitemap in root.findall("sm:sitemap", self.NAMESPACES):
            if sitemap is None:
                sitemap = root.findall("sitemap")  # No namespace

            if sitemap is not None:
                loc = sitemap.find("sm:loc", self.NAMESPACES)
                if loc is None:
                    loc = sitemap.find("loc")

                if loc is not None and loc.text:
                    entry = SitemapEntry(
                        url=loc.text.strip(),
                        type="sitemap",
                    )

                    # Optional fields
                    lastmod = sitemap.find("sm:lastmod", self.NAMESPACES)
                    if lastmod is None:
                        lastmod = sitemap.find("lastmod")
                    if lastmod is not None:
                        entry.lastmod = lastmod.text or ""

                    entries.append(entry)

        return entries

    def _parse_sitemap(self, root) -> List[SitemapEntry]:
        """Parse a regular sitemap."""
        entries = []

        for url_elem in root.findall("sm:url", self.NAMESPACES):
            if url_elem is None:
                url_elem = root.findall("url")  # No namespace

            if url_elem is not None:
                loc = url_elem.find("sm:loc", self.NAMESPACES)
                if loc is None:
                    loc = url_elem.find("loc")

                if loc is not None and loc.text:
                    entry = SitemapEntry(
                        url=loc.text.strip(),
                    )

                    # Last modified
                    lastmod = url_elem.find("sm:lastmod", self.NAMESPACES)
                    if lastmod is None:
                        lastmod = url_elem.find("lastmod")
                    if lastmod is not None:
                        entry.lastmod = lastmod.text or ""

                    # Change frequency
                    changefreq = url_elem.find("sm:changefreq", self.NAMESPACES)
                    if changefreq is None:
                        changefreq = url_elem.find("changefreq")
                    if changefreq is not None:
                        entry.changefreq = changefreq.text or ""

                    # Priority
                    priority = url_elem.find("sm:priority", self.NAMESPACES)
                    if priority is None:
                        priority = url_elem.find("priority")
                    if priority is not None and priority.text:
                        try:
                            entry.priority = float(priority.text)
                        except ValueError:
                            pass

                    # Images (image sitemap)
                    images = self._parse_images(url_elem)
                    entry.images = images

                    entries.append(entry)

        return entries

    def _parse_images(self, url_elem) -> List[str]:
        """Parse image URLs from sitemap entry."""
        images = []

        # Try different namespaces
        for ns_prefix, ns_uri in self.NAMESPACES.items():
            if "image" in ns_prefix:
                image_elems = url_elem.findall(f".//{{{ns_uri}}}image:loc")
                for img in image_elems:
                    if img.text:
                        images.append(img.text.strip())

        # Try without namespace
        if not images:
            for img in url_elem.findall(".//image:loc"):
                if img.text:
                    images.append(img.text.strip())

        return images

    def get_urls_by_priority(self, min_priority: float = 0.0) -> List[str]:
        """Get URLs filtered by priority."""
        return [e.url for e in self.urls if e.priority >= min_priority]

    def get_urls_by_changefreq(self, freq: str) -> List[str]:
        """Get URLs filtered by change frequency."""
        return [e.url for e in self.urls if e.changefreq == freq]

    def get_recent(self, days: int = 7) -> List[str]:
        """Get URLs modified in the last N days."""
        from datetime import datetime, timedelta

        cutoff = datetime.now() - timedelta(days=days)
        recent = []

        for entry in self.urls:
            if entry.lastmod:
                try:
                    # Try common date formats
                    for fmt in ["%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ"]:
                        try:
                            lastmod = datetime.strptime(entry.lastmod[:10], fmt)
                            if lastmod >= cutoff:
                                recent.append(entry.url)
                            break
                        except ValueError:
                            continue
                except:
                    pass

        return recent


def sitemap_find(base_url: str) -> List[str]:
    """
    Convenience function to find and parse sitemaps.

    Args:
        base_url: Base URL of website

    Returns:
        List of discovered URLs
    """
    parser = SitemapParser()

    # Discover sitemaps
    sitemap_urls = parser.discover_sitemaps(base_url)

    all_urls = []

    # Parse each sitemap
    for sitemap_url in sitemap_urls:
        entries = parser.parse_url(sitemap_url)

        # If it's a sitemap index, parse child sitemaps
        if entries and entries[0].type == "sitemap":
            for entry in entries:
                child_entries = parser.parse_url(entry.url)
                all_urls.extend([e.url for e in child_entries])
        else:
            all_urls.extend([e.url for e in entries])

    return all_urls
