"""
Autoscaling - Automatically scale workers based on resources.
"""
import asyncio
import time
import psutil
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from loguru import logger


@dataclass
class WorkerStats:
    """Statistics for a worker."""
    worker_id: str
    tasks_completed: int = 0
    tasks_failed: int = 0
    avg_task_time: float = 0.0
    cpu_usage: float = 0.0
    memory_usage: float = 0.0


@dataclass
class AutoscalingConfig:
    """Configuration for autoscaling."""
    min_workers: int = 1
    max_workers: int = 20
    scale_up_threshold: float = 0.7  # Scale up when CPU/memory > 70%
    scale_down_threshold: float = 0.3  # Scale down when < 30%
    scale_up_cooldown: int = 30  # Seconds between scale ups
    scale_down_cooldown: int = 60  # Seconds between scale downs
    check_interval: int = 5  # Seconds between checks


class Autoscaler:
    """
    Automatically scale workers based on system resources and workload.
    Like Crawlee's AutoscaledPool.
    """

    def __init__(self, config: AutoscalingConfig = None):
        self.config = config or AutoscalingConfig()
        self.workers: Dict[int, asyncio.Task] = {}
        self.running = False
        self.stats: Dict[int, WorkerStats] = {}
        self.current_workers = 0
        self.last_scale_up = 0
        self.last_scale_down = 0
        self.task_queue: asyncio.Queue = asyncio.Queue()

    async def run(
        self,
        worker_fn: Callable,
        timeout: float = None,
    ):
        """
        Run autoscaled workers.

        Args:
            worker_fn: Async function to run for each worker
            timeout: Maximum runtime in seconds
        """
        self.running = True
        start_time = time.time()

        # Start initial workers
        await self._scale_to(self.config.min_workers, worker_fn)

        # Main scaling loop
        while self.running:
            # Check timeout
            if timeout and (time.time() - start_time) > timeout:
                logger.info("Autoscaler timeout reached")
                break

            # Check resources
            await self._check_and_scale(worker_fn)

            await asyncio.sleep(self.config.check_interval)

        # Stop all workers
        await self._stop_all()

    async def _check_and_scale(self, worker_fn: Callable):
        """Check resources and scale if needed."""
        cpu_percent = psutil.cpu_percent(interval=1) / 100
        memory_percent = psutil.virtual_memory().percent / 100

        avg_usage = (cpu_percent + memory_percent) / 2

        current_time = time.time()

        # Scale up
        if avg_usage < self.config.scale_up_threshold:
            if current_time - self.last_scale_up > self.config.scale_up_cooldown:
                if self.current_workers < self.config.max_workers:
                    # Calculate how many workers to add
                    deficit = self.config.scale_up_threshold - avg_usage
                    workers_to_add = max(1, int(deficit * 10))

                    new_count = min(
                        self.current_workers + workers_to_add,
                        self.config.max_workers
                    )

                    if new_count > self.current_workers:
                        await self._scale_to(new_count, worker_fn)
                        self.last_scale_up = current_time

        # Scale down
        elif avg_usage > self.config.scale_down_threshold:
            if current_time - self.last_scale_down > self.config.scale_down_cooldown:
                if self.current_workers > self.config.min_workers:
                    # Calculate how many workers to remove
                    excess = avg_usage - self.config.scale_down_threshold
                    workers_to_remove = max(1, int(excess * 10))

                    new_count = max(
                        self.current_workers - workers_to_remove,
                        self.config.min_workers
                    )

                    if new_count < self.current_workers:
                        await self._scale_to(new_count, worker_fn)
                        self.last_scale_down = current_time

    async def _scale_to(self, target_count: int, worker_fn: Callable):
        """Scale to target worker count."""
        if target_count > self.current_workers:
            # Add workers
            for i in range(target_count - self.current_workers):
                worker_id = self.current_workers + i
                worker = asyncio.create_task(self._worker(worker_id, worker_fn))
                self.workers[worker_id] = worker
                self.stats[worker_id] = WorkerStats(worker_id=str(worker_id))

            logger.info(f"Scaled up to {target_count} workers")

        elif target_count < self.current_workers:
            # Remove workers
            for _ in range(self.current_workers - target_count):
                worker_id = self.current_workers - 1
                if worker_id in self.workers:
                    self.workers[worker_id].cancel()
                    del self.workers[worker_id]
                    del self.stats[worker_id]

            logger.info(f"Scaled down to {target_count} workers")

        self.current_workers = target_count

    async def _worker(self, worker_id: int, worker_fn: Callable):
        """Worker coroutine."""
        logger.debug(f"Worker {worker_id} started")

        while self.running:
            try:
                # Get task from queue with timeout
                try:
                    task = await asyncio.wait_for(
                        self.task_queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue

                # Run worker function
                start = time.time()
                try:
                    await worker_fn(task)
                    self.stats[worker_id].tasks_completed += 1
                except Exception as e:
                    logger.error(f"Worker {worker_id} task failed: {e}")
                    self.stats[worker_id].tasks_failed += 1

                # Update stats
                elapsed = time.time() - start
                stats = self.stats[worker_id]
                stats.avg_task_time = (
                    (stats.avg_task_time * (stats.tasks_completed - 1) + elapsed)
                    / stats.tasks_completed
                )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")

        logger.debug(f"Worker {worker_id} stopped")

    async def _stop_all(self):
        """Stop all workers."""
        self.running = False

        for worker in self.workers.values():
            worker.cancel()

        await asyncio.gather(*self.workers.values(), return_exceptions=True)
        self.workers.clear()

    def stop(self):
        """Stop the autoscaler."""
        self.running = False

    def get_stats(self) -> Dict[str, Any]:
        """Get autoscaling statistics."""
        total_completed = sum(s.tasks_completed for s in self.stats.values())
        total_failed = sum(s.tasks_failed for s in self.stats.values())

        return {
            "current_workers": self.current_workers,
            "min_workers": self.config.min_workers,
            "max_workers": self.config.max_workers,
            "queue_size": self.task_queue.qsize(),
            "total_completed": total_completed,
            "total_failed": total_failed,
            "workers": {
                wid: {
                    "completed": s.tasks_completed,
                    "failed": s.tasks_failed,
                    "avg_time": round(s.avg_task_time, 3),
                }
                for wid, s in self.stats.items()
            },
            "system": {
                "cpu_percent": psutil.cpu_percent(),
                "memory_percent": psutil.virtual_memory().percent,
            },
        }

    def add_task(self, task: Any):
        """Add a task to the queue."""
        self.task_queue.put_nowait(task)


class ResourceMonitor:
    """
    Monitor system resources for scraping operations.
    """

    def __init__(self):
        self.snapshots: List[Dict] = []

    def record_snapshot(self):
        """Record current resource usage."""
        snapshot = {
            "timestamp": time.time(),
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "memory_used_mb": psutil.virtual_memory().used / (1024 * 1024),
            "disk_io": psutil.disk_io_counters()._asdict() if psutil.disk_io_counters() else {},
            "net_io": psutil.net_io_counters()._asdict() if psutil.net_io_counters() else {},
        }
        self.snapshots.append(snapshot)

        # Keep last 100 snapshots
        if len(self.snapshots) > 100:
            self.snapshots = self.snapshots[-100:]

        return snapshot

    def get_stats(self) -> Dict[str, Any]:
        """Get resource statistics."""
        if not self.snapshots:
            return {}

        return {
            "samples": len(self.snapshots),
            "cpu": {
                "current": self.snapshots[-1]["cpu_percent"],
                "avg": sum(s["cpu_percent"] for s in self.snapshots) / len(self.snapshots),
                "max": max(s["cpu_percent"] for s in self.snapshots),
            },
            "memory": {
                "current": self.snapshots[-1]["memory_percent"],
                "avg": sum(s["memory_percent"] for s in self.snapshots) / len(self.snapshots),
                "max": max(s["memory_percent"] for s in self.snapshots),
            },
        }


class WorkerPool:
    """
    Simple worker pool with fixed size.
    For simpler use cases without autoscaling.
    """

    def __init__(self, size: int = 5):
        self.size = size
        self.workers: List[asyncio.Task] = []
        self.queue: asyncio.Queue = asyncio.Queue()
        self.running = False

    async def run(self, worker_fn: Callable, tasks: List[Any]):
        """Run all tasks with the worker pool."""
        self.running = True

        # Fill queue
        for task in tasks:
            await self.queue.put(task)

        # Start workers
        for i in range(self.size):
            worker = asyncio.create_task(self._worker(i, worker_fn))
            self.workers.append(worker)

        # Wait for completion
        await self.queue.join()

        # Stop workers
        self.running = False
        for worker in self.workers:
            worker.cancel()

        await asyncio.gather(*self.workers, return_exceptions=True)

    async def _worker(self, worker_id: int, worker_fn: Callable):
        """Worker coroutine."""
        while self.running:
            try:
                task = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                await worker_fn(task)
                self.queue.task_done()
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
