"""
Pydantic models/schemas for API requests and responses.
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr, HttpUrl


# ============== USER MODELS ==============

class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(UserBase):
    id: int
    created_at: datetime
    is_active: bool = True
    is_premium: bool = False

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


# ============== SCRAPE MODELS ==============

class ScrapeRequest(BaseModel):
    url: HttpUrl
    selectors: Optional[Dict[str, str]] = None
    mode: str = Field(default="auto", pattern="^(auto|parallel|api|ai|incremental)$")
    use_browser: bool = False
    webhook_url: Optional[HttpUrl] = None


class ScrapeResponse(BaseModel):
    job_id: str
    status: str  # pending, processing, completed, failed
    created_at: datetime


class ScrapeStatus(BaseModel):
    job_id: str
    status: str
    progress: float = 0.0
    data_preview: Optional[List[Dict]] = None
    error: Optional[str] = None


# ============== SCHEDULE MODELS ==============

class ScheduleCreate(BaseModel):
    name: str
    url: HttpUrl
    selectors: Optional[Dict[str, str]] = None
    cron_expression: str = "0 */6 * * *"  # Default: every 6 hours
    webhook_url: Optional[HttpUrl] = None
    enabled: bool = True


class ScheduleResponse(BaseModel):
    id: str
    name: str
    url: str
    cron_expression: str
    enabled: bool
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    run_count: int = 0
    success_count: int = 0
    failure_count: int = 0


# ============== RESULTS MODELS ==============

class ResultsResponse(BaseModel):
    id: str
    job_id: str
    url: str
    created_at: datetime
    item_count: int
    format: str
    size_bytes: int
    download_url: Optional[str] = None


class ResultsListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    results: List[ResultsResponse]


# ============== SKILLS MODELS ==============

class SkillResponse(BaseModel):
    id: int
    name: str
    category: str
    problem_type: str
    solution_type: str
    confidence: float
    success_rate: float
    use_count: int
    created_at: datetime
    last_used: Optional[datetime] = None


class SkillImport(BaseModel):
    skills: List[Dict[str, Any]]


# ============== CONFIG MODELS ==============

class ProxyConfig(BaseModel):
    enabled: bool = False
    proxies: List[str] = []


class BrowserConfig(BaseModel):
    headless: bool = True
    stealth: bool = True
    user_agent: Optional[str] = None
    viewport: Optional[Dict[str, int]] = {"width": 1280, "height": 720}


class ConfigUpdate(BaseModel):
    rate_limit_per_minute: Optional[int] = None
    scrape_timeout: Optional[int] = None
    max_concurrent_jobs: Optional[int] = None
    proxy: Optional[ProxyConfig] = None
    browser: Optional[BrowserConfig] = None


# ============== HEALTH MODELS ==============

class HealthResponse(BaseModel):
    status: str
    version: str
    uptime_seconds: float
    database: str
    redis: str
    queue: str


class StatsResponse(BaseModel):
    total_scrapes: int
    successful_scrapes: int
    failed_scrapes: int
    total_skills: int
    active_schedules: int
    storage_used_mb: float
