"""
Distributed Parallel Scraper
Scales scraping across multiple workers with shared resources.
"""
import asyncio
import time
import hashlib
import uuid
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable
from queue import Queue, Empty
from threading import Lock, Semaphore
from loguru import logger

from ..modules.anti_detection import AntiDetection
from ..modules.rate_limiter import AdaptiveRateLimiter


@dataclass
class Task:
    """A scraping task."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    url: str = ""
    selectors: Dict[str, str] = field(default_factory=dict)
    priority: int = 1  # 1-10, higher = more important
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    retries: int = 0
    max_retries: int = 3


@dataclass
class TaskResult:
    """Result from a task."""
    task_id: str
    success: bool
    data: List[Dict] = field(default_factory=list)
    error: str = ""
    duration_ms: int = 0
    worker_id: str = ""


@dataclass
class WorkerStats:
    """Worker statistics."""
    worker_id: str
    tasks_completed: int = 0
    tasks_failed: int = 0
    total_data: int = 0
    total_time_ms: int = 0


class WorkerPool:
    """
    Pool of workers for parallel scraping.
    Uses thread pool for I/O-bound tasks.
    """

    def __init__(
        self,
        size: int = 10,
        config: Dict[str, Any] = None,
    ):
        self.size = size
        self.config = config or {}
        self.workers: List["ScraperWorker"] = []
        self.task_queue: Queue = Queue()
        self.result_queue: Queue = Queue()
        self.running = False
        self.stats: Dict[str, WorkerStats] = {}
        self._lock = Lock()

    def start(self):
        """Start all workers."""
        self.running = True

        for i in range(self.size):
            worker = ScraperWorker(
                worker_id=f"worker_{i}",
                task_queue=self.task_queue,
                result_queue=self.result_queue,
                config=self.config,
            )
            worker.start()
            self.workers.append(worker)
            self.stats[worker.worker_id] = WorkerStats(worker_id=worker.worker_id)

        logger.info(f"Started {self.size} workers")

    def stop(self):
        """Stop all workers."""
        self.running = False

        for worker in self.workers:
            worker.stop()

        self.workers.clear()
        logger.info("Stopped all workers")

    def submit_task(self, task: Task):
        """Submit a task to the pool."""
        self.task_queue.put(task)

    def submit_tasks(self, tasks: List[Task]):
        """Submit multiple tasks."""
        for task in tasks:
            self.submit_task(task)

    def get_result(self, timeout: float = 1.0) -> Optional[TaskResult]:
        """Get a result from the pool."""
        try:
            return self.result_queue.get(timeout=timeout)
        except Empty:
            return None

    def get_results(self, count: int, timeout: float = 1.0) -> List[TaskResult]:
        """Get multiple results."""
        results = []
        for _ in range(count):
            result = self.get_result(timeout)
            if result:
                results.append(result)
        return results

    def get_all_results(self, timeout: float = 60.0) -> List[TaskResult]:
        """Get all remaining results."""
        results = []
        start = time.time()

        while time.time() - start < timeout:
            result = self.get_result(0.1)
            if result:
                results.append(result)
            elif self.task_queue.empty():
                break

        return results

    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics."""
        total_completed = sum(s.tasks_completed for s in self.stats.values())
        total_failed = sum(s.tasks_failed for s in self.stats.values())
        total_time = sum(s.total_time_ms for s in self.stats.values())
        total_data = sum(s.total_data for s in self.stats.values())

        return {
            "workers": len(self.workers),
            "running": self.running,
            "queue_size": self.task_queue.qsize(),
            "results_pending": self.result_queue.qsize(),
            "total_completed": total_completed,
            "total_failed": total_failed,
            "total_data": total_data,
            "avg_time_ms": total_time / max(total_completed, 1),
        }


class ScraperWorker:
    """
    Single worker that processes scraping tasks.
    """

    def __init__(
        self,
        worker_id: str,
        task_queue: Queue,
        result_queue: Queue,
        config: Dict[str, Any],
    ):
        self.worker_id = worker_id
        self.task_queue = task_queue
        self.result_queue = result_queue
        self.config = config
        self.running = False
        self.thread = None
        self.anti_detection = AntiDetection(config)
        self.rate_limiter = AdaptiveRateLimiter(config)

    def start(self):
        """Start the worker thread."""
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self):
        """Stop the worker thread."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)

    def _run(self):
        """Main worker loop."""
        logger.debug(f"{self.worker_id} started")

        while self.running:
            try:
                # Get task with timeout
                task = self.task_queue.get(timeout=1.0)
                result = self._process_task(task)
                self.result_queue.put(result)
                self.task_queue.task_done()

            except Empty:
                continue
            except Exception as e:
                logger.error(f"{self.worker_id} error: {e}")

        logger.debug(f"{self.worker_id} stopped")

    def _process_task(self, task: Task) -> TaskResult:
        """Process a single task."""
        start_time = time.time()

        try:
            # Rate limit by domain
            from urllib.parse import urlparse
            domain = urlparse(task.url).netloc
            self.rate_limiter.acquire(domain)

            # Scrape
            data = self._scrape(task)

            duration = int((time.time() - start_time) * 1000)

            return TaskResult(
                task_id=task.id,
                success=True,
                data=data,
                duration_ms=duration,
                worker_id=self.worker_id,
            )

        except Exception as e:
            duration = int((time.time() - start_time) * 1000)

            # Retry if needed
            if task.retries < task.max_retries:
                task.retries += 1
                self.task_queue.put(task)
                logger.debug(f"{self.worker_id} retrying task {task.id}")

            return TaskResult(
                task_id=task.id,
                success=False,
                error=str(e),
                duration_ms=duration,
                worker_id=self.worker_id,
            )

    def _scrape(self, task: Task) -> List[Dict]:
        """Perform the actual scrape."""
        import requests
        from bs4 import BeautifulSoup

        headers = self.anti_detection.get_headers(task.url)

        response = requests.get(
            task.url,
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()

        html = response.text
        soup = BeautifulSoup(html, "lxml")

        # Extract data
        results = []
        containers = self._find_containers(soup)

        for container in containers:
            item = {}
            for field_name, selector in task.selectors.items():
                elem = container.select_one(selector)
                if elem:
                    if field_name == "url":
                        item[field_name] = elem.get("href", "")
                    elif field_name == "image":
                        item[field_name] = elem.get("src", "")
                    else:
                        item[field_name] = elem.get_text(strip=True)
            if item:
                results.append(item)

        return results

    def _find_containers(self, soup) -> List:
        """Find data containers."""
        patterns = [
            "[class*='item']", "[class*='card']", "[class*='product']",
            "[class*='listing']", "[class*='result']", "article",
        ]

        for pattern in patterns:
            containers = soup.select(pattern)
            if len(containers) > 1:
                return containers

        return [soup]


class ParallelScraper:
    """
    High-performance parallel scraper with worker pool.
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.worker_pool: Optional[WorkerPool] = None
        self.proxy_manager = ProxyManager(self.config)
        self.results: List[TaskResult] = []

    def scrape_urls(
        self,
        urls: List[str],
        selectors: Dict[str, str] = None,
        workers: int = 10,
        priority: int = 5,
    ) -> List[TaskResult]:
        """
        Scrape multiple URLs in parallel.

        Args:
            urls: List of URLs to scrape
            selectors: CSS selectors for data extraction
            workers: Number of parallel workers
            priority: Task priority (1-10)

        Returns:
            List of TaskResults
        """
        if selectors is None:
            selectors = {}

        # Start worker pool
        self.worker_pool = WorkerPool(size=workers, config=self.config)
        self.worker_pool.start()

        # Create tasks
        tasks = []
        for url in urls:
            task = Task(
                url=url,
                selectors=selectors,
                priority=priority,
            )
            tasks.append(task)

        # Submit tasks
        self.worker_pool.submit_tasks(tasks)

        # Wait for completion
        self.worker_pool.task_queue.join()

        # Get all results
        results = self.worker_pool.get_all_results(timeout=30)

        # Stop pool
        self.worker_pool.stop()

        self.results = results
        return results

    def scrape_with_pagination(
        self,
        base_url: str,
        page_param: str = "page",
        max_pages: int = 10,
        selectors: Dict[str, str] = None,
        workers: int = 10,
    ) -> List[TaskResult]:
        """
        Scrape paginated content in parallel.

        Args:
            base_url: Base URL (without page parameter)
            page_param: Name of the page parameter
            max_pages: Maximum pages to scrape
            selectors: CSS selectors
            workers: Number of parallel workers

        Returns:
            List of TaskResults
        """
        # Generate URLs
        urls = []
        separator = "&" if "?" in base_url else "?"
        for page in range(1, max_pages + 1):
            urls.append(f"{base_url}{separator}{page_param}={page}")

        return self.scrape_urls(urls, selectors, workers)

    def crawl_site(
        self,
        start_url: str,
        selectors: Dict[str, str],
        max_depth: int = 3,
        max_pages: int = 100,
        workers: int = 10,
    ) -> List[TaskResult]:
        """
        Crawl a site starting from a URL.

        Args:
            start_url: Starting URL
            selectors: CSS selectors
            max_depth: Maximum link depth to follow
            max_pages: Maximum pages to crawl
            workers: Number of parallel workers

        Returns:
            List of TaskResults
        """
        from urllib.parse import urljoin, urlparse

        visited = set()
        to_visit = [(start_url, 0)]  # (url, depth)
        urls_to_scrape = []

        while to_visit and len(visited) < max_pages:
            url, depth = to_visit.pop(0)

            if url in visited or depth > max_depth:
                continue

            visited.add(url)

            # Scrape this URL
            urls_to_scrape.append(url)

            if depth < max_depth:
                # Get links from this page
                try:
                    import requests
                    response = requests.get(url, timeout=10)
                    if response.status_code == 200:
                        from bs4 import BeautifulSoup
                        soup = BeautifulSoup(response.text, "lxml")

                        # Find all links on same domain
                        base_domain = urlparse(start_url).netloc
                        for link in soup.select("a[href]"):
                            href = link.get("href", "")
                            if href:
                                full_url = urljoin(url, href)
                                link_domain = urlparse(full_url).netloc
                                if link_domain == base_domain:
                                    if full_url not in visited:
                                        to_visit.append((full_url, depth + 1))

                except Exception as e:
                    logger.debug(f"Failed to get links from {url}: {e}")

        # Scrape all discovered URLs
        return self.scrape_urls(urls_to_scrape, selectors, workers)

    def get_stats(self) -> Dict[str, Any]:
        """Get scraping statistics."""
        if not self.worker_pool:
            return {}

        pool_stats = self.worker_pool.get_stats()

        # Calculate success rate
        total = len(self.results)
        successful = sum(1 for r in self.results if r.success)

        return {
            **pool_stats,
            "total_results": total,
            "successful": successful,
            "failed": total - successful,
            "success_rate": successful / max(total, 1),
            "total_data_items": sum(len(r.data) for r in self.results),
        }


# Import threading
import threading
