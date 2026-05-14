"""
Clutch.co Scraper - Uses Firecrawl to bypass Cloudflare protection.
"""
import json
import time
from typing import List, Dict, Optional
from pathlib import Path
from bs4 import BeautifulSoup
from loguru import logger


class ClutchScraper:
    """
    Scrape agency data from Clutch.co using Firecrawl.

    Categories supported:
    - SEO Firms
    - Link Building
    - Content Marketing (may be blocked by Cloudflare)
    - Social Media Marketing (may be blocked by Cloudflare)
    - Digital PR

    Setup:
    1. Start Firecrawl: cd c:/tmp/firecrawl && docker compose up -d
    2. Access at http://localhost:3002
    """

    BASE_URL = "https://clutch.co"

    CATEGORIES = {
        "seo": "/seo-firms",
        "link_building": "/seo-firms/link-building",
        "content_marketing": "/content-marketing",
        "social_media": "/social-media-marketing",
        "digital_pr": "/digital-pr",
        "email_marketing": "/email-marketing",
        "public_relations": "/public-relations",
    }

    LOCATIONS = {
        "new_york": "new-york",
        "los_angeles": "los-angeles",
        "chicago": "chicago",
        "san_francisco": "san-francisco",
        "austin": "austin",
        "seattle": "seattle",
        "boston": "boston",
        "miami": "miami",
        "denver": "denver",
        "atlanta": "atlanta",
    }

    def __init__(self, firecrawl_url: str = "http://localhost:3002"):
        self.firecrawl_url = firecrawl_url
        self.session = None

    def _get_session(self):
        """Get or create requests session."""
        if self.session is None:
            import requests
            self.session = requests.Session()
        return self.session

    def _build_url(self, category: str, location: str = None) -> str:
        """Build full URL for category and location."""
        cat_path = self.CATEGORIES.get(category, category)
        if location:
            loc = self.LOCATIONS.get(location, location)
            return f"{self.BASE_URL}{cat_path}/{loc}"
        return f"{self.BASE_URL}{cat_path}"

    def scrape(
        self,
        category: str,
        location: str = "new_york",
        save_to_file: bool = True,
    ) -> List[Dict]:
        """
        Scrape agencies from Clutch.co.

        Args:
            category: Category key (e.g., 'seo', 'link_building')
            location: Location key (e.g., 'new_york', 'los_angeles')
            save_to_file: Save results to JSON file

        Returns:
            List of agency dictionaries
        """
        url = self._build_url(category, location)
        logger.info(f"Scraping: {url}")

        try:
            session = self._get_session()
            response = session.post(
                f"{self.firecrawl_url}/v1/scrape",
                json={"url": url, "formats": ["html"]},
                timeout=120,
            )

            if response.status_code != 200:
                logger.error(f"HTTP Error: {response.status_code}")
                return []

            data = response.json()
            if not data.get("success"):
                logger.error(f"Scraping failed: {data.get('error')}")
                return []

            html = data["data"]["html"]

            # Check if we got actual content
            if len(html) < 10000:
                logger.warning(f"Got minimal HTML ({len(html)} chars) - likely blocked")
                return []

            # Parse HTML
            agencies = self._parse_html(html)

            logger.info(f"Found {len(agencies)} agencies")

            # Save to file
            if save_to_file and agencies:
                filename = f"data/clutch_{category}_{location}.json"
                Path("data").mkdir(exist_ok=True)
                with open(filename, "w", encoding="utf-8") as f:
                    json.dump(agencies, f, indent=2, ensure_ascii=False)
                logger.info(f"Saved to {filename}")

            return agencies

        except Exception as e:
            logger.error(f"Error: {e}")
            return []

    def _parse_html(self, html: str) -> List[Dict]:
        """Parse HTML to extract agency data."""
        soup = BeautifulSoup(html, "lxml")
        providers = soup.select(".provider__main-info")

        agencies = []
        for p in providers:
            agency = {}

            # Name and profile
            name_elem = p.select_one("h3 a")
            if name_elem:
                agency["name"] = name_elem.get_text(strip=True)
                href = name_elem.get("href", "")
                if href.startswith("/"):
                    agency["profile_url"] = f"https://clutch.co{href}"
                else:
                    agency["profile_url"] = href

            # Parent element for additional data
            parent = p.parent
            if parent:
                # Website
                for a in parent.select("a"):
                    href = a.get("href", "")
                    if href and "clutch" not in href and href.startswith("http"):
                        agency["website"] = href
                        break

                # Location
                loc = parent.select_one("[class*='location']")
                if loc:
                    agency["location"] = loc.get_text(strip=True)

                # Min project size
                min_proj = parent.select_one("[class*='min-project']")
                if min_proj:
                    agency["min_project_size"] = min_proj.get_text(strip=True)

            if agency.get("name"):
                agencies.append(agency)

        return agencies

    def scrape_all(
        self,
        categories: List[str] = None,
        location: str = "new_york",
    ) -> Dict[str, List[Dict]]:
        """
        Scrape multiple categories.

        Args:
            categories: List of category keys (default: all)
            location: Location to scrape

        Returns:
            Dict mapping category to list of agencies
        """
        if categories is None:
            categories = list(self.CATEGORIES.keys())

        results = {}
        for cat in categories:
            logger.info(f"Scraping category: {cat}")
            agencies = self.scrape(cat, location)
            results[cat] = agencies
            time.sleep(2)  # Rate limiting

        return results

    def is_firecrawl_running(self) -> bool:
        """Check if Firecrawl is accessible."""
        try:
            session = self._get_session()
            response = session.get(self.firecrawl_url, timeout=5)
            return response.status_code == 200
        except:
            return False


def main():
    """CLI entry point."""
    import sys

    scraper = ClutchScraper()

    print("Checking Firecrawl...")
    if not scraper.is_firecrawl_running():
        print("ERROR: Firecrawl is not running!")
        print("Start it with: cd c:/tmp/firecrawl && docker compose up -d")
        sys.exit(1)

    print("Firecrawl is running!")

    # Scrape categories
    categories = ["seo", "link_building"]

    for cat in categories:
        print(f"\nScraping {cat}...")
        agencies = scraper.scrape(cat, "new_york")
        print(f"Found {len(agencies)} agencies")


if __name__ == "__main__":
    main()
