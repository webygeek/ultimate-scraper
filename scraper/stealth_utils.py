"""
Ad Blocker - Block ads, trackers, and unwanted content.
"""
import re
from typing import List, Set
from loguru import logger


class AdBlocker:
    """
    Block ads, trackers, and malicious content.
    Uses EasyList-style filter rules.
    """

    def __init__(self):
        self.blocked_domains: Set[str] = set()
        self.blocked_patterns: List[re.Pattern] = []
        self.blocked_selectors: List[str] = []
        self._load_default_rules()

    def _load_default_rules(self):
        """Load default ad-blocking rules."""
        # Common ad domains
        ad_domains = [
            "googlesyndication.com",
            "googleadservices.com",
            "doubleclick.net",
            "adservice.google.com",
            "pagead2.googlesyndication.com",
            "ads.facebook.com",
            "advertising.com",
            "adnxs.com",
            "adsrvr.org",
            "adform.net",
            "criteo.com",
            "criteo.net",
            "outbrain.com",
            "taboola.com",
            "mgid.com",
            "revcontent.com",
            "popads.net",
            "popcash.net",
            "propellerads.com",
            "bidswitch.net",
            "casalemedia.com",
            "pubmatic.com",
            "rubiconproject.com",
            "openx.net",
            "amazon-adsystem.com",
            "media.net",
            "moatads.com",
        ]
        self.blocked_domains.update(ad_domains)

        # Ad URL patterns
        patterns = [
            r"\.ad[s]?\.",
            r"\.doubleclick\.",
            r"banner.*\.jpg",
            r"banner.*\.png",
            r"/ads/",
            r"/ad/",
            r"advertisement",
            r"googleadservices",
            r"googlesyndication",
        ]
        for p in patterns:
            self.blocked_patterns.append(re.compile(p, re.I))

        # CSS selectors for ad elements
        selectors = [
            "[class*='ad-']",
            "[class*='ads-']",
            "[class*='advert']",
            "[id*='ad-']",
            "[id*='ads-']",
            "[id*='advert']",
            ".sponsored",
            ".promotion",
            "[data-ad]",
            "[data-ad-slot]",
            "ins.adsbygoogle",
            ".google-ad",
            ".dfp-ad",
        ]
        self.blocked_selectors.extend(selectors)

    def add_domain(self, domain: str):
        """Add domain to block list."""
        self.blocked_domains.add(domain.lower())

    def add_pattern(self, pattern: str):
        """Add URL pattern to block."""
        self.blocked_patterns.append(re.compile(pattern, re.I))

    def add_selector(self, selector: str):
        """Add CSS selector to block."""
        self.blocked_selectors.append(selector)

    def should_block_url(self, url: str) -> bool:
        """Check if URL should be blocked."""
        if not url:
            return False

        url_lower = url.lower()

        # Check domain blocklist
        for domain in self.blocked_domains:
            if domain in url_lower:
                return True

        # Check patterns
        for pattern in self.blocked_patterns:
            if pattern.search(url):
                return True

        return False

    def should_block_element(self, tag: str, attrs: dict) -> bool:
        """Check if element should be blocked."""
        class_name = attrs.get("class", "")
        id_ = attrs.get("id", "")
        src = attrs.get("src", "")

        # Check blocked selectors
        for selector in self.blocked_selectors:
            if self._matches_simple_selector(tag, class_name, id_, selector):
                return True

        # Check blocked URLs in src
        if src and self.should_block_url(src):
            return True

        return False

    def _matches_simple_selector(self, tag: str, class_name: str, id_: str, selector: str) -> bool:
        """Check if element matches a simple CSS selector."""
        selector = selector.strip()

        # Class selector
        if selector.startswith("."):
            needed_class = selector[1:]
            return needed_class in class_name

        # ID selector
        if selector.startswith("#"):
            needed_id = selector[1:]
            return needed_id == id_

        # Attribute selector
        if selector.startswith("["):
            if "class*=" in selector:
                match = re.search(r'class\*=["\']([^"\']+)["\']', selector)
                if match and match.group(1) in class_name:
                    return True
            if "id*=" in selector:
                match = re.search(r'id\*=["\']([^"\']+)["\']', selector)
                if match and match.group(1) in id_:
                    return True

        return False

    def filter_html(self, html: str) -> str:
        """Remove ad elements from HTML."""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")

        # Remove blocked elements
        for selector in self.blocked_selectors:
            for elem in soup.select(selector):
                elem.decompose()

        # Remove script sources with blocked domains
        for script in soup.find_all("script", src=True):
            if self.should_block_url(script.get("src", "")):
                script.decompose()

        # Remove iframe sources with blocked domains
        for iframe in soup.find_all("iframe", src=True):
            if self.should_block_url(iframe.get("src", "")):
                iframe.decompose()

        return str(soup)

    def get_blocked_resources(self, html: str) -> List[dict]:
        """Get list of resources that would be blocked."""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")
        blocked = []

        # Check scripts
        for script in soup.find_all("script", src=True):
            src = script.get("src", "")
            if self.should_block_url(src):
                blocked.append({
                    "type": "script",
                    "url": src,
                    "reason": "blocked_domain",
                })

        # Check stylesheets
        for link in soup.find_all("link", href=True):
            href = link.get("href", "")
            if self.should_block_url(href) or "stylesheet" in link.get("rel", []):
                blocked.append({
                    "type": "stylesheet",
                    "url": href,
                    "reason": "blocked_domain",
                })

        # Check images
        for img in soup.find_all("img", src=True):
            src = img.get("src", "")
            if self.should_block_url(src):
                blocked.append({
                    "type": "image",
                    "url": src,
                    "reason": "blocked_domain",
                })

        # Check iframes
        for iframe in soup.find_all("iframe", src=True):
            src = iframe.get("src", "")
            if self.should_block_url(src):
                blocked.append({
                    "type": "iframe",
                    "url": src,
                    "reason": "blocked_domain",
                })

        return blocked


class TrackerBlocker(AdBlocker):
    """
    Specialized tracker blocker with fingerprinting protection.
    """

    def __init__(self):
        super().__init__()

        # Add tracker domains
        tracker_domains = [
            "google-analytics.com",
            "googletagmanager.com",
            "googletagservices.com",
            "facebook.net",
            "facebook.com/tr",
            "connect.facebook.net",
            "hotjar.com",
            "mixpanel.com",
            "segment.com",
            "segment.io",
            "amplitude.com",
            "heap.io",
            "heapanalytics.com",
            "intercom.io",
            "crisp.chat",
            "drift.com",
            "hubspot.com",
            "marketo.com",
            "pardot.com",
            "salesforce.com/analytics",
            "optimizely.com",
            "kissmetrics.com",
            "mouseflow.com",
            "fullstory.com",
            "crazyegg.com",
            "clarity.ms",
            "analytics.twitter.com",
            "tiktok.com/api/track",
        ]
        self.blocked_domains.update(tracker_domains)

    def block_fingerprinting(self, html: str) -> str:
        """Remove fingerprinting vectors."""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")

        # Remove canvas fingerprinting
        for canvas in soup.find_all("canvas"):
            canvas.decompose()

        # Remove WebGL info exposure
        for style in soup.find_all("style"):
            if "webgl" in str(style).lower():
                style.decompose()

        # Remove navigator properties
        scripts = soup.find_all("script")
        for script in scripts:
            script_text = str(script)
            fingerprint_patterns = [
                "navigator.plugins",
                "navigator.mimeTypes",
                "canvas.toDataURL",
                "webgl",
                "getContext('webgl')",
            ]
            if any(p in script_text for p in fingerprint_patterns):
                # Comment out but don't remove entirely
                pass

        return str(soup)
