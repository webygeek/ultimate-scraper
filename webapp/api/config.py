"""Configuration endpoints."""
from typing import Dict
from fastapi import APIRouter, Depends

from ..models.schemas import ConfigUpdate, ProxyConfig, BrowserConfig
from ..core.security import get_current_user


router = APIRouter()

# In-memory config (use DB in production)
USER_CONFIG = {}


@router.get("")
async def get_config(
    current_user: dict = Depends(get_current_user)
) -> Dict:
    """Get current user configuration."""
    user_id = current_user.get("user_id", 1)

    if user_id not in USER_CONFIG:
        USER_CONFIG[user_id] = {
            "rate_limit_per_minute": 60,
            "scrape_timeout": 60,
            "max_concurrent_jobs": 10,
            "proxy": {
                "enabled": False,
                "proxies": [],
            },
            "browser": {
                "headless": True,
                "stealth": True,
                "user_agent": None,
                "viewport": {"width": 1280, "height": 720},
            },
        }

    return USER_CONFIG[user_id]


@router.patch("")
async def update_config(
    config: ConfigUpdate,
    current_user: dict = Depends(get_current_user)
) -> Dict:
    """Update user configuration."""
    user_id = current_user.get("user_id", 1)

    if user_id not in USER_CONFIG:
        USER_CONFIG[user_id] = {}

    # Update provided fields
    if config.rate_limit_per_minute is not None:
        USER_CONFIG[user_id]["rate_limit_per_minute"] = config.rate_limit_per_minute

    if config.scrape_timeout is not None:
        USER_CONFIG[user_id]["scrape_timeout"] = config.scrape_timeout

    if config.max_concurrent_jobs is not None:
        USER_CONFIG[user_id]["max_concurrent_jobs"] = config.max_concurrent_jobs

    if config.proxy is not None:
        USER_CONFIG[user_id]["proxy"] = config.proxy.dict()

    if config.browser is not None:
        USER_CONFIG[user_id]["browser"] = config.browser.dict()

    return USER_CONFIG[user_id]


@router.post("/proxy/test")
async def test_proxy(
    proxy_url: str,
    current_user: dict = Depends(get_current_user)
) -> Dict:
    """Test a proxy URL."""
    try:
        import requests
        response = requests.get(
            "https://httpbin.org/ip",
            proxies={"http": proxy_url, "https": proxy_url},
            timeout=10,
        )

        if response.status_code == 200:
            return {
                "success": True,
                "proxy": proxy_url,
                "response": response.json(),
            }
        else:
            return {
                "success": False,
                "proxy": proxy_url,
                "error": f"Status code: {response.status_code}",
            }

    except Exception as e:
        return {
            "success": False,
            "proxy": proxy_url,
            "error": str(e),
        }
