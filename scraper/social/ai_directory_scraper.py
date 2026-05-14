"""
AI Directory Scraper - Scrape and format tools for AI directories.
"""
import json
import re
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class AITool:
    """Standardized AI tool data for directories."""
    name: str = ""
    description: str = ""
    website: str = ""
    logo: str = ""
    pricing: str = ""  # free, freemium, paid
    pricing_details: str = ""
    categories: List[str] = None
    tags: List[str] = None
    features: List[str] = None
    use_cases: List[str] = None
    company: str = ""
    founded: str = ""
    location: str = ""
    twitter: str = ""
    linkedin: str = ""
    github: str = ""
    rating: float = 0.0
    reviews_count: int = 0
    source_url: str = ""

    def __post_init__(self):
        if self.categories is None:
            self.categories = []
        if self.tags is None:
            self.tags = []
        if self.features is None:
            self.features = []
        if self.use_cases is None:
            self.use_cases = []

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)

    def to_csv_row(self) -> Dict:
        """Convert to CSV row."""
        return {
            "name": self.name,
            "description": self.description[:200] if self.description else "",
            "website": self.website,
            "pricing": self.pricing,
            "categories": ", ".join(self.categories),
            "tags": ", ".join(self.tags[:5]),
            "company": self.company,
            "source_url": self.source_url,
        }


class AIDirectoryScraper:
    """
    Scrape AI tools from various directories.
    Outputs standardized format for uploading to other directories.
    """

    # Supported directories
    DIRECTORIES = {
        "theresanaiforthat": "https://theresanaiforthat.com",
        "producthunt": "https://producthunt.com",
        "alternatives": "https://alternatives.co",
        "g2": "https://g2.com",
        "capterra": "https://capterra.com",
    }

    def __init__(self):
        self.tools: List[AITool] = []

    def scrape_from_url(self, url: str) -> List[AITool]:
        """
        Scrape tools from a URL.
        Uses appropriate scraper based on domain.
        """
        if "theresanaiforthat" in url:
            return self._scrape_taaft(url)
        elif "producthunt" in url:
            return self._scrape_producthunt(url)
        else:
            return self._scrape_generic(url)

    def _scrape_taaft(self, url: str) -> List[AITool]:
        """Scrape from There's An AI For That."""
        # Placeholder - site has Cloudflare protection
        return []

    def _scrape_producthunt(self, url: str) -> List[AITool]:
        """Scrape from Product Hunt."""
        from ..modules.anti_detection import RequestSession

        session = RequestSession({})
        response = session.get(url)

        if response.status_code != 200:
            return []

        tools = []
        # Parse HTML and extract tool data
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.text, "lxml")

        # Product Hunt structure
        for product in soup.select("[class*='product']"):
            tool = AITool()
            tool.name = product.select_one("h3, h2") or ""
            tool.description = product.select_one("p") or ""
            tool.source_url = url
            tools.append(tool)

        return tools

    def _scrape_generic(self, url: str) -> List[AITool]:
        """Generic scraper for any directory."""
        from ..modules.anti_detection import RequestSession

        session = RequestSession({})
        response = session.get(url)

        if response.status_code != 200:
            return []

        tools = []
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.text, "lxml")

        # Try common patterns
        for item in soup.select("article, .item, [class*='product'], [class*='tool']"):
            tool = self._extract_tool_from_element(item)
            if tool.name:
                tools.append(tool)

        return tools

    def _extract_tool_from_element(self, element) -> AITool:
        """Extract tool data from an element."""
        tool = AITool()

        # Try to find common fields
        try:
            title = element.select_one("h1, h2, h3, h4, .title, [class*='title']")
            if title:
                tool.name = title.get_text(strip=True)

            desc = element.select_one("p, .description, [class*='desc']")
            if desc:
                tool.description = desc.get_text(strip=True)

            link = element.select_one("a[href]")
            if link:
                href = link.get("href", "")
                if href.startswith("http"):
                    tool.website = href

        except:
            pass

        return tool

    def enrich_from_website(self, tool: AITool) -> AITool:
        """
        Enrich tool data by visiting its website.
        Extracts logo, social links, pricing info.
        """
        if not tool.website:
            return tool

        from ..modules.anti_detection import RequestSession

        session = RequestSession({})
        response = session.get(tool.website)

        if response.status_code != 200:
            return tool

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.text, "lxml")

        # Find logo
        og_image = soup.select_one('meta[property="og:image"]')
        if og_image:
            tool.logo = og_image.get("content", "")

        # Find social links
        for link in soup.select('a[href*="twitter.com"], a[href*="github.com"], a[href*="linkedin.com"]'):
            href = link.get("href", "")
            if "twitter.com" in href:
                tool.twitter = href
            elif "github.com" in href:
                tool.github = href
            elif "linkedin.com" in href:
                tool.linkedin = href

        return tool

    def export_json(self, filepath: str = "data/ai_tools.json"):
        """Export tools to JSON."""
        data = [t.to_dict() for t in self.tools]
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return len(data)

    def export_csv(self, filepath: str = "data/ai_tools.csv"):
        """Export tools to CSV."""
        import csv

        if not self.tools:
            return 0

        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "name", "description", "website", "pricing", "categories",
                "tags", "company", "twitter", "source_url"
            ])
            writer.writeheader()
            for tool in self.tools:
                writer.writerow(tool.to_csv_row())

        return len(self.tools)

    def export_for_directory(self, directory_name: str) -> Dict:
        """
        Export in format required by specific directory.
        """
        exports = {
            "producthunt": self._export_producthunt_format,
            "g2": self._export_g2_format,
            "capterra": self._export_capterra_format,
        }

        if directory_name in exports:
            return exports[directory_name]()
        return {"error": f"Unknown directory: {directory_name}"}

    def _export_producthunt_format(self) -> Dict:
        """Export in Product Hunt format."""
        return {
            "tools": [
                {
                    "name": t.name,
                    "tagline": t.description[:120] if t.description else "",
                    "website": t.website,
                    "categories": t.categories,
                    "topic": t.tags[0] if t.tags else "",
                }
                for t in self.tools
            ]
        }

    def _export_g2_format(self) -> Dict:
        """Export in G2 format."""
        return {
            "products": [
                {
                    "name": t.name,
                    "description": t.description,
                    "website": t.website,
                    "pricing": t.pricing,
                    "categories": t.categories,
                }
                for t in self.tools
            ]
        }

    def _export_capterra_format(self) -> Dict:
        """Export in Capterra format."""
        return {
            "software": [
                {
                    "name": t.name,
                    "description": t.description,
                    "website": t.website,
                    "pricing_model": t.pricing,
                    "categories": t.categories,
                }
                for t in self.tools
            ]
        }


def scrape_ai_directory(
    url: str,
    output_dir: str = "data/ai_tools",
    enrich: bool = False,
) -> List[AITool]:
    """
    Scrape AI tools from directory and save in multiple formats.

    Args:
        url: Directory URL
        output_dir: Output directory
        enrich: Visit each tool's website for more info

    Returns:
        List of scraped tools
    """
    scraper = AIDirectoryScraper()
    tools = scraper.scrape_from_url(url)

    if enrich:
        for tool in tools[:10]:  # Limit to avoid rate limiting
            scraper.tools.append(scraper.enrich_from_website(tool))
    else:
        scraper.tools = tools

    # Export formats
    scraper.export_json(f"{output_dir}/tools.json")
    scraper.export_csv(f"{output_dir}/tools.csv")

    return tools
