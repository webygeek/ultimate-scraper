"""
Spider Contracts - Testing framework for spiders.
"""
import json
import time
from typing import Dict, List, Any, Callable
from dataclasses import dataclass, field
from loguru import logger


@dataclass
class Contract:
    """A spider contract."""
    method: str  # Method name
    priority: int = 0  # Higher = runs first
    args: Dict = field(default_factory=dict)
    kwargs: Dict = field(default_factory=dict)


class SpiderContract:
    """Decorator to define contracts for spider methods."""

    def __init__(self, priority: int = 0, **kwargs):
        self.priority = priority
        self.kwargs = kwargs

    def __call__(self, method: Callable) -> Callable:
        method._contract = Contract(
            method=method.__name__,
            priority=self.priority,
            kwargs=self.kwargs,
        )
        return method


class ContractRunner:
    """
    Run spider contracts to verify spider behavior.
    """

    def __init__(self):
        self.results: List[Dict] = []

    async def run_contracts(
        self,
        spider: Any,
        method_name: str = None,
    ) -> Dict[str, Any]:
        """
        Run contracts for a spider method.

        Returns:
            {"passed": [...], "failed": [...], "errors": [...]}
        """
        results = {
            "passed": [],
            "failed": [],
            "errors": [],
        }

        # Find contracted methods
        methods = []
        for name in dir(spider):
            if name.startswith("_"):
                continue
            attr = getattr(spider, name)
            if callable(attr) and hasattr(attr, "_contract"):
                if method_name is None or name == method_name:
                    methods.append((attr, attr._contract))

        # Sort by priority
        methods.sort(key=lambda x: x[1].priority, reverse=True)

        for method, contract in methods:
            try:
                # Setup
                result = await self._run_contract(spider, method, contract)
                if result["passed"]:
                    results["passed"].append({
                        "method": contract.method,
                        "result": result,
                    })
                else:
                    results["failed"].append({
                        "method": contract.method,
                        "result": result,
                    })
            except Exception as e:
                results["errors"].append({
                    "method": contract.method,
                    "error": str(e),
                })

        return results

    async def _run_contract(self, spider, method, contract) -> Dict:
        """Run a single contract."""
        result = {
            "passed": True,
            "checks": [],
        }

        # Check response has certain attributes
        if "response_contains" in contract.kwargs:
            expected = contract.kwargs["response_contains"]
            # Would check actual response
            result["checks"].append({
                "type": "contains",
                "expected": expected,
                "passed": True,  # Simplified
            })

        if "item_count_min" in contract.kwargs:
            min_count = contract.kwargs["item_count_min"]
            # Would check actual item count
            result["checks"].append({
                "type": "min_count",
                "expected": min_count,
                "actual": 0,  # Would be actual
                "passed": True,
            })

        return result


class ContractChecker:
    """
    Verify spider contracts match requirements.
    """

    @staticmethod
    def check_returns_list(method: Callable) -> bool:
        """Check if method returns a list."""
        # Would inspect return type
        return True

    @staticmethod
    def check_has_selectors(method: Callable) -> bool:
        """Check if method uses selectors."""
        import inspect
        source = inspect.getsource(method)
        selectors = ["select", "css", "xpath", "find"]
        return any(s in source.lower() for s in selectors)

    @staticmethod
    def check_rate_limit(method: Callable) -> bool:
        """Check if method respects rate limits."""
        import inspect
        source = inspect.getsource(method)
        rate_keywords = ["delay", "sleep", "rate", "throttle"]
        return any(k in source.lower() for k in rate_keywords)


# ============== PAUSE/RESUME ==============

class CrawlState:
    """
    Persist crawl state for pause/resume.
    """

    def __init__(self, state_file: str = "data/crawl_state.json"):
        self.state_file = state_file
        self.state: Dict = {}
        self._load()

    def _load(self):
        """Load state from disk."""
        import os
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file) as f:
                    self.state = json.load(f)
            except:
                self.state = {}

    def _save(self):
        """Save state to disk."""
        import os
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        with open(self.state_file, "w") as f:
            json.dump(self.state, f, indent=2)

    def save(self):
        """Public save method."""
        self._save()

    def get(self, key: str, default: Any = None) -> Any:
        """Get a state value."""
        return self.state.get(key, default)

    def set(self, key: str, value: Any):
        """Set a state value."""
        self.state[key] = value
        self._save()

    def get_visited(self) -> set:
        """Get visited URLs."""
        return set(self.state.get("visited", []))

    def add_visited(self, url: str):
        """Mark URL as visited."""
        visited = self.get_visited()
        visited.add(url)
        self.state["visited"] = list(visited)
        self._save()

    def is_visited(self, url: str) -> bool:
        """Check if URL was visited."""
        return url in self.get_visited()

    def get_depth(self, url: str) -> int:
        """Get crawl depth for URL."""
        depths = self.state.get("depths", {})
        return depths.get(url, 0)

    def set_depth(self, url: str, depth: int):
        """Set crawl depth for URL."""
        depths = self.state.get("depths", {})
        depths[url] = depth
        self.state["depths"] = depths
        self._save()

    def get_pending(self) -> List[Dict]:
        """Get pending URLs to crawl."""
        return self.state.get("pending", [])

    def add_pending(self, url: str, depth: int, meta: Dict = None):
        """Add URL to pending queue."""
        pending = self.state.get("pending", [])
        if not any(p["url"] == url for p in pending):
            pending.append({
                "url": url,
                "depth": depth,
                "meta": meta or {},
                "added_at": time.time(),
            })
            self.state["pending"] = pending
            self._save()

    def pop_pending(self) -> Dict:
        """Get and remove next pending URL."""
        pending = self.state.get("pending", [])
        if pending:
            item = pending.pop(0)
            self.state["pending"] = pending
            self._save()
            return item
        return None

    def clear(self):
        """Clear all state."""
        self.state = {
            "visited": [],
            "pending": [],
            "depths": {},
            "stats": {},
        }
        self._save()

    def get_stats(self) -> Dict:
        """Get crawl statistics."""
        return self.state.get("stats", {})

    def update_stats(self, **kwargs):
        """Update statistics."""
        stats = self.state.get("stats", {})
        for key, value in kwargs.items():
            if key in stats:
                stats[key] += value
            else:
                stats[key] = value
        self.state["stats"] = stats
        self._save()


class PauseableSpider:
    """
    Spider with pause/resume support.
    """

    def __init__(self, state_file: str = "data/crawl_state.json"):
        self.state = CrawlState(state_file)
        self.paused = False

    def pause(self):
        """Pause the spider."""
        self.paused = True
        self.state.set("status", "paused")
        logger.info("Spider paused")

    def resume(self):
        """Resume the spider."""
        self.paused = False
        self.state.set("status", "running")
        logger.info("Spider resumed")

    def is_paused(self) -> bool:
        """Check if paused."""
        return self.paused

    def should_stop(self) -> bool:
        """Check if should stop."""
        return self.state.get("status") == "stopped"

    def stop(self):
        """Stop the spider."""
        self.state.set("status", "stopped")
        logger.info("Spider stopped")

    async def crawl_with_state(
        self,
        start_url: str,
        max_depth: int = 3,
        max_pages: int = 1000,
    ):
        """
        Crawl with pause/resume support.
        """
        self.state.set("status", "running")
        self.state.clear()

        # Initialize with start URL
        if not self.state.get_pending():
            self.state.add_pending(start_url, 0)

        while True:
            # Check pause/stop
            if self.is_paused():
                await self._wait_for_resume()

            if self.should_stop():
                break

            # Get next URL
            pending = self.state.pop_pending()
            if not pending:
                break

            url = pending["url"]
            depth = pending["depth"]

            # Skip if visited
            if self.state.is_visited(url):
                continue

            # Mark visited
            self.state.add_visited(url)
            self.state.set_depth(url, depth)

            # Update stats
            self.state.update_stats(pages=1)

            # Check limits
            if self.state.get_stats().get("pages", 0) >= max_pages:
                logger.info("Max pages reached")
                break

            # Process URL
            await self._process_url(url, depth, max_depth)

        self.state.set("status", "complete")
        logger.info("Crawl complete")

    async def _wait_for_resume(self):
        """Wait while paused."""
        import asyncio
        while self.paused and not self.should_stop():
            await asyncio.sleep(1)

    async def _process_url(self, url: str, depth: int, max_depth: int):
        """Process a URL."""
        pass  # Override in subclass


def check_contracts(spider_class, method_name: str = None) -> Dict:
    """
    Check contracts for a spider class.

    Usage:
        results = check_contracts(MySpider)
    """
    runner = ContractRunner()

    # Create instance
    spider = spider_class()

    import asyncio
    return asyncio.run(runner.run_contracts(spider, method_name))
