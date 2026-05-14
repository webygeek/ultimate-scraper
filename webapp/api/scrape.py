"""Scraping endpoints."""
import asyncio
import uuid
from datetime import datetime
from typing import Dict, List
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends

from ..models.schemas import ScrapeRequest, ScrapeResponse, ScrapeStatus
from ..core.security import get_current_user


router = APIRouter()

# In-memory job storage (use Redis/DB in production)
JOBS = {}


@router.post("", response_model=ScrapeResponse)
async def create_scrape_job(
    request: ScrapeRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
) -> Dict:
    """Create a new scraping job."""
    job_id = str(uuid.uuid4())

    # Store job
    JOBS[job_id] = {
        "id": job_id,
        "user_id": current_user.get("user_id", 1),
        "url": str(request.url),
        "selectors": request.selectors,
        "mode": request.mode,
        "status": "pending",
        "progress": 0.0,
        "created_at": datetime.utcnow().isoformat(),
        "result": None,
        "error": None,
    }

    # Run scrape in background
    background_tasks.add_task(run_scrape, job_id, request)

    return {
        "job_id": job_id,
        "status": "pending",
        "created_at": datetime.utcnow(),
    }


@router.get("/{job_id}", response_model=ScrapeStatus)
async def get_scrape_status(
    job_id: str,
    current_user: dict = Depends(get_current_user)
) -> Dict:
    """Get status of a scraping job."""
    if job_id not in JOBS:
        raise HTTPException(status_code=404, detail="Job not found")

    job = JOBS[job_id]

    # Limit preview to 5 items
    data_preview = None
    if job.get("result"):
        data_preview = job["result"][:5]

    return {
        "job_id": job_id,
        "status": job["status"],
        "progress": job["progress"],
        "data_preview": data_preview,
        "error": job.get("error"),
    }


@router.get("/{job_id}/result")
async def get_scrape_result(
    job_id: str,
    current_user: dict = Depends(get_current_user)
) -> Dict:
    """Get full result of a completed job."""
    if job_id not in JOBS:
        raise HTTPException(status_code=404, detail="Job not found")

    job = JOBS[job_id]

    if job["status"] != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Job not completed. Status: {job['status']}"
        )

    return {
        "job_id": job_id,
        "data": job["result"],
        "url": job["url"],
        "created_at": job["created_at"],
    }


async def run_scrape(job_id: str, request: ScrapeRequest):
    """Run the scrape job."""
    try:
        job = JOBS[job_id]
        job["status"] = "processing"
        job["progress"] = 0.1

        # Import scraper
        import sys
        sys.path.insert(0, ".")
        from scraper.mega_scraper import UltimateMegaScraper

        scraper = UltimateMegaScraper()

        job["progress"] = 0.3

        # Run scrape
        result = await scraper.scrape_ultimate(
            url=str(request.url),
            selectors=request.selectors,
            mode=request.mode,
        )

        job["progress"] = 0.9

        if result.success:
            job["status"] = "completed"
            job["result"] = result.data
        else:
            job["status"] = "failed"
            job["error"] = result.error

        job["progress"] = 1.0

    except Exception as e:
        if job_id in JOBS:
            JOBS[job_id]["status"] = "failed"
            JOBS[job_id]["error"] = str(e)
