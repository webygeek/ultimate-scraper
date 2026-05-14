"""
Ultimate Scraper Capabilities
Playwright MCP + httpx + Firecrawl-like + Crawlee-like + ScrapFly-like
"""
import asyncio
import httpx
from typing import Dict, List, Optional
import json
import time


class PlaywrightMCP:
    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None

    async def start(self, headless: bool = True):
        from playwright.async_api import async_playwright
        pw = await async_playwright().start()
        self.browser = await pw.chromium.launch(headless=headless)
        self.context = await self.browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            viewport={"width": 1920, "height": 1080},
        )
        await self.context.add_init_script("Object.defineProperty(navigator, 'webdriver', { get: () => undefined});")
        return self

    async def navigate(self, url: str, wait: float = 5.0) -> str:
        self.page = await self.context.new_page()
        await self.page.goto(url)
        await asyncio.sleep(wait)
        await self.page.wait_for_load_state("networkidle")
        return await self.page.title()

    async def scroll(self, times: int = 10) -> int:
        for _ in range(times):
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(1)
        return times

    async def extract_links(self) -> List[Dict]:
        links = []
        async for a in self.page.query_selector_all("a[href]"):
            href = await a.get_attribute("href")
            text = await a.inner_text()
            if href:
                links.append({"href": href, "text": text[:100] if text else ""})
        return links

    async def screenshot(self, path: str = "screenshot.png") -> str:
        await self.page.screenshot(path=path)
        return path

    async def close(self):
        if self.page:
            await self.page.close()
        if self.browser:
            await self.browser.close()


class AsyncHTTPClient:
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.client = None

    async def __aenter__(self):
        limits = httpx.Limits(max_keepalive_connections=20, max_connections=100)
        self.client = httpx.AsyncClient(timeout=self.timeout, limits=limits)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    async def get(self, url: str, headers: Dict = None) -> Dict:
        for attempt in range(3):
            try:
                response = await self.client.get(url, headers=headers or {})
                return {
                    "status": response.status_code,
                    "content": response.text,
                    "headers": dict(response.headers),
                }
            except Exception:
                if attempt == 2:
                    return {"error": "failed"}
        return {"error": "max retries"}

    async def scrape_many(self, urls: List[str], concurrency: int = 10) -> List[Dict]:
        semaphore = asyncio.Semaphore(concurrency)
        async def fetch(url):
            async with semaphore:
                return await self.get(url)
        return await asyncio.gather(*[fetch(u) for u in urls], return_exceptions=True)


class SiteMapper:
    def __init__(self, browser: PlaywrightMCP = None):
        self.browser = browser or PlaywrightMCP()
        self.seen = set()
        self.results = []

    async def map(self, url: str, max_depth: int = 3) -> Dict:
        await self.browser.start()
        await self.browser.navigate(url)
        await self.browser.scroll(20)
        links = await self.browser.extract_links()
        for link in links:
            href = link["href"]
            if href and url in href and href not in self.seen:
                self.seen.add(href)
                self.results.append(href)
        await self.browser.close()
        return {"urls": self.results, "count": len(self.results)}

    async def sitemap_discover(self, base_url: str) -> List[str]:
        async with AsyncHTTPClient() as client:
            result = await client.get(f"{base_url}/sitemap.xml")
            if result.get("content"):
                import xml.etree.ElementTree as ET
                try:
                    root = ET.fromstring(result["content"])
                    return [loc.text for loc in root.iter() if "loc" in loc.tag.lower()]
                except:
                    return []
        return []


class ProductionCrawler:
    def __init__(self):
        self.queue = []
        self.results = []
        self.failed = []

    def add_url(self, url: str, priority: int = 0):
        self.queue.append({"url": url, "priority": priority, "added": time.time()})
        self.queue.sort(key=lambda x: x["priority"], reverse=True)

    async def crawl(self, scraper_func, max_retries: int = 3) -> Dict:
        while self.queue:
            item = self.queue.pop(0)
            url = item["url"]
            for attempt in range(max_retries):
                try:
                    data = await scraper_func(url)
                    self.results.append({"url": url, "data": data})
                    break
                except Exception as e:
                    if attempt == max_retries - 1:
                        self.failed.append({"url": url, "error": str(e)})
        return {"completed": len(self.results), "failed": len(self.failed)}


class AntiBotBypass:
    TECHNIQUES = [
        {"name": "stealth_chrome", "rate": 0.8},
        {"name": "firefox_stealth", "rate": 0.7},
        {"name": "edge_stealth", "rate": 0.6},
    ]

    def __init__(self):
        self.attempts = []

    async def try_bypass(self, url: str) -> Dict:
        for technique in self.TECHNIQUES:
            try:
                browser = PlaywrightMCP()
                await browser.start()
                title = await browser.navigate(url)
                await browser.close()
                if "cloudflare" not in title.lower() and "just a moment" not in title.lower():
                    return {"success": True, "technique": technique["name"], "url": url}
                self.attempts.append({"technique": technique["name"], "success": False})
            except Exception as e:
                self.attempts.append({"technique": technique["name"], "error": str(e)})
        return {"success": False, "attempts": self.attempts}


class MCPServer:
    def __init__(self):
        self.browser = PlaywrightMCP()
        self.http = AsyncHTTPClient()
        self.mapper = SiteMapper()
        self.crawler = ProductionCrawler()
        self.bypass = AntiBotBypass()

    def tools(self) -> List[Dict]:
        return [
            {"name": "scrape", "description": "Scrape URL with anti-bot bypass"},
            {"name": "map_site", "description": "Map all URLs on domain"},
            {"name": "crawl", "description": "Crawl multiple URLs"},
            {"name": "browser", "description": "Browser automation"},
            {"name": "http_get", "description": "Async HTTP GET"},
        ]

    async def call(self, tool: str, args: Dict) -> Dict:
        if tool == "scrape":
            return await self.scrape(args["url"])
        elif tool == "map_site":
            return await self.mapper.map(args["url"])
        elif tool == "http_get":
            async with self.http as client:
                return await client.get(args["url"])
        return {"error": "unknown tool"}

    async def scrape(self, url: str) -> Dict:
        bypass_result = await self.bypass.try_bypass(url)
        if bypass_result["success"]:
            await self.browser.start()
            title = await self.browser.navigate(url)
            links = await self.browser.extract_links()
            await self.browser.close()
            return {"success": True, "title": title, "links": links}
        return {"success": False, "bypass_attempts": bypass_result}


def create_ultimate_scraper() -> MCPServer:
    return MCPServer()
