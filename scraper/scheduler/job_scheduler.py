"""
Job Scheduler - Cron-like scheduling for scraping jobs.
"""
import time
import json
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from pathlib import Path
from loguru import logger
import croniter


@dataclass
class ScrapingJob:
    """A scheduled scraping job."""
    id: str
    name: str
    url: str
    selectors: Dict[str, str] = field(default_factory=dict)
    schedule: str = ""  # Cron expression
    enabled: bool = True
    last_run: str = ""
    next_run: str = ""
    run_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    config: Dict[str, Any] = field(default_factory=dict)
    webhook_url: str = ""
    output_dir: str = "data/output"

    def __post_init__(self):
        if not self.schedule:
            self.schedule = "0 */6 * * *"  # Default: every 6 hours


class JobScheduler:
    """
    Cron-like scheduler for scraping jobs.
    """

    def __init__(self, db_path: str = "data/scheduler_jobs.json"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        self.jobs: Dict[str, ScrapingJob] = {}
        self.running = False
        self.thread = None
        self._lock = threading.Lock()

        self._load()

    def _load(self):
        """Load jobs from disk."""
        if Path(self.db_path).exists():
            try:
                with open(self.db_path) as f:
                    data = json.load(f)
                    self.jobs = {
                        k: ScrapingJob(**v) for k, v in data.get("jobs", {}).items()
                    }
            except Exception as e:
                logger.warning(f"Failed to load scheduler: {e}")

    def _save(self):
        """Save jobs to disk."""
        try:
            data = {
                "jobs": {k: v.__dict__ for k, v in self.jobs.items()}
            }
            with open(self.db_path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save scheduler: {e}")

    def add_job(
        self,
        name: str,
        url: str,
        schedule: str,
        selectors: Dict[str, str] = None,
        webhook_url: str = "",
        output_dir: str = "data/output",
    ) -> str:
        """Add a new scheduled job."""
        import uuid
        job_id = str(uuid.uuid4())[:8]

        job = ScrapingJob(
            id=job_id,
            name=name,
            url=url,
            schedule=schedule,
            selectors=selectors or {},
            webhook_url=webhook_url,
            output_dir=output_dir,
        )

        # Calculate next run
        job.next_run = self._get_next_run_time(schedule)

        with self._lock:
            self.jobs[job_id] = job
            self._save()

        logger.info(f"Added job: {name} (ID: {job_id})")
        return job_id

    def remove_job(self, job_id: str) -> bool:
        """Remove a job."""
        with self._lock:
            if job_id in self.jobs:
                del self.jobs[job_id]
                self._save()
                logger.info(f"Removed job: {job_id}")
                return True
        return False

    def enable_job(self, job_id: str, enabled: bool = True):
        """Enable or disable a job."""
        with self._lock:
            if job_id in self.jobs:
                self.jobs[job_id].enabled = enabled
                self._save()

    def get_job(self, job_id: str) -> Optional[ScrapingJob]:
        """Get a job by ID."""
        return self.jobs.get(job_id)

    def list_jobs(self) -> List[ScrapingJob]:
        """List all jobs."""
        return list(self.jobs.values())

    def get_due_jobs(self) -> List[ScrapingJob]:
        """Get jobs that are due to run."""
        now = datetime.now()
        due = []

        for job in self.jobs.values():
            if not job.enabled:
                continue

            if job.next_run:
                try:
                    next_run = datetime.fromisoformat(job.next_run)
                    if next_run <= now:
                        due.append(job)
                except:
                    pass

        return due

    def _get_next_run_time(self, schedule: str) -> str:
        """Calculate next run time from cron expression."""
        try:
            cron = croniter.croniter(schedule, datetime.now())
            next_time = cron.get_next(datetime)
            return next_time.isoformat()
        except:
            # Default to 1 hour from now
            return (datetime.now() + timedelta(hours=1)).isoformat()

    def update_next_run(self, job_id: str):
        """Update next run time for a job."""
        if job_id in self.jobs:
            job = self.jobs[job_id]
            job.next_run = self._get_next_run_time(job.schedule)

    def start(self, callback: Callable[[ScrapingJob], Any]):
        """
        Start the scheduler.

        Args:
            callback: Function to call when a job is due
        """
        self.running = True
        self.callback = callback
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        logger.info("Scheduler started")

    def stop(self):
        """Stop the scheduler."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
        logger.info("Scheduler stopped")

    def _run_loop(self):
        """Main scheduler loop."""
        while self.running:
            try:
                due_jobs = self.get_due_jobs()

                for job in due_jobs:
                    self._run_job(job)

                # Update next run times
                for job_id in self.jobs:
                    self.update_next_run(job_id)

            except Exception as e:
                logger.error(f"Scheduler error: {e}")

            time.sleep(60)  # Check every minute

    def _run_job(self, job: ScrapingJob):
        """Execute a job."""
        logger.info(f"Running job: {job.name} ({job.id})")

        try:
            # Run the scraper
            result = self.callback(job)

            # Update stats
            job.run_count += 1
            job.last_run = datetime.now().isoformat()

            if result and result.get("success"):
                job.success_count += 1

                # Send webhook if configured
                if job.webhook_url:
                    self._send_webhook(job, result)
            else:
                job.failure_count += 1

            self._save()

        except Exception as e:
            logger.error(f"Job {job.id} failed: {e}")
            job.failure_count += 1
            job.last_run = datetime.now().isoformat()
            self._save()

    def _send_webhook(self, job: ScrapingJob, result: Dict):
        """Send webhook notification."""
        try:
            import requests

            payload = {
                "job_id": job.id,
                "job_name": job.name,
                "url": job.url,
                "success": result.get("success", False),
                "items": result.get("count", 0),
                "timestamp": datetime.now().isoformat(),
            }

            requests.post(
                job.webhook_url,
                json=payload,
                timeout=10,
            )

            logger.info(f"Webhook sent for job {job.id}")

        except Exception as e:
            logger.error(f"Webhook failed: {e}")

    def get_stats(self) -> Dict:
        """Get scheduler statistics."""
        total = len(self.jobs)
        enabled = sum(1 for j in self.jobs.values() if j.enabled)

        total_runs = sum(j.run_count for j in self.jobs.values())
        total_success = sum(j.success_count for j in self.jobs.values())

        return {
            "total_jobs": total,
            "enabled_jobs": enabled,
            "total_runs": total_runs,
            "total_success": total_success,
            "success_rate": total_success / max(total_runs, 1),
        }


class IncrementalCache:
    """
    Cache for incremental scraping - only stores new/changed data.
    """

    def __init__(self, db_path: str = "data/scraped_cache.json"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.cache: Dict[str, Dict] = {}
        self._load()

    def _load(self):
        """Load cache from disk."""
        if Path(self.db_path).exists():
            try:
                with open(self.db_path) as f:
                    self.cache = json.load(f)
            except:
                self.cache = {}

    def _save(self):
        """Save cache to disk."""
        with open(self.db_path, "w") as f:
            json.dump(self.cache, f, indent=2)

    def get_key(self, url: str, selectors: Dict) -> str:
        """Generate cache key for URL and selectors."""
        import hashlib
        key_data = f"{url}:{json.dumps(selectors, sort_keys=True)}"
        return hashlib.md5(key_data.encode()).hexdigest()

    def get(self, url: str, selectors: Dict) -> Optional[List[Dict]]:
        """Get cached data for URL."""
        key = self.get_key(url, selectors)
        return self.cache.get(key, {}).get("data")

    def set(self, url: str, selectors: Dict, data: List[Dict]):
        """Set cached data."""
        key = self.get_key(url, selectors)
        self.cache[key] = {
            "url": url,
            "selectors": selectors,
            "data": data,
            "timestamp": datetime.now().isoformat(),
        }
        self._save()

    def get_new_items(
        self,
        url: str,
        selectors: Dict,
        new_data: List[Dict],
        key_field: str = "url",
    ) -> List[Dict]:
        """
        Get only new items compared to cache.

        Args:
            url: URL that was scraped
            selectors: Selectors used
            new_data: New scraped data
            key_field: Field to use for comparison

        Returns:
            List of items that are new or changed
        """
        cached = self.get(url, selectors) or []
        cached_keys = {item.get(key_field) for item in cached}

        new_items = []
        for item in new_data:
            item_key = item.get(key_field)
            if item_key not in cached_keys:
                new_items.append(item)

        # Update cache
        self.set(url, selectors, new_data)

        return new_items

    def clear(self, url: str = None):
        """Clear cache."""
        if url:
            # Clear specific URL (by pattern)
            to_remove = [k for k, v in self.cache.items() if url in v.get("url", "")]
            for k in to_remove:
                del self.cache[k]
        else:
            self.cache = {}

        self._save()


class WebhookPusher:
    """
    Push scraping results to webhooks.
    """

    def __init__(self):
        self.webhooks: List[str] = []

    def add(self, url: str):
        """Add a webhook URL."""
        if url not in self.webhooks:
            self.webhooks.append(url)

    def remove(self, url: str):
        """Remove a webhook URL."""
        if url in self.webhooks:
            self.webhooks.remove(url)

    def push(self, data: Dict) -> Dict[str, bool]:
        """
        Push data to all webhooks.

        Returns:
            Dict mapping webhook URL to success status
        """
        results = {}

        for webhook_url in self.webhooks:
            try:
                import requests

                payload = {
                    "timestamp": datetime.now().isoformat(),
                    "data": data,
                }

                response = requests.post(
                    webhook_url,
                    json=payload,
                    timeout=10,
                )

                results[webhook_url] = response.status_code == 200

            except Exception as e:
                logger.error(f"Webhook push failed: {e}")
                results[webhook_url] = False

        return results
