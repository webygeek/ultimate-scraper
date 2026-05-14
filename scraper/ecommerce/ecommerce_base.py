"""
E-commerce Base Scraper - Common patterns for all e-commerce sites.
"""
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from abc import ABC, abstractmethod
from loguru import logger


@dataclass
class Product:
    """A product."""
    sku: str
    name: str
    price: float
    original_price: Optional[float]
    currency: str
    description: str
    category: str
    brand: str
    availability: str
    rating: Optional[float]
    review_count: int
    images: List[str]
    url: str
    source: str


class EcommerceScraper(ABC):
    """
    Base class for e-commerce scrapers.
    Provides common functionality for all e-commerce sites.
    """

    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.rate_limit_delay = 2

    @abstractmethod
    def get_selectors(self) -> Dict[str, str]:
        """Return CSS selectors for this site."""
        pass

    @abstractmethod
    def get_url_patterns(self) -> Dict[str, str]:
        """Return URL patterns for search, product, category pages."""
        pass

    def parse_price(self, price_str: str) -> Dict[str, Any]:
        """
        Parse price string into amount and currency.

        Returns:
            {"amount": float, "currency": str}
        """
        if not price_str:
            return {"amount": None, "currency": "USD"}

        price_str = price_str.strip()

        # Detect currency
        currency = "USD"
        currency_map = {
            "$": "USD",
            "€": "EUR",
            "£": "GBP",
            "¥": "JPY",
            "₹": "INR",
            "A$": "AUD",
            "C$": "CAD",
        }

        for symbol, curr in currency_map.items():
            if symbol in price_str:
                currency = curr
                price_str = price_str.replace(symbol, "")
                break

        # Extract number
        price_str = re.sub(r"[^\d.,]", "", price_str)
        price_str = price_str.replace(",", "")

        try:
            amount = float(price_str)
        except ValueError:
            amount = None

        return {"amount": amount, "currency": currency}

    def parse_rating(self, rating_str: str) -> Optional[float]:
        """Parse rating string."""
        if not rating_str:
            return None

        # Try to find number
        match = re.search(r"(\d+\.?\d*)", rating_str)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                pass

        return None

    def parse_review_count(self, count_str: str) -> int:
        """Parse review count."""
        if not count_str:
            return 0

        # Handle formats like "1,234" or "1.2K" or "1234"
        count_str = count_str.strip()

        # Remove non-numeric except K, M, k, m
        match = re.search(r"([\d.,]+[KkMm]?)", count_str)
        if match:
            num_str = match.group(1)
            num_str = num_str.replace(",", "")

            if "k" in num_str.lower():
                return int(float(num_str.lower().replace("k", "")) * 1000)
            elif "m" in num_str.lower():
                return int(float(num_str.lower().replace("m", "")) * 1000000)
            else:
                try:
                    return int(float(num_str))
                except ValueError:
                    return 0

        return 0

    def parse_availability(self, avail_str: str) -> str:
        """Parse availability string."""
        avail_str = avail_str.lower().strip()

        if any(x in avail_str for x in ["in stock", "available", "dispatched"]):
            return "in_stock"
        elif any(x in avail_str for x in ["out of stock", "unavailable", "sold out"]):
            return "out_of_stock"
        elif any(x in avail_str for x in ["pre-order", "preorder"]):
            return "pre_order"
        elif "limited" in avail_str:
            return "limited"
        else:
            return "unknown"

    def clean_text(self, text: str) -> str:
        """Clean extracted text."""
        if not text:
            return ""

        # Remove extra whitespace
        text = re.sub(r"\s+", " ", text)

        # Remove special characters but keep punctuation
        text = text.strip()

        return text

    async def scrape_product(self, url: str) -> Optional[Product]:
        """Scrape a single product page."""
        from ..modules.anti_detection import RequestSession

        session = RequestSession(self.config)
        response = session.get(url)

        if response.status_code != 200:
            return None

        return self._parse_product(response.text, url)

    async def scrape_search(
        self,
        query: str,
        max_pages: int = 1,
    ) -> List[Product]:
        """
        Scrape search results.

        Args:
            query: Search query
            max_pages: Maximum pages

        Returns:
            List of products
        """
        from ..modules.anti_detection import RequestSession

        products = []
        search_url = self._build_search_url(query)

        for page in range(1, max_pages + 1):
            url = self._add_page_param(search_url, page)

            session = RequestSession(self.config)
            response = session.get(url)

            if response.status_code == 200:
                page_products = self._parse_search_results(response.text)
                products.extend(page_products)

            import time
            time.sleep(self.rate_limit_delay)

        return products

    async def scrape_category(
        self,
        category_url: str,
        max_pages: int = 1,
    ) -> List[Product]:
        """Scrape category/listing page."""
        from ..modules.anti_detection import RequestSession

        products = []

        for page in range(1, max_pages + 1):
            url = self._add_page_param(category_url, page)

            session = RequestSession(self.config)
            response = session.get(url)

            if response.status_code == 200:
                page_products = self._parse_search_results(response.text)
                products.extend(page_products)

            import time
            time.sleep(self.rate_limit_delay)

        return products

    def _build_search_url(self, query: str) -> str:
        """Build search URL. Override in subclass."""
        return ""

    def _add_page_param(self, url: str, page: int) -> str:
        """Add page parameter to URL. Override in subclass."""
        separator = "&" if "?" in url else "?"
        return f"{url}{separator}page={page}"

    @abstractmethod
    def _parse_product(self, html: str, url: str) -> Optional[Product]:
        """Parse product page HTML. Override in subclass."""
        pass

    @abstractmethod
    def _parse_search_results(self, html: str) -> List[Product]:
        """Parse search results HTML. Override in subclass."""
        pass
