"""Results management endpoints."""
import os
import uuid
from datetime import datetime
from typing import List, Dict
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import FileResponse

from ..models.schemas import ResultsResponse, ResultsListResponse
from ..core.security import get_current_user


router = APIRouter()

# In-memory storage (use DB in production)
RESULTS = {}


@router.get("", response_model=ResultsListResponse)
async def list_results(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user)
) -> Dict:
    """List all results for current user."""
    user_results = [
        r for r in RESULTS.values()
        if r.get("user_id") == current_user.get("user_id", 1)
    ]

    # Sort by created_at desc
    user_results.sort(key=lambda x: x.get("created_at", ""), reverse=True)

    # Paginate
    start = (page - 1) * page_size
    end = start + page_size
    paginated = user_results[start:end]

    return {
        "total": len(user_results),
        "page": page,
        "page_size": page_size,
        "results": paginated,
    }


@router.get("/{result_id}", response_model=ResultsResponse)
async def get_result(
    result_id: str,
    current_user: dict = Depends(get_current_user)
) -> Dict:
    """Get a specific result."""
    if result_id not in RESULTS:
        raise HTTPException(status_code=404, detail="Result not found")

    result = RESULTS[result_id]

    if result.get("user_id") != current_user.get("user_id", 1):
        raise HTTPException(status_code=403, detail="Not authorized")

    return result


@router.get("/{result_id}/download")
async def download_result(
    result_id: str,
    format: str = Query("json"),
    current_user: dict = Depends(get_current_user)
) -> FileResponse:
    """Download result in specified format."""
    if result_id not in RESULTS:
        raise HTTPException(status_code=404, detail="Result not found")

    result = RESULTS[result_id]

    if result.get("user_id") != current_user.get("user_id", 1):
        raise HTTPException(status_code=403, detail="Not authorized")

    # In production: Stream from storage
    filepath = result.get("filepath", f"/tmp/{result_id}.json")

    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        filepath,
        media_type="application/json",
        filename=f"scrape_{result_id}.{format}",
    )


@router.delete("/{result_id}")
async def delete_result(
    result_id: str,
    current_user: dict = Depends(get_current_user)
) -> Dict:
    """Delete a result."""
    if result_id not in RESULTS:
        raise HTTPException(status_code=404, detail="Result not found")

    result = RESULTS[result_id]

    if result.get("user_id") != current_user.get("user_id", 1):
        raise HTTPException(status_code=403, detail="Not authorized")

    del RESULTS[result_id]

    return {"message": "Result deleted"}


@router.post("/{result_id}/share")
async def share_result(
    result_id: str,
    expires_hours: int = Query(24, ge=1, le=168),
    current_user: dict = Depends(get_current_user)
) -> Dict:
    """Create a shareable link for a result."""
    if result_id not in RESULTS:
        raise HTTPException(status_code=404, detail="Result not found")

    share_id = str(uuid.uuid4())[:8]

    # In production: Store share link with expiry

    return {
        "share_id": share_id,
        "url": f"/shared/{share_id}",
        "expires_hours": expires_hours,
    }
