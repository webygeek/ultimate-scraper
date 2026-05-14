"""
Ultimate Mega Scraper
Combines all features: distributed, parallel, AI-powered, API discovery, visual learning.
"""
import asyncio
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from loguru import logger

from .enhanced_orchestrator import UltimateSelfEvolvingScraper
from .distributed import ParallelScraper, ProxyManager
from .api_discovery import APIDiscovery, GraphQLScanner
from .ai_selectors import AISelectorGenerator
from .scheduler import JobScheduler, IncrementalCache, WebhookPusher
from .visual import VisualLearner


@dataclass
class MegaScrapeResult:
    """Complete result from mega scraper."""
    success: bool
    data: List[Dict]
    method: str  # distributed, parallel, api, visual
    techniques_used: List[str]
    duration_ms: int
    items_count: int
    workers_used: int
    error: Optional[str] = None


class UltimateMegaScraper:
    """
    Ultimate scraper combining all features:

    1. Self-Learning: Skills, agents, visual learning
    2. Distributed: Parallel workers, proxy pool
    3. API Discovery: REST/GraphQL API finding
    4. AI Selectors: Auto-generate CSS selectors
    5. Scheduling: Cron-like job scheduling
    6. Webhooks: Real-time result pushing
    7. Incremental: Only new/changed data
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}

        # Initialize all systems
        self.self_evolving = UltimateSelfEvolvingScraper(self.config)
        self.parallel = ParallelScraper(self.config)
        self.proxy_manager = ProxyManager(self.config)
        self.api_discovery = APIDiscovery(self.config)
        self.graphql = GraphQLScanner()
        self.ai_selector = AISelectorGenerator(self.config)
        self.scheduler = JobScheduler()
        self.cache = IncrementalCache()
        self.webhook = WebhookPusher()
        self.visual = VisualLearner()

    # ============== DISTRIBUTED SCRAPING ==============

    def scrape_parallel(
        self,
        urls: List[str],
        selectors: Dict[str, str] = None,
        workers: int = 10,
    ) -> MegaScrapeResult:
        """
        Scrape multiple URLs in parallel.

        Args:
            urls: List of URLs to scrape
            selectors: CSS selectors
            workers: Number of parallel workers

        Returns:
            MegaScrapeResult with combined data
        """
        start = time.time()
        techniques = ["parallel", f"workers:{workers}"]

        results = self.parallel.scrape_urls(
            urls=urls,
            selectors=selectors,
            workers=workers,
        )

        # Combine all data
        all_data = []
        for result in results:
            if result.success:
                all_data.extend(result.data)
                techniques.extend(result.worker_id.split("_"))

        duration = int((time.time() - start) * 1000)

        return MegaScrapeResult(
            success=len(all_data) > 0,
            data=all_data,
            method="distributed_parallel",
            techniques_used=techniques,
            duration_ms=duration,
            items_count=len(all_data),
            workers_used=workers,
        )

    def scrape_crawl(
        self,
        start_url: str,
        selectors: Dict[str, str] = None,
        max_pages: int = 100,
        max_depth: int = 3,
        workers: int = 10,
    ) -> MegaScrapeResult:
        """
        Crawl entire site starting from a URL.

        Args:
            start_url: Starting URL
            selectors: CSS selectors
            max_pages: Max pages to crawl
            max_depth: Max link depth
            workers: Number of workers

        Returns:
            MegaScrapeResult with all scraped data
        """
        start = time.time()

        results = self.parallel.crawl_site(
            start_url=start_url,
            selectors=selectors or {},
            max_pages=max_pages,
            max_depth=max_depth,
            workers=workers,
        )

        all_data = []
        for result in results:
            if result.success:
                all_data.extend(result.data)

        duration = int((time.time() - start) * 1000)

        return MegaScrapeResult(
            success=len(all_data) > 0,
            data=all_data,
            method="distributed_crawl",
            techniques_used=["crawl", f"depth:{max_depth}", f"pages:{max_pages}"],
            duration_ms=duration,
            items_count=len(all_data),
            workers_used=workers,
        )

    # ============== API DISCOVERY SCRAPING ==============

    def scrape_api(
        self,
        url: str,
        prefer_api: bool = True,
        use_browser: bool = False,
    ) -> MegaScrapeResult:
        """
        Discover and scrape via hidden APIs.

        Args:
            url: Target URL
            prefer_api: Prefer API over HTML
            use_browser: Use browser for request interception

        Returns:
            MegaScrapeResult with API-scraped data
        """
        start = time.time()

        result = self.api_discovery.scrape_via_api(
            url=url,
            use_browser=use_browser,
            prefer_apis=prefer_api,
        )

        duration = int((time.time() - start) * 1000)

        techniques = [result.get("method", "api")]
        if result.get("api_used"):
            techniques.append(result["api_used"])

        return MegaScrapeResult(
            success=result.get("success", False),
            data=result.get("data", []),
            method="api_discovery",
            techniques_used=techniques,
            duration_ms=duration,
            items_count=len(result.get("data", [])),
            workers_used=1,
        )

    def scrape_graphql(
        self,
        url: str,
        fields: List[str] = None,
    ) -> MegaScrapeResult:
        """
        Scrape using GraphQL API.

        Args:
            url: Target URL
            fields: GraphQL fields to query

        Returns:
            MegaScrapeResult
        """
        start = time.time()

        result = self.graphql.scrape_graphql(
            url=url,
            selectors={f: f for f in (fields or [])},
        )

        duration = int((time.time() - start) * 1000)

        return MegaScrapeResult(
            success=result.get("success", False),
            data=result.get("data", []),
            method="graphql",
            techniques_used=["graphql"],
            duration_ms=duration,
            items_count=len(result.get("data", [])),
            workers_used=1,
            error=result.get("error"),
        )

    # ============== AI SELECTORS ==============

    async def generate_selectors_ai(
        self,
        html: str,
        field_names: List[str],
        examples: Dict[str, str] = None,
    ) -> Dict[str, str]:
        """
        Generate CSS selectors using AI.

        Args:
            html: HTML content
            field_names: Fields to extract
            examples: Example values for each field

        Returns:
            Dict mapping field names to CSS selectors
        """
        return await self.ai_selector.generate_selectors(
            html=html,
            field_names=field_names,
            examples=examples,
        )

    # ============== SCHEDULED SCRAPING ==============

    def schedule_job(
        self,
        name: str,
        url: str,
        schedule: str,
        selectors: Dict[str, str] = None,
        webhook_url: str = "",
        incremental: bool = True,
    ) -> str:
        """
        Schedule a recurring scrape job.

        Args:
            name: Job name
            url: Target URL
            schedule: Cron expression (e.g., "0 */6 * * *" for every 6 hours)
            selectors: CSS selectors
            webhook_url: Webhook to notify on completion
            incremental: Only return new/changed data

        Returns:
            Job ID
        """
        job_id = self.scheduler.add_job(
            name=name,
            url=url,
            schedule=schedule,
            selectors=selectors,
            webhook_url=webhook_url,
        )

        logger.info(f"Scheduled job: {name} (ID: {job_id})")
        return job_id

    def start_scheduler(self):
        """Start the job scheduler."""
        self.scheduler.start(callback=self._run_scheduled_job)
        logger.info("Scheduler started")

    def stop_scheduler(self):
        """Stop the job scheduler."""
        self.scheduler.stop()
        logger.info("Scheduler stopped")

    def _run_scheduled_job(self, job) -> Dict:
        """Execute a scheduled job."""
        logger.info(f"Running scheduled job: {job.name}")

        # Try API discovery first
        result = self.api_discovery.scrape_via_api(job.url)

        if not result.get("success"):
            # Fall back to self-evolving scraper
            scrape_result = self.self_evolving.scrape(job.url, job.selectors)
            result = {
                "success": scrape_result.success,
                "data": scrape_result.data,
            }

        # Apply incremental caching
        if job.config.get("incremental", True):
            new_items = self.cache.get_new_items(
                url=job.url,
                selectors=job.selectors,
                new_data=result.get("data", []),
            )
            result["data"] = new_items
            result["is_incremental"] = True
        else:
            result["is_incremental"] = False

        # Send webhook
        if job.webhook_url:
            self.webhook.add(job.webhook_url)
            self.webhook.push({
                "job_name": job.name,
                "url": job.url,
                "success": result.get("success", False),
                "items": len(result.get("data", [])),
                "incremental": result.get("is_incremental", False),
            })

        return result

    # ============== INCREMENTAL SCRAPING ==============

    def scrape_incremental(
        self,
        url: str,
        selectors: Dict[str, str],
        key_field: str = "url",
    ) -> MegaScrapeResult:
        """
        Scrape and only return new/changed items.

        Args:
            url: Target URL
            selectors: CSS selectors
            key_field: Field to use for change detection

        Returns:
            MegaScrapeResult with only new items
        """
        # Get fresh data
        scrape_result = self.self_evolving.scrape(url, selectors)

        if not scrape_result.success:
            return MegaScrapeResult(
                success=False,
                data=[],
                method="incremental",
                techniques_used=[],
                duration_ms=0,
                items_count=0,
                error="Scrape failed",
            )

        # Find new items
        new_items = self.cache.get_new_items(
            url=url,
            selectors=selectors,
            new_data=scrape_result.data,
            key_field=key_field,
        )

        return MegaScrapeResult(
            success=True,
            data=new_items,
            method="incremental",
            techniques_used=scrape_result.techniques_used,
            duration_ms=scrape_result.duration_ms,
            items_count=len(new_items),
            workers_used=1,
        )

    # ============== ULTIMATE SCRAPE ==============

    async def scrape_ultimate(
        self,
        url: str,
        selectors: Dict[str, str] = None,
        mode: str = "auto",  # auto, parallel, api, ai, incremental
    ) -> MegaScrapeResult:
        """
        Ultimate scraping with automatic optimization.

        Args:
            url: Target URL
            selectors: CSS selectors
            mode: Scrape mode (auto, parallel, api, ai, incremental)

        Returns:
            MegaScrapeResult
        """
        start = time.time()
        techniques = []

        if mode == "auto":
            # Try each method in order of preference
            # 1. Try API discovery
            result = self.api_discovery.scrape_via_api(url, prefer_api=True)
            if result.get("success"):
                techniques.append("api_discovery")
                return self._wrap_result(result, "api_discovery", start, techniques)

            # 2. Try AI selector generation
            if selectors is None:
                try:
                    import requests
                    resp = requests.get(url, timeout=30)
                    selectors = await self.generate_selectors_ai(
                        html=resp.text,
                        field_names=["title", "price", "description", "image"],
                    )
                    techniques.append("ai_selectors")
                except:
                    pass

            # 3. Use self-evolving scraper
            scrape_result = self.self_evolving.scrape(url, selectors)
            if scrape_result.success:
                techniques.extend(scrape_result.techniques_used)
                return MegaScrapeResult(
                    success=True,
                    data=scrape_result.data,
                    method="self_evolving",
                    techniques_used=techniques,
                    duration_ms=scrape_result.duration_ms,
                    items_count=len(scrape_result.data),
                    workers_used=1,
                )

            # 4. Fall back to distributed parallel
            techniques.append("distributed_fallback")
            return self.scrape_parallel([url], selectors)

        elif mode == "parallel":
            return self.scrape_parallel([url], selectors)

        elif mode == "api":
            return self.scrape_api(url)

        elif mode == "ai":
            # Use AI to generate selectors then scrape
            try:
                import requests
                resp = requests.get(url, timeout=30)
                if selectors is None:
                    selectors = await self.generate_selectors_ai(
                        html=resp.text,
                        field_names=["title", "price", "description", "image"],
                    )
                techniques.append("ai_selectors")
            except Exception as e:
                logger.warning(f"AI selector generation failed: {e}")

            scrape_result = self.self_evolving.scrape(url, selectors)
            return MegaScrapeResult(
                success=scrape_result.success,
                data=scrape_result.data,
                method="ai_assisted",
                techniques_used=techniques + scrape_result.techniques_used,
                duration_ms=scrape_result.duration_ms,
                items_count=len(scrape_result.data),
                workers_used=1,
            )

        elif mode == "incremental":
            return self.scrape_incremental(url, selectors)

        return MegaScrapeResult(
            success=False,
            data=[],
            method="unknown",
            techniques_used=[],
            duration_ms=0,
            items_count=0,
            error=f"Unknown mode: {mode}",
        )

    def _wrap_result(
        self,
        result: Dict,
        method: str,
        start: float,
        techniques: List[str],
    ) -> MegaScrapeResult:
        """Wrap API result into MegaScrapeResult."""
        duration = int((time.time() - start) * 1000)
        data = result.get("data", [])

        return MegaScrapeResult(
            success=result.get("success", False),
            data=data,
            method=method,
            techniques_used=techniques,
            duration_ms=duration,
            items_count=len(data),
            workers_used=1,
        )

    # ============== STATS ==============

    def get_all_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics."""
        return {
            "self_evolving": self.self_evolving.get_all_stats(),
            "parallel": self.parallel.get_stats() if hasattr(self.parallel, 'get_stats') else {},
            "scheduler": self.scheduler.get_stats(),
            "cache": {
                "size": len(self.cache.cache),
            },
            "webhooks": {
                "count": len(self.webhook.webhooks),
            },
            "visual": {
                "demonstrations": len(self.visual.demonstrations),
                "workflows": len(self.visual.workflows),
            },
        }


# Synchronous wrapper
class MegaScraper:
    """Synchronous wrapper for UltimateMegaScraper."""

    def __init__(self, config: Dict = None):
        self._async = UltimateMegaScraper(config)

    def scrape_ultimate(self, url, selectors=None, mode="auto"):
        return asyncio.run(self._async.scrape_ultimate(url, selectors, mode))

    def scrape_parallel(self, urls, selectors=None, workers=10):
        return self._async.scrape_parallel(urls, selectors, workers)

    def scrape_api(self, url, prefer_api=True):
        return self._async.scrape_api(url, prefer_api)

    def scrape_incremental(self, url, selectors):
        return self._async.scrape_incremental(url, selectors)

    def schedule_job(self, name, url, schedule, selectors=None):
        return self._async.schedule_job(name, url, schedule, selectors)

    def start_scheduler(self):
        self._async.start_scheduler()

    def get_stats(self):
        return self._async.get_all_stats()
