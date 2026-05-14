"""
LinkedIn Scraper - Specialized scraper for LinkedIn.
"""
import time
import re
from typing import Dict, List, Optional
from loguru import logger


class LinkedInScraper:
    """
    Specialized scraper for LinkedIn.
    Handles LinkedIn's authentication and anti-bot measures.
    """

    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.rate_limit_delay = 3

    async def scrape_profile(self, profile_url: str) -> Dict:
        """
        Scrape a LinkedIn profile.

        Args:
            profile_url: Profile URL

        Returns:
            Profile data
        """
        return await self._scrape_with_browser(profile_url, "profile")

    async def scrape_company(self, company_url: str) -> Dict:
        """
        Scrape a company page.

        Args:
            company_url: Company URL

        Returns:
            Company data
        """
        return await self._scrape_with_browser(company_url, "company")

    async def scrape_jobs(
        self,
        keywords: str,
        location: str = "",
        max_results: int = 25,
    ) -> List[Dict]:
        """
        Scrape job listings.

        Args:
            keywords: Job search keywords
            location: Job location
            max_results: Maximum results

        Returns:
            List of jobs
        """
        # Build URL
        encoded_keywords = keywords.replace(" ", "%20")
        url = f"https://www.linkedin.com/jobs/search/?keywords={encoded_keywords}"

        if location:
            encoded_location = location.replace(" ", "%20")
            url += f"&location={encoded_location}"

        return await self._scrape_jobs(url, max_results)

    async def scrape_company_jobs(
        self,
        company_id: str,
        max_results: int = 25,
    ) -> List[Dict]:
        """
        Scrape jobs from a specific company.

        Args:
            company_id: LinkedIn company ID
            max_results: Maximum results

        Returns:
            List of jobs
        """
        url = f"https://www.linkedin.com/jobs/search/?f_C={company_id}"
        return await self._scrape_jobs(url, max_results)

    async def _scrape_with_browser(self, url: str, scrape_type: str) -> Dict:
        """Scrape using browser."""
        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    viewport={"width": 1280, "height": 720},
                )
                page = context.new_page()

                # Additional headers
                page.set_extra_http_headers({
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                })

                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                time.sleep(5)  # Wait for content to load

                if scrape_type == "profile":
                    result = self._parse_profile(page.content())
                elif scrape_type == "company":
                    result = self._parse_company(page.content())
                else:
                    result = {}

                browser.close()
                return result

        except Exception as e:
            logger.error(f"LinkedIn scrape failed: {e}")
            return {}

    async def _scrape_jobs(self, url: str, max_results: int) -> List[Dict]:
        """Scrape job listings."""
        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                )
                page = context.new_page()

                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                time.sleep(3)

                # Scroll to load more jobs
                for _ in range(3):
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    time.sleep(2)

                html = page.content()
                browser.close()

                return self._parse_jobs(html)[:max_results]

        except Exception as e:
            logger.error(f"LinkedIn jobs scrape failed: {e}")
            return []

    def _parse_profile(self, html: str) -> Dict:
        """Parse profile HTML."""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")
        profile = {
            "name": "",
            "headline": "",
            "location": "",
            "about": "",
            "experience": [],
            "education": [],
            "skills": [],
            "connections": "",
        }

        # Name
        name_elem = soup.find("h1")
        if name_elem:
            profile["name"] = name_elem.get_text(strip=True)

        # Headline
        headline_elem = soup.find("div", {"class": "text-body-medium"})
        if headline_elem:
            profile["headline"] = headline_elem.get_text(strip=True)

        # Location
        for span in soup.find_all("span"):
            if span.get("class") and "tvm__text" in str(span.get("class")):
                text = span.get_text(strip=True)
                if any(x in text.lower() for x in ["usa", "uk", "india", "canada"]):
                    profile["location"] = text
                    break

        # Experience
        exp_section = soup.find("section", {"id": "experience"})
        if exp_section:
            for li in exp_section.find_all("li"):
                exp = {
                    "title": "",
                    "company": "",
                    "duration": "",
                }
                title_elem = li.find("h3")
                if title_elem:
                    exp["title"] = title_elem.get_text(strip=True)
                company_elem = li.find("p")
                if company_elem:
                    exp["company"] = company_elem.get_text(strip=True)
                if exp["title"]:
                    profile["experience"].append(exp)

        return profile

    def _parse_company(self, html: str) -> Dict:
        """Parse company HTML."""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")
        company = {
            "name": "",
            "tagline": "",
            "industry": "",
            "size": "",
            "headquarters": "",
            "description": "",
            "website": "",
        }

        # Name
        name_elem = soup.find("h1")
        if name_elem:
            company["name"] = name_elem.get_text(strip=True)

        # Industry
        for dt in soup.find_all("dt"):
            if "industry" in dt.get_text(strip=True).lower():
                dd = dt.find_next_sibling("dd")
                if dd:
                    company["industry"] = dd.get_text(strip=True)

        # Size
        for dt in soup.find_all("dt"):
            if "company size" in dt.get_text(strip=True).lower():
                dd = dt.find_next_sibling("dd")
                if dd:
                    company["size"] = dd.get_text(strip=True)

        return company

    def _parse_jobs(self, html: str) -> List[Dict]:
        """Parse job listings."""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")
        jobs = []

        # Find job cards
        job_cards = soup.find_all("div", {"class": "job-card-container"})

        for card in job_cards:
            job = {
                "title": "",
                "company": "",
                "location": "",
                "posted": "",
                "url": "",
                "description": "",
            }

            # Title
            title_elem = card.find("h3")
            if title_elem:
                job["title"] = title_elem.get_text(strip=True)

            # Company
            company_elem = card.find("a", {"class": "job-card-container__link"})
            if company_elem:
                job["url"] = "https://linkedin.com" + company_elem.get("href", "")

            # Location
            for span in card.find_all("span"):
                text = span.get_text(strip=True)
                if "," in text and len(text) < 50:
                    job["location"] = text
                    break

            if job["title"]:
                jobs.append(job)

        return jobs
