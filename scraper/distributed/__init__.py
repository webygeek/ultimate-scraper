"""Distributed parallel scraping module."""
from .parallel_scraper import ParallelScraper, WorkerPool, Task
from .proxy_manager import ProxyManager, ProxyPool

__all__ = ["ParallelScraper", "WorkerPool", "Task", "ProxyManager", "ProxyPool"]
