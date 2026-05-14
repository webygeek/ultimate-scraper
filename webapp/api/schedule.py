"""Scheduling endpoints."""
import uuid
from datetime import datetime, timedelta
from typing import Dict, List
from fastapi import APIRouter, HTTPException, Depends

from ..models.schemas import ScheduleCreate, ScheduleResponse
from ..core.security import get_current_user


router = APIRouter()

# In-memory storage (use DB in production)
SCHEDULES = {}


def calculate_next_run(cron_expression: str) -> datetime:
    """Calculate next run time from cron expression."""
    # Simplified - use croniter in production
    return datetime.utcnow() + timedelta(hours=6)


@router.post("", response_model=ScheduleResponse)
async def create_schedule(
    request: ScheduleCreate,
    current_user: dict = Depends(get_current_user)
) -> Dict:
    """Create a new scheduled job."""
    schedule_id = str(uuid.uuid4())[:8]

    schedule = {
        "id": schedule_id,
        "user_id": current_user.get("user_id", 1),
        "name": request.name,
        "url": str(request.url),
        "selectors": request.selectors,
        "cron_expression": request.cron_expression,
        "webhook_url": str(request.webhook_url) if request.webhook_url else None,
        "enabled": request.enabled,
        "last_run": None,
        "next_run": calculate_next_run(request.cron_expression).isoformat(),
        "run_count": 0,
        "success_count": 0,
        "failure_count": 0,
        "created_at": datetime.utcnow().isoformat(),
    }

    SCHEDULES[schedule_id] = schedule

    return {
        "id": schedule_id,
        "name": schedule["name"],
        "url": schedule["url"],
        "cron_expression": schedule["cron_expression"],
        "enabled": schedule["enabled"],
        "last_run": schedule["last_run"],
        "next_run": schedule["next_run"],
        "run_count": schedule["run_count"],
        "success_count": schedule["success_count"],
        "failure_count": schedule["failure_count"],
    }


@router.get("", response_model=List[ScheduleResponse])
async def list_schedules(
    current_user: dict = Depends(get_current_user)
) -> List[Dict]:
    """List all schedules for current user."""
    user_schedules = [
        s for s in SCHEDULES.values()
        if s.get("user_id") == current_user.get("user_id", 1)
    ]
    return user_schedules


@router.get("/{schedule_id}", response_model=ScheduleResponse)
async def get_schedule(
    schedule_id: str,
    current_user: dict = Depends(get_current_user)
) -> Dict:
    """Get a specific schedule."""
    if schedule_id not in SCHEDULES:
        raise HTTPException(status_code=404, detail="Schedule not found")

    return SCHEDULES[schedule_id]


@router.patch("/{schedule_id}/toggle")
async def toggle_schedule(
    schedule_id: str,
    enabled: bool,
    current_user: dict = Depends(get_current_user)
) -> Dict:
    """Enable or disable a schedule."""
    if schedule_id not in SCHEDULES:
        raise HTTPException(status_code=404, detail="Schedule not found")

    SCHEDULES[schedule_id]["enabled"] = enabled
    return SCHEDULES[schedule_id]


@router.delete("/{schedule_id}")
async def delete_schedule(
    schedule_id: str,
    current_user: dict = Depends(get_current_user)
) -> Dict:
    """Delete a schedule."""
    if schedule_id not in SCHEDULES:
        raise HTTPException(status_code=404, detail="Schedule not found")

    del SCHEDULES[schedule_id]
    return {"message": "Schedule deleted"}


@router.post("/{schedule_id}/run")
async def run_schedule_now(
    schedule_id: str,
    current_user: dict = Depends(get_current_user)
) -> Dict:
    """Trigger a schedule to run immediately."""
    if schedule_id not in SCHEDULES:
        raise HTTPException(status_code=404, detail="Schedule not found")

    schedule = SCHEDULES[schedule_id]

    # In production: Queue the scrape job
    schedule["last_run"] = datetime.utcnow().isoformat()
    schedule["run_count"] += 1

    return {
        "message": "Schedule triggered",
        "schedule_id": schedule_id,
        "last_run": schedule["last_run"],
    }
