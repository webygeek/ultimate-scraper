"""
Ultimate Scraper - FastAPI Web Application
"""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from contextlib import asynccontextmanager

from .api import (
    scrape_router,
    schedule_router,
    results_router,
    skills_router,
    config_router,
    auth_router,
    health_router,
)
from .core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan."""
    # Startup
    print(f"Starting Ultimate Scraper API...")
    print(f"Environment: {settings.ENVIRONMENT}")
    print(f"Database: {settings.DATABASE_URL[:20] if settings.DATABASE_URL else 'Not configured'}...")

    yield

    # Shutdown
    print("Shutting down Ultimate Scraper API...")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title="Ultimate Scraper API",
        description="Self-learning, multi-agent web scraping platform",
        version="1.0.0",
        lifespan=lifespan,
    )

    # Middleware
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(health_router, prefix="/api/v1", tags=["Health"])
    app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])
    app.include_router(scrape_router, prefix="/api/v1/scrape", tags=["Scraping"])
    app.include_router(schedule_router, prefix="/api/v1/schedule", tags=["Scheduling"])
    app.include_router(results_router, prefix="/api/v1/results", tags=["Results"])
    app.include_router(skills_router, prefix="/api/v1/skills", tags=["Skills"])
    app.include_router(config_router, prefix="/api/v1/config", tags=["Configuration"])

    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.ENVIRONMENT == "development",
    )
