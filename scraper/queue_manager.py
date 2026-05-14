"""
Queue Manager - Crawlee-style reliable request queue.
"""
import asyncio
import json
import time
import hashlib
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import deque
from loguru import logger


class QueueState(Enum):
    """Queue states."""
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class QueueItem:
    """An item in the queue."""
    id: str
    url: str
    method: str = "GET"
    headers: Dict[str, str] = field(default_factory=dict)
    data: Any = None
    priority: int = 0
    state: QueueState = QueueState.PENDING
    attempts: int = 0
    max_attempts: int = 3
    created_at: float = field(default_factory=time.time)
    started_at: float = 0
    completed_at: float = 0
    error: str = ""
    result: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class RequestQueue:
    """
    Crawlee-style request queue with persistence.
    Handles deduplication, prioritization, and retry logic.
    """

    def __init__(
        self,
        name: str = "default",
        persist_path: str = "data/queue",
        max_attempts: int = 3,
    ):
        self.name = name
        self.persist_path = persist_path
        self.max_attempts = max_attempts

        # In-memory queues
        self.pending: deque = deque()
        self.active: Dict[str, QueueItem] = {}
        self.completed: Dict[str, QueueItem] = {}
        self.failed: Dict[str, QueueItem] = {}

        # Statistics
        self.stats = {
            "total_requests": 0,
            "completed": 0,
            "failed": 0,
            "retried": 0,
        }

        # Load from disk
        self._load()

    def _get_id(self, url: str) -> str:
        """Generate unique ID for URL."""
        return hashlib.md5(url.encode()).hexdigest()[:16]

    def add(
        self,
        url: str,
        method: str = "GET",
        headers: Dict = None,
        data: Any = None,
        priority: int = 0,
        max_attempts: int = None,
    ) -> str:
        """
        Add a request to the queue.

        Returns:
            Request ID
        """
        request_id = self._get_id(url)

        # Skip if already in queue
        if request_id in self.active or request_id in self.completed:
            if request_id in self.completed:
                return request_id  # Already done
            # In pending
            for item in self.pending:
                if item.id == request_id:
                    return request_id

        item = QueueItem(
            id=request_id,
            url=url,
            method=method,
            headers=headers or {},
            data=data,
            priority=priority,
            max_attempts=max_attempts or self.max_attempts,
        )

        # Add to pending (sorted by priority)
        self._insert_pending(item)

        self.stats["total_requests"] += 1
        self._save()

        logger.debug(f"Added to queue: {url}")
        return request_id

    def add_many(self, urls: List[str], priority: int = 0):
        """Add multiple URLs to queue."""
        for url in urls:
            self.add(url, priority=priority)

    def _insert_pending(self, item: QueueItem):
        """Insert item into pending deque sorted by priority."""
        inserted = False
        for i, pending_item in enumerate(self.pending):
            if item.priority > pending_item.priority:
                self.pending.insert(i, item)
                inserted = True
                break

        if not inserted:
            self.pending.append(item)

    async def fetch(self) -> Optional[QueueItem]:
        """
        Fetch next item from queue.

        Returns:
            QueueItem or None
        """
        while self.pending:
            item = self.pending.popleft()

            # Check if already processed
            if item.id in self.completed or item.id in self.failed:
                continue

            # Move to active
            item.state = QueueState.ACTIVE
            item.started_at = time.time()
            item.attempts += 1
            self.active[item.id] = item

            self._save()
            return item

        return None

    def complete(self, request_id: str, result: Any = None):
        """
        Mark request as completed.
        """
        if request_id in self.active:
            item = self.active.pop(request_id)
            item.state = QueueState.COMPLETED
            item.completed_at = time.time()
            item.result = result
            self.completed[request_id] = item

            self.stats["completed"] += 1
            self._save()

    def fail(
        self,
        request_id: str,
        error: str = "",
        retry: bool = True,
    ):
        """
        Mark request as failed.
        """
        if request_id not in self.active:
            return

        item = self.active[request_id]

        if retry and item.attempts < item.max_attempts:
            # Retry
            item.attempts += 1
            item.error = error
            item.started_at = 0
            item.state = QueueState.PENDING

            # Re-add to pending with same priority
            self._insert_pending(item)
            del self.active[request_id]

            self.stats["retried"] += 1
            logger.info(f"Retrying {item.url} (attempt {item.attempts})")

        else:
            # Mark as failed
            item = self.active.pop(request_id)
            item.state = QueueState.FAILED
            item.completed_at = time.time()
            item.error = error
            self.failed[request_id] = item

            self.stats["failed"] += 1
            logger.warning(f"Failed {item.url}: {error}")

        self._save()

    def get_stats(self) -> Dict:
        """Get queue statistics."""
        return {
            **self.stats,
            "pending": len(self.pending),
            "active": len(self.active),
            "completed": len(self.completed),
            "failed": len(self.failed),
        }

    def _save(self):
        """Save queue state to disk."""
        import os
        os.makedirs(self.persist_path, exist_ok=True)

        data = {
            "name": self.name,
            "pending": [
                self._item_to_dict(item) for item in self.pending
            ],
            "active": {
                k: self._item_to_dict(v) for k, v in self.active.items()
            },
            "completed": {
                k: self._item_to_dict(v) for k, v in self.completed.items()
            },
            "failed": {
                k: self._item_to_dict(v) for k, v in self.failed.items()
            },
            "stats": self.stats,
        }

        filepath = f"{self.persist_path}/{self.name}.json"
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

    def _load(self):
        """Load queue state from disk."""
        import os

        filepath = f"{self.persist_path}/{self.name}.json"
        if not os.path.exists(filepath):
            return

        try:
            with open(filepath) as f:
                data = json.load(f)

            self.pending = deque([
                self._dict_to_item(d) for d in data.get("pending", [])
            ])

            self.active = {
                k: self._dict_to_item(v) for k, v in data.get("active", {}).items()
            }

            self.completed = {
                k: self._dict_to_item(v) for k, v in data.get("completed", {}).items()
            }

            self.failed = {
                k: self._dict_to_item(v) for k, v in data.get("failed", {}).items()
            }

            self.stats = data.get("stats", self.stats)

        except Exception as e:
            logger.warning(f"Failed to load queue: {e}")

    def _item_to_dict(self, item: QueueItem) -> dict:
        """Convert item to dict."""
        return {
            "id": item.id,
            "url": item.url,
            "method": item.method,
            "headers": item.headers,
            "data": item.data,
            "priority": item.priority,
            "state": item.state.value,
            "attempts": item.attempts,
            "max_attempts": item.max_attempts,
            "created_at": item.created_at,
            "started_at": item.started_at,
            "completed_at": item.completed_at,
            "error": item.error,
            "metadata": item.metadata,
        }

    def _dict_to_item(self, d: dict) -> QueueItem:
        """Convert dict to item."""
        return QueueItem(
            id=d["id"],
            url=d["url"],
            method=d.get("method", "GET"),
            headers=d.get("headers", {}),
            data=d.get("data"),
            priority=d.get("priority", 0),
            state=QueueState(d.get("state", "pending")),
            attempts=d.get("attempts", 0),
            max_attempts=d.get("max_attempts", self.max_attempts),
            created_at=d.get("created_at", time.time()),
            started_at=d.get("started_at", 0),
            completed_at=d.get("completed_at", 0),
            error=d.get("error", ""),
            metadata=d.get("metadata", {}),
        )

    def clear(self):
        """Clear all queues."""
        self.pending.clear()
        self.active.clear()
        self.completed.clear()
        self.failed.clear()
        self.stats = {
            "total_requests": 0,
            "completed": 0,
            "failed": 0,
            "retried": 0,
        }
        self._save()

    def retry_failed(self):
        """Re-queue all failed requests."""
        for item in list(self.failed.values()):
            item.attempts = 0
            item.error = ""
            item.state = QueueState.PENDING
            self._insert_pending(item)

        self.failed.clear()
        self._save()
        logger.info("Retried all failed requests")


class QueueRunner:
    """
    Run queue with worker pool.
    """

    def __init__(
        self,
        queue: RequestQueue,
        worker_count: int = 5,
        scraper: Callable = None,
    ):
        self.queue = queue
        self.worker_count = worker_count
        self.scraper = scraper
        self.running = False

    async def run(self, timeout: float = None):
        """
        Run the queue with workers.

        Args:
            timeout: Maximum runtime in seconds
        """
        self.running = True
        start_time = time.time()

        workers = []
        for i in range(self.worker_count):
            worker = asyncio.create_task(self._worker(i))
            workers.append(worker)

        # Wait for completion or timeout
        while self.running:
            # Check timeout
            if timeout and (time.time() - start_time) > timeout:
                logger.info("Timeout reached")
                break

            # Check if queue is empty
            stats = self.queue.get_stats()
            if stats["pending"] == 0 and stats["active"] == 0:
                logger.info("Queue empty")
                break

            await asyncio.sleep(0.5)

        # Stop workers
        self.running = False
        await asyncio.gather(*workers, return_exceptions=True)

        return self.queue.get_stats()

    async def _worker(self, worker_id: int):
        """Worker coroutine."""
        logger.debug(f"Worker {worker_id} started")

        while self.running:
            # Fetch next item
            item = await self.queue.fetch()

            if not item:
                await asyncio.sleep(0.5)
                continue

            # Process
            try:
                if self.scraper:
                    result = await self.scraper(item)
                    self.queue.complete(item.id, result)
                else:
                    self.queue.complete(item.id)

            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
                self.queue.fail(item.id, str(e))

        logger.debug(f"Worker {worker_id} stopped")


def create_queue(
    name: str = "default",
    persist: bool = True,
) -> RequestQueue:
    """
    Create a new request queue.

    Args:
        name: Queue name
        persist: Enable disk persistence

    Returns:
        RequestQueue
    """
    persist_path = "data/queue" if persist else None

    if persist_path:
        import os
        os.makedirs(persist_path, exist_ok=True)

    return RequestQueue(name=name, persist_path=persist_path)
