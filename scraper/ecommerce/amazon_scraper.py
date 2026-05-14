"""
Amazon Scraper - Specialized scraper for Amazon.
"""
import re
from typing import Dict, List, Optional
from loguru import logger

from .ecommerce_base import EcommerceScraper, Product


class AmazonScraper(EcommerceScraper):
    """
    Specialized scraper for Amazon.
    """

    def __init__(self, config: Dict = None):
        super().__init__(config)
        self.rate_limit_delay = 5  # Amazon is aggressive

    def get_selectors(self) -> Dict[str, str]:
        """Amazon CSS selectors."""
        return {
            # Product page
            "title": "#productTitle",
            "price": ".a-price .a-offscreen, #priceblock_ourprice, #priceblock_dealprice",
            "original_price": ".a-text-price .a-offscreen, #listPrice",
            "rating": ".a-icon-star .a-icon-alt",
            "review_count": "#acrCustomerReviewText",
            "availability": "#availability span",
            "description": "#productDescription p",
            "brand": "#bylineInfoFeature",
            "features": "#feature-bullets li",
            "images": "#altImages img",
            "asin": "[data-asin]",

            # Search results
            "product_title": "h2.a-size-mini a span",
            "product_price": ".a-price-whole",
            "product_image": ".s-image",
            "product_link": "h2.a-size-mini a",
            "product_rating": ".a-icon-star .a-icon-alt",
        }

    def get_url_patterns(self) -> Dict[str, str]:
        """Amazon URL patterns."""
        return {
            "search": "https://www.amazon.com/s?k={query}",
            "product": "https://www.amazon.com/dp/{asin}",
            "category": "https://www.amazon.com/{category}/b?node={node}",
        }

    def _build_search_url(self, query: str) -> str:
        """Build Amazon search URL."""
        query_encoded = query.replace(" ", "+")
        return f"https://www.amazon.com/s?k={query_encoded}"

    def _parse_product(self, html: str, url: str) -> Optional[Product]:
        """Parse Amazon product page."""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")

        # Extract ASIN
        asin = ""
        asin_match = re.search(r"/dp/([A-Z0-9]{10})", url)
        if asin_match:
            asin = asin_match.group(1)

        # Title
        title = ""
        title_elem = soup.select_one("#productTitle")
        if title_elem:
            title = self.clean_text(title_elem.get_text())

        # Price
        price_str = ""
        price_elem = soup.select_one(".a-price .a-offscreen, #priceblock_ourprice, #priceblock_dealprice")
        if price_elem:
            price_str = price_elem.get_text(strip=True)
        price_data = self.parse_price(price_str)

        # Original price
        orig_price = None
        orig_elem = soup.select_one(".a-text-price .a-offscreen, #listPrice")
        if orig_elem:
            orig_data = self.parse_price(orig_elem.get_text())
            orig_price = orig_data.get("amount")

        # Rating
        rating = None
        rating_elem = soup.select_one(".a-icon-star .a-icon-alt")
        if rating_elem:
            rating = self.parse_rating(rating_elem.get_text())

        # Review count
        review_count = 0
        review_elem = soup.select_one("#acrCustomerReviewText")
        if review_elem:
            review_count = self.parse_review_count(review_elem.get_text())

        # Availability
        availability = ""
        avail_elem = soup.select_one("#availability span")
        if avail_elem:
            availability = self.parse_availability(avail_elem.get_text())

        # Brand
        brand = ""
        brand_elem = soup.select_one("#bylineInfoFeature")
        if brand_elem:
            brand = brand_elem.get_text(strip=True).replace("Brand: ", "")

        # Description
        description = ""
        desc_elem = soup.select_one("#productDescription p")
        if desc_elem:
            description = self.clean_text(desc_elem.get_text())

        # Features/Bullet points
        features = []
        for li in soup.select("#feature-bullets li"):
            text = li.get_text(strip=True)
            if text and "{" not in text:
                features.append(text)
        description = " | ".join(features) if features else description

        # Images
        images = []
        for img in soup.select("#altImages img, #imgTagWrapperId img"):
            src = img.get("src") or img.get("data-old-hires")
            if src and "sprite" not in src:
                images.append(src)

        # Category (breadcrumbs)
        category = ""
        breadcrumbs = soup.select(".a-breadcrumb li")
        if breadcrumbs:
            category = " > ".join(b.get_text(strip=True) for b in breadcrumbs)

        return Product(
            sku=asin,
            name=title,
            price=price_data.get("amount"),
            original_price=orig_price,
            currency=price_data.get("currency", "USD"),
            description=description,
            category=category,
            brand=brand,
            availability=availability,
            rating=rating,
            review_count=review_count,
            images=images,
            url=url,
            source="amazon",
        )

    def _parse_search_results(self, html: str) -> List[Product]:
        """Parse Amazon search results."""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")
        products = []

        # Find product containers
        for div in soup.select("[data-component-type='s-search-result']"):
            try:
                # Get link and ASIN
                link_elem = div.select_one("h2 a")
                if not link_elem:
                    continue

                href = link_elem.get("href", "")
                asin_match = re.search(r"/dp/([A-Z0-9]{10})", href)
                if not asin_match:
                    continue

                asin = asin_match.group(1)
                url = f"https://www.amazon.com/dp/{asin}"

                # Title
                title = link_elem.get_text(strip=True)

                # Price
                price_str = ""
                price_elem = div.select_one(".a-price-whole")
                if price_elem:
                    cents_elem = div.select_one(".a-price-fraction")
                    cents = cents_elem.get_text(strip=True) if cents_elem else "00"
                    price_str = f"${price_elem.get_text(strip=True)}.{cents}"
                price_data = self.parse_price(price_str)

                # Rating
                rating = None
                rating_elem = div.select_one(".a-icon-star .a-icon-alt")
                if rating_elem:
                    rating = self.parse_rating(rating_elem.get_text())

                # Review count
                review_count = 0
                review_elem = div.select_one("span.a-size-small .a-size-base")
                if review_elem:
                    review_count = self.parse_review_count(review_elem.get_text())

                # Image
                image = ""
                img_elem = div.select_one(".s-image")
                if img_elem:
                    image = img_elem.get("src", "")

                # Availability
                avail_elem = div.select_one("[aria-label]")
                availability = ""
                if avail_elem:
                    availability = self.parse_availability(avail_elem.get("aria-label", ""))

                products.append(Product(
                    sku=asin,
                    name=title,
                    price=price_data.get("amount"),
                    original_price=None,
                    currency=price_data.get("currency", "USD"),
                    description="",
                    category="",
                    brand="",
                    availability=availability,
                    rating=rating,
                    review_count=review_count,
                    images=[image] if image else [],
                    url=url,
                    source="amazon",
                ))

            except Exception as e:
                logger.debug(f"Failed to parse product: {e}")
                continue

        return products


class EbayScraper(EcommerceScraper):
    """
    Specialized scraper for eBay.
    """

    def __init__(self, config: Dict = None):
        super().__init__(config)
        self.rate_limit_delay = 3

    def get_selectors(self) -> Dict[str, str]:
        return {
            "title": ".x-item-title__mainTitle span",
            "price": ".x-price-primary span",
            "original_price": ".x-price-was span",
            "description": "#desc_div",
            "seller": ".x-sellercard-info__seller-name",
            "availability": ".d-quantityavailability",
        }

    def get_url_patterns(self) -> Dict[str, str]:
        return {
            "search": "https://www.ebay.com/sch/i.html?_nkw={query}",
            "product": "https://www.ebay.com/itm/{item_id}",
        }

    def _build_search_url(self, query: str) -> str:
        query_encoded = query.replace(" ", "+")
        return f"https://www.ebay.com/sch/i.html?_nkw={query_encoded}"

    def _parse_product(self, html: str, url: str) -> Optional[Product]:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "lxml")

        title_elem = soup.select_one(".x-item-title__mainTitle span")
        title = self.clean_text(title_elem.get_text()) if title_elem else ""

        price_elem = soup.select_one(".x-price-primary span")
        price_str = price_elem.get_text(strip=True) if price_elem else ""
        price_data = self.parse_price(price_str)

        return Product(
            sku="",
            name=title,
            price=price_data.get("amount"),
            original_price=None,
            currency=price_data.get("currency", "USD"),
            description="",
            category="",
            brand="",
            availability="",
            rating=None,
            review_count=0,
            images=[],
            url=url,
            source="ebay",
        )

    def _parse_search_results(self, html: str) -> List[Product]:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "lxml")
        products = []

        for li in soup.select(".s-item"):
            try:
                title_elem = li.select_one(".s-item__title")
                price_elem = li.select_one(".s-item__price")
                link_elem = li.select_one(".s-item__link")

                if title_elem and price_elem:
                    price_data = self.parse_price(price_elem.get_text())
                    products.append(Product(
                        sku="",
                        name=title_elem.get_text(strip=True),
                        price=price_data.get("amount"),
                        original_price=None,
                        currency=price_data.get("currency", "USD"),
                        description="",
                        category="",
                        brand="",
                        availability="",
                        rating=None,
                        review_count=0,
                        images=[],
                        url=link_elem.get("href") if link_elem else "",
                        source="ebay",
                    ))
            except:
                continue

        return products
