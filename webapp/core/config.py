"""
Core configuration for the web application.
"""
import os
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = "your-secret-key-change-in-production"

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://user:password@localhost:5432/scraper"
    )

    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # Storage
    STORAGE_TYPE: str = "local"  # local, s3, gcs
    STORAGE_PATH: str = "data/storage"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_S3_BUCKET: str = ""
    AWS_REGION: str = "us-east-1"

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "https://your-domain.com",
    ]

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60

    # Scraping
    SCRAPE_TIMEOUT: int = 60
    MAX_CONCURRENT_JOBS: int = 10
    MAX_PAGES_PER_SCRAPE: int = 1000

    # Auth
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
