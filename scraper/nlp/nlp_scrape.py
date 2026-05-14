"""
Natural Language Scraping - Prompt-based data extraction.
Like ScrapeGraphAI but self-contained.
"""
import json
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from loguru import logger

from ..modules.browser import BuiltInStealthBrowser
from ..modules.anti_detection import RequestSession


@dataclass
class PromptTemplate:
    """Template for natural language scraping."""
    prompt: str
    schema: Dict[str, Any] = None
    examples: List[Dict] = None

    def format(self, **kwargs) -> str:
        """Format prompt with variables."""
        return self.prompt.format(**kwargs)


class NLPScraper:
    """
    Natural language scraping using LLM.
    Prompts describe what to extract, LLM interprets and extracts.
    """

    # Built-in prompt templates
    TEMPLATES = {
        "products": PromptTemplate(
            prompt="""Extract product information from this webpage.

Look for:
- Product name/title
- Price (current price and original if on sale)
- Description/features
- Images/image URLs
- Reviews/ratings
- Availability
- Brand
- SKU or product ID

Return ONLY valid JSON matching this schema:
{
    "products": [{
        "name": "",
        "price": "",
        "original_price": "",
        "description": "",
        "image_url": "",
        "rating": "",
        "reviews_count": "",
        "in_stock": true/false,
        "brand": ""
    }]
}

If no products found, return: {{"products": []}}""",
            schema={"products": "array"}
        ),

        "articles": PromptTemplate(
            prompt="""Extract article/blog post information from this webpage.

Look for:
- Title/headline
- Author name
- Publication date
- Main content/body text
- Summary/excerpt
- Category/tags
- Featured image
- Reading time

Return ONLY valid JSON:
{{
    "article": {{
        "title": "",
        "author": "",
        "published_date": "",
        "content": "",
        "excerpt": "",
        "category": "",
        "tags": [],
        "image_url": "",
        "reading_time": ""
    }}
}}""",
            schema={"article": "object"}
        ),

        "contacts": PromptTemplate(
            prompt="""Extract contact information from this webpage.

Look for:
- Company name
- Email addresses
- Phone numbers
- Physical address
- Social media links
- Contact form URLs

Return ONLY valid JSON:
{{
    "contacts": {{
        "company_name": "",
        "emails": [],
        "phones": [],
        "address": "",
        "social_media": {{
            "twitter": "",
            "linkedin": "",
            "facebook": "",
            "instagram": ""
        }}
    }}
}}""",
            schema={"contacts": "object"}
        ),

        "jobs": PromptTemplate(
            prompt="""Extract job listing information from this webpage.

Look for:
- Job title
- Company name
- Location
- Salary range
- Job description
- Requirements/qualifications
- Benefits
- Posted date
- Job type (full-time, part-time, contract)
- Remote/hybrid info

Return ONLY valid JSON:
{{
    "jobs": [{
        "title": "",
        "company": "",
        "location": "",
        "salary": "",
        "description": "",
        "requirements": [],
        "benefits": [],
        "posted_date": "",
        "job_type": "",
        "remote": ""
    }]
}}""",
            schema={"jobs": "array"}
        ),

        "prices": PromptTemplate(
            prompt="""Extract pricing information from this webpage.

Look for:
- Product/item name
- Current price
- Original price (if discounted)
- Currency
- Discount percentage
- Price history (if available)
- Availability
- Unit pricing (per kg, per liter, etc.)

Return ONLY valid JSON:
{{
    "prices": [{
        "item_name": "",
        "current_price": "",
        "original_price": "",
        "currency": "",
        "discount_percent": "",
        "available": true/false,
        "unit_price": ""
    }]
}}""",
            schema={"prices": "array"}
        ),
    }

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.llm_config = config.get("llm", {})

    def scrape(
        self,
        url: str,
        prompt: str,
        use_browser: bool = False,
        use_llm: bool = True,
    ) -> Dict[str, Any]:
        """
        Scrape using natural language prompt.

        Args:
            url: Target URL
            prompt: What to extract (natural language)
            use_browser: Use browser for JS rendering
            use_llm: Use LLM for extraction (False = simple regex)

        Returns:
            Extracted data as dict
        """
        # Get HTML
        html = self._fetch_html(url, use_browser)
        if not html:
            return {"error": "Failed to fetch page"}

        if use_llm and self._is_llm_available():
            return self._extract_with_llm(html, prompt, url)
        else:
            return self._extract_with_regex(html, prompt)

    def scrape_with_template(
        self,
        url: str,
        template: str,
        **kwargs,
    ) -> Dict[str, Any]:
        """Scrape using a built-in template."""
        if template not in self.TEMPLATES:
            raise ValueError(f"Unknown template: {template}. Available: {list(self.TEMPLATES.keys())}")

        tmpl = self.TEMPLATES[template]
        prompt = tmpl.format(**kwargs)
        return self.scrape(url, prompt)

    def _fetch_html(self, url: str, use_browser: bool) -> str:
        """Fetch HTML from URL."""
        if use_browser:
            browser = BuiltInStealthBrowser(self.config)
            try:
                browser.start()
                html = browser.navigate_and_wait(url)
                return html or ""
            finally:
                browser.close()
        else:
            session = RequestSession(self.config)
            response = session.get(url)
            return response.text

    def _is_llm_available(self) -> bool:
        """Check if LLM is available."""
        provider = self.llm_config.get("provider", "ollama")
        if provider == "ollama":
            try:
                import requests
                base_url = self.llm_config.get("base_url", "http://localhost:11434")
                resp = requests.get(f"{base_url}/api/tags", timeout=5)
                return resp.status_code == 200
            except:
                return False
        return bool(self.llm_config.get("api_key"))

    async def _extract_with_llm(self, html: str, prompt: str, url: str) -> Dict[str, Any]:
        """Extract data using LLM."""
        # Truncate HTML for token limit
        html_short = html[:8000]

        full_prompt = f"""You are a web scraping assistant. Extract structured data from this HTML.

URL: {url}

User Request: {prompt}

HTML Content (first 8000 chars):
```html
{html_short}
```

Extract the requested information and return ONLY valid JSON. No markdown, no explanation, just JSON."""

        provider = self.llm_config.get("provider", "ollama")
        model = self.llm_config.get("model", "llama3")

        if provider == "ollama":
            return await self._query_ollama(full_prompt, model)
        elif provider == "openai":
            return await self._query_openai(full_prompt, model)
        elif provider == "anthropic":
            return await self._query_anthropic(full_prompt, model)

        return {"error": "No LLM configured"}

    async def _query_ollama(self, prompt: str, model: str) -> Dict[str, Any]:
        """Query Ollama."""
        import requests

        base_url = self.llm_config.get("base_url", "http://localhost:11434")

        response = requests.post(
            f"{base_url}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.1, "num_predict": 1000},
            },
            timeout=60,
        )

        if response.status_code != 200:
            return {"error": f"Ollama error: {response.status_code}"}

        text = response.json().get("response", "")
        return self._parse_json_response(text)

    async def _query_openai(self, prompt: str, model: str) -> Dict[str, Any]:
        """Query OpenAI."""
        import requests

        api_key = self.llm_config.get("api_key", "")
        model = model or "gpt-3.5-turbo"

        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "max_tokens": 1000,
            },
            timeout=60,
        )

        if response.status_code != 200:
            return {"error": f"OpenAI error: {response.status_code}"}

        text = response.json()["choices"][0]["message"]["content"]
        return self._parse_json_response(text)

    async def _query_anthropic(self, prompt: str, model: str) -> Dict[str, Any]:
        """Query Anthropic."""
        import requests

        api_key = self.llm_config.get("api_key", "")
        model = model or "claude-3-haiku-20240307"

        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01",
            },
            json={
                "model": model,
                "max_tokens": 1000,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=60,
        )

        if response.status_code != 200:
            return {"error": f"Anthropic error: {response.status_code}"}

        text = response.json()["content"][0]["text"]
        return self._parse_json_response(text)

    def _parse_json_response(self, text: str) -> Dict[str, Any]:
        """Parse JSON from LLM response."""
        # Try to extract JSON from markdown code blocks
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
        if json_match:
            text = json_match.group(1)

        # Try direct JSON
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            pass

        # Try to find JSON-like content
        brace_start = text.find('{')
        brace_end = text.rfind('}') + 1
        if brace_start >= 0 and brace_end > brace_start:
            try:
                return json.loads(text[brace_start:brace_end])
            except:
                pass

        return {"error": "Failed to parse LLM response", "raw": text[:500]}

    def _extract_with_regex(self, html: str, prompt: str) -> Dict[str, Any]:
        """Fallback extraction using regex patterns."""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")
        results = {"extracted": []}

        # Simple pattern matching based on prompt keywords
        prompt_lower = prompt.lower()

        if "email" in prompt_lower:
            emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', html)
            results["emails"] = list(set(emails))

        if "phone" in prompt_lower:
            phones = re.findall(r'\+?1?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', html)
            results["phones"] = phones

        if "price" in prompt_lower:
            prices = re.findall(r'\$[\d,]+\.?\d*', html)
            results["prices"] = prices

        if "title" in prompt_lower or "heading" in prompt_lower:
            titles = [h.get_text(strip=True) for h in soup.find_all(['h1', 'h2', 'h3'])[:10]]
            results["titles"] = titles

        if "link" in prompt_lower or "url" in prompt_lower:
            links = [a.get('href', '') for a in soup.find_all('a', href=True)[:20]]
            results["links"] = links

        if "image" in prompt_lower:
            images = [img.get('src', '') for img in soup.find_all('img')[:20] if img.get('src')]
            results["images"] = images

        return results


class GraphPipeline:
    """
    Graph-based scraping pipelines like ScrapeGraphAI.
    Orchestrates multiple scraping stages.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.nlp = NLPScraper(config)

    async def smart_scraper(
        self,
        url: str,
        prompt: str,
    ) -> Dict[str, Any]:
        """Single page smart scraping."""
        return self.nlp.scrape(url, prompt, use_browser=True)

    async def search_scraper(
        self,
        query: str,
        prompt: str,
        num_results: int = 10,
    ) -> List[Dict[str, Any]]:
        """Scrape search results."""
        # Get search results first
        from ..api_discovery import APIDiscovery

        finder = APIDiscovery(self.config)
        serp_url = f"https://www.google.com/search?q={query}"

        results = []
        try:
            session = RequestSession(self.config)
            response = session.get(serp_url)
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, "lxml")

            # Extract URLs
            urls = []
            for link in soup.select(".yuRUbf a")[:num_results]:
                href = link.get("href", "")
                if href.startswith("http"):
                    urls.append(href)

            # Scrape each URL
            for url in urls:
                try:
                    data = await self.smart_scraper(url, prompt)
                    if data and "error" not in data:
                        results.append({"url": url, "data": data})
                except Exception as e:
                    logger.debug(f"Failed to scrape {url}: {e}")

        except Exception as e:
            logger.error(f"Search scrape failed: {e}")

        return results

    async def multi_scraper(
        self,
        urls: List[str],
        prompt: str,
    ) -> List[Dict[str, Any]]:
        """Scrape multiple URLs in parallel."""
        import asyncio

        async def scrape_one(url):
            return await self.smart_scraper(url, prompt)

        tasks = [scrape_one(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        return [
            {"url": url, "data": r} if not isinstance(r, Exception) else {"url": url, "error": str(r)}
            for url, r in zip(urls, results)
        ]
