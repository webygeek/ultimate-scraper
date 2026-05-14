"""Health check endpoints."""
import time
from datetime import datetime
from fastapi import APIRouter, Depends
from typing import Dict

from ..models.schemas import HealthResponse, StatsResponse
from ..core.security import get_current_user


router = APIRouter()

# Track start time
START_TIME = time.time()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> Dict:
    """Check API health."""
    # In production, check DB, Redis, Queue
    return {
        "status": "healthy",
        "version": "1.0.0",
        "uptime_seconds": time.time() - START_TIME,
        "database": "connected",
        "redis": "connected",
        "queue": "connected",
    }


@router.get("/stats", response_model=StatsResponse)
async def get_stats(current_user: dict = Depends(get_current_user)) -> Dict:
    """Get scraper statistics."""
    # In production, query from database
    return {
        "total_scrapes": 0,
        "successful_scrapes": 0,
        "failed_scrapes": 0,
        "total_skills": 0,
        "active_schedules": 0,
        "storage_used_mb": 0.0,
    }
