"""
Spider Middleware and Item Pipeline - Like Scrapy but better.
"""
import json
import time
import hashlib
from typing import List, Dict, Any, Callable, Optional
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from loguru import logger


# ============== MIDDLEWARE ==============

class Middleware(ABC):
    """Base middleware class."""

    @abstractmethod
    async def process_request(self, request: "Request") -> Optional["Response"]:
        """Process outgoing request. Return Response to short-circuit or None to continue."""
        pass

    @abstractmethod
    async def process_response(self, request: "Request", response: "Response") -> "Response":
        """Process incoming response."""
        pass

    @abstractmethod
    async def process_error(self, request: "Request", error: Exception) -> Optional["Response"]:
        """Process error. Return Response to recover or None to propagate."""
        pass


@dataclass
class Request:
    """HTTP Request."""
    url: str
    method: str = "GET"
    headers: Dict[str, str] = field(default_factory=dict)
    body: str = ""
    cookies: Dict[str, str] = field(default_factory=dict)
    meta: Dict[str, Any] = field(default_factory=dict)
    callback: str = "parse"
    errback: str = "error"
    priority: int = 0
    dont_filter: bool = False
    _id: str = ""

    def __post_init__(self):
        if not self._id:
            self._id = hashlib.md5(f"{self.url}{time.time()}".encode()).hexdigest()[:16]


@dataclass
class Response:
    """HTTP Response."""
    url: str
    status: int = 200
    headers: Dict[str, str] = field(default_factory=dict)
    body: str = ""
    cookies: Dict[str, str] = field(default_factory=dict)
    meta: Dict[str, Any] = field(default_factory=dict)
    request: Optional[Request] = None


class MiddlewareManager:
    """
    Manages middleware pipeline.
    Like Scrapy's downloader middleware.
    """

    def __init__(self):
        self.downloader_middlewares: List[Middleware] = []
        self.spider_middlewares: List[Middleware] = []

    def add_downloader_middleware(self, middleware: Middleware):
        """Add a downloader middleware."""
        self.downloader_middlewares.append(middleware)

    def add_spider_middleware(self, middleware: Middleware):
        """Add a spider middleware."""
        self.spider_middlewares.append(middleware)

    async def fetch(self, request: Request) -> Response:
        """Fetch request through middleware pipeline."""
        # Process through downloader middlewares
        for middleware in self.downloader_middlewares:
            response = await middleware.process_request(request)
            if response:
                return response

        # Make actual request
        try:
            response = await self._make_request(request)
            # Process through response middlewares
            for middleware in self.downloader_middlewares:
                response = await middleware.process_response(request, response)
            return response

        except Exception as e:
            # Process through error middlewares
            for middleware in self.downloader_middlewares:
                response = await middleware.process_error(request, e)
                if response:
                    return response
            raise

    async def _make_request(self, request: Request) -> Response:
        """Make actual HTTP request."""
        import requests

        headers = request.headers or {}
        headers["User-Agent"] = headers.get("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")

        resp = requests.request(
            method=request.method,
            url=request.url,
            headers=headers,
            cookies=request.cookies,
            data=request.body,
            timeout=30,
        )

        return Response(
            url=str(resp.url),
            status=resp.status_code,
            headers=dict(resp.headers),
            body=resp.text,
            cookies=dict(resp.cookies),
            meta=request.meta,
            request=request,
        )


# ============== BUILT-IN MIDDLEWARES ==============

class UserAgentMiddleware(Middleware):
    """Rotate User-Agent headers."""

    def __init__(self):
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        ]
        self.current = 0

    async def process_request(self, request: Request) -> None:
        request.headers["User-Agent"] = self.user_agents[self.current]
        self.current = (self.current + 1) % len(self.user_agents)

    async def process_response(self, request: Request, response: Response) -> Response:
        return response

    async def process_error(self, request: Request, error: Exception) -> None:
        pass


class ProxyMiddleware(Middleware):
    """Rotate through proxy pool."""

    def __init__(self, proxies: List[str] = None):
        self.proxies = proxies or []
        self.current = 0

    async def process_request(self, request: Request) -> None:
        if self.proxies:
            request.meta["proxy"] = self.proxies[self.current]
            self.current = (self.current + 1) % len(self.proxies)

    async def process_response(self, request: Request, response: Response) -> Response:
        return response

    async def process_error(self, request: Request, error: Exception) -> None:
        pass


class RetryMiddleware(Middleware):
    """Retry failed requests."""

    def __init__(self, max_retries: int = 3, retry_codes: List[int] = None):
        self.max_retries = max_retries
        self.retry_codes = retry_codes or [500, 502, 503, 504, 408, 429]

    async def process_request(self, request: Request) -> None:
        retry = request.meta.get("retry", 0)
        request.meta["retry"] = retry

    async def process_response(self, request: Request, response: Response) -> Response:
        if response.status in self.retry_codes:
            retry = request.meta.get("retry", 0) + 1
            if retry <= self.max_retries:
                request.meta["retry"] = retry
                # Would re-queue the request
                logger.info(f"Retrying {request.url} (attempt {retry})")
        return response

    async def process_error(self, request: Request, error: Exception) -> None:
        retry = request.meta.get("retry", 0) + 1
        if retry <= self.max_retries:
            request.meta["retry"] = retry
            logger.info(f"Retrying {request.url} after error (attempt {retry})")


class CookiesMiddleware(Middleware):
    """Handle cookies automatically."""

    def __init__(self):
        self.cookie_jar: Dict[str, Dict] = {}

    async def process_request(self, request: Request) -> None:
        domain = self._get_domain(request.url)
        if domain in self.cookie_jar:
            request.cookies.update(self.cookie_jar[domain])

    async def process_response(self, request: Request, response: Response) -> Response:
        domain = self._get_domain(response.url)
        self.cookie_jar[domain] = response.cookies
        return response

    async def process_error(self, request: Request, error: Exception) -> None:
        pass

    def _get_domain(self, url: str) -> str:
        from urllib.parse import urlparse
        return urlparse(url).netloc


# ============== ITEM PIPELINE ==============

class ItemPipeline(ABC):
    """Base item pipeline class."""

    @abstractmethod
    async def process_item(self, item: Dict, spider: "Spider") -> Dict:
        """Process an item. Return item to continue or drop to discard."""
        pass

    def open_spider(self, spider: "Spider"):
        """Called when spider opens."""
        pass

    def close_spider(self, spider: "Spider"):
        """Called when spider closes."""
        pass


class ItemPipelineManager:
    """
    Manages item pipeline stages.
    """

    def __init__(self):
        self.pipelines: List[ItemPipeline] = []
        self._settings = {}

    def add_pipeline(self, pipeline: ItemPipeline, priority: int = 100):
        """Add pipeline with priority (lower = earlier)."""
        self.pipelines.append((priority, pipeline))
        self.pipelines.sort(key=lambda x: x[0])

    async def process_item(self, item: Dict, spider: "Spider") -> Dict:
        """Process item through all pipelines."""
        for priority, pipeline in self.pipelines:
            try:
                item = await pipeline.process_item(item, spider)
                if item is None:  # Dropped
                    return None
            except Exception as e:
                logger.error(f"Pipeline {pipeline.__class__.__name__} error: {e}")
        return item


# ============== BUILT-IN PIPELINES ==============

class ValidationPipeline(ItemPipeline):
    """Validate item fields."""

    def __init__(self, schema: Dict):
        self.schema = schema

    async def process_item(self, item: Dict, spider: "Spider") -> Dict:
        for field, rules in self.schema.items():
            if rules.get("required") and field not in item:
                logger.warning(f"Missing required field: {field}")
                return None  # Drop

            if field in item:
                expected_type = rules.get("type")
                if expected_type == "str" and not isinstance(item[field], str):
                    item[field] = str(item[field])
                elif expected_type == "int":
                    try:
                        item[field] = int(item[field])
                    except:
                        return None

        return item


class CleanPipeline(ItemPipeline):
    """Clean and normalize item data."""

    async def process_item(self, item: Dict, spider: "Spider") -> Dict:
        for key, value in item.items():
            if isinstance(value, str):
                # Remove extra whitespace
                item[key] = " ".join(value.split())
                # Remove control characters
                item[key] = "".join(c for c in value if ord(c) >= 32 or c in "\n\r\t")

        return item


class DuplicateFilterPipeline(ItemPipeline):
    """Filter duplicate items."""

    def __init__(self, key_field: str = "url"):
        self.key_field = key_field
        self.seen = set()

    async def process_item(self, item: Dict, spider: "Spider") -> Dict:
        if self.key_field not in item:
            return item

        key = item[self.key_field]
        if key in self.seen:
            return None  # Drop duplicate
        self.seen.add(key)
        return item


class DedupePipeline(ItemPipeline):
    """Remove duplicate fields from items."""

    async def process_item(self, item: Dict, spider: "Spider") -> Dict:
        # Remove empty fields
        return {k: v for k, v in item.items() if v}


class ExportPipeline(ItemPipeline):
    """Export items to file."""

    def __init__(self, output_dir: str, format: str = "jsonl"):
        self.output_dir = output_dir
        self.format = format
        self.count = 0

    async def process_item(self, item: Dict, spider: "Spider") -> Dict:
        import os
        os.makedirs(self.output_dir, exist_ok=True)

        filepath = f"{self.output_dir}/{spider.name}.{self.format}"

        if self.format == "jsonl":
            with open(filepath, "a") as f:
                f.write(json.dumps(item) + "\n")
        elif self.format == "json":
            with open(filepath, "a") as f:
                f.write(json.dumps(item) + "\n")

        self.count += 1
        return item


# ============== SPIDER ==============

@dataclass
class Spider:
    """Base Spider class."""

    name: str
    start_urls: List[str] = field(default_factory=list)
    custom_settings: Dict = field(default_factory=dict)

    middleware_manager: MiddlewareManager = field(default_factory=MiddlewareManager)
    item_pipeline_manager: ItemPipelineManager = field(default_factory=ItemPipelineManager)

    def __post_init__(self):
        self.middleware_manager = MiddlewareManager()
        self.item_pipeline_manager = ItemPipelineManager()
        self.items = []
        self.requests = []

    def start_requests(self):
        """Generate initial requests."""
        for url in self.start_urls:
            yield Request(url=url, callback="parse")

    async def parse(self, response: Response) -> Dict:
        """Default parse callback."""
        return {}

    async def run(self):
        """Run the spider."""
        logger.info(f"Starting spider: {self.name}")

        # Open pipelines
        for _, pipeline in self.item_pipeline_manager.pipelines:
            pipeline.open_spider(self)

        # Process start requests
        for request in self.start_requests():
            try:
                response = await self.middleware_manager.fetch(request)
                item = await self.parse(response)

                if item:
                    # Process through pipeline
                    processed = await self.item_pipeline_manager.process_item(item, self)
                    if processed:
                        self.items.append(processed)

            except Exception as e:
                logger.error(f"Spider error: {e}")

        # Close pipelines
        for _, pipeline in self.item_pipeline_manager.pipelines:
            pipeline.close_spider(self)

        logger.info(f"Spider complete. Items: {len(self.items)}")
        return self.items
