"""API routes module."""
from .health import router as health_router
from .auth import router as auth_router
from .scrape import router as scrape_router
from .schedule import router as schedule_router
from .results import router as results_router
from .skills import router as skills_router
from .config import router as config_router

__all__ = [
    "health_router",
    "auth_router",
    "scrape_router",
    "schedule_router",
    "results_router",
    "skills_router",
    "config_router",
]
