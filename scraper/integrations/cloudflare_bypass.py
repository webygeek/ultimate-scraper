"""
Cloudflare Bypass Integration - Multiple strategies for bypassing Cloudflare protection.
Supports: cloudscraper, undetected-chromedriver, and third-party services.
"""
import time
import random
from typing import Optional, Dict, Callable
from dataclasses import dataclass
from enum import Enum
from loguru import logger


class BypassStrategy(Enum):
    """Available Cloudflare bypass strategies."""
    CLOUDSCRAPER = "cloudscraper"
    UNDETECTED = "undetected"
    SCRAPER_API = "scraperapi"
    BRIGHT_DATA = "brightdata"
    OXYLABS = "oxylabs"
    INFATICA = "infatica"
    NONE = "none"  # No bypass, standard request


@dataclass
class CloudflareConfig:
    """Configuration for Cloudflare bypass."""
    enabled: bool = True
    strategy: str = "cloudscraper"  # Default strategy
    max_retries: int = 3
    wait_time: int = 5  # Seconds to wait for challenge
    scraperapi_key: str = ""  # Optional ScraperAPI key
    brightdata_key: str = ""  # Optional Bright Data key
    oxylabs_key: str = ""  # Optional Oxylabs key
    infatica_key: str = ""  # Optional Infatica key
    use_residential_proxy: bool = False


class CloudflareBypasser:
    """
    Multi-strategy Cloudflare bypass.

    Strategies (in order of effectiveness):
    1. ScraperAPI/Bright Data/Oxylabs (paid, 99%+ success)
    2. undetected-chromedriver (free, ~70% success)
    3. cloudscraper (free, ~30% success, simple challenges only)
    """

    def __init__(self, config: Dict = None):
        self.config = CloudflareConfig(
            enabled=config.get("cloudflare_bypass", {}).get("enabled", True),
            strategy=config.get("cloudflare_bypass", {}).get("strategy", "cloudscraper"),
            max_retries=config.get("cloudflare_bypass", {}).get("max_retries", 3),
            wait_time=config.get("cloudflare_bypass", {}).get("wait_time", 5),
            scraperapi_key=config.get("cloudflare_bypass", {}).get("scraperapi_key", ""),
            brightdata_key=config.get("cloudflare_bypass", {}).get("brightdata_key", ""),
            oxylabs_key=config.get("cloudflare_bypass", {}).get("oxylabs_key", ""),
            infatica_key=config.get("cloudflare_bypass", {}).get("infatica_key", ""),
        )

    def is_cloudflare_protected(self, response) -> bool:
        """Check if response is a Cloudflare challenge page."""
        if not response:
            return True

        text = ""
        if hasattr(response, 'text'):
            text = response.text
        elif hasattr(response, 'content'):
            text = response.content.decode('utf-8', errors='ignore')

        cloudflare_indicators = [
            "checking your browser",
            "cf-challenge-browser",
            "cloudflare",
            "ray id",
            "turnstile",
            "just a moment",
            "_cf_chl_opt",
        ]

        text_lower = text.lower()
        return any(indicator.lower() in text_lower for indicator in cloudflare_indicators)

    def get_bypass_strategy(self, strategy_name: str = None) -> Callable:
        """Get the bypass function for the specified strategy."""
        strategy = strategy_name or self.config.strategy

        strategies = {
            "cloudscraper": self._bypass_cloudscraper,
            "undetected": self._bypass_undetected,
            "scraperapi": self._bypass_scraperapi,
            "brightdata": self._bypass_brightdata,
            "oxylabs": self._bypass_oxylabs,
            "infatica": self._bypass_infatica,
            "none": self._bypass_none,
        }

        return strategies.get(strategy.lower(), self._bypass_cloudscraper)

    def bypass(self, url: str, strategy: str = None) -> Optional[Dict]:
        """
        Attempt to bypass Cloudflare and fetch URL.

        Returns:
            Dict with 'success', 'html', 'response', 'strategy'
        """
        if not self.config.enabled:
            logger.info("Cloudflare bypass disabled")
            return self._bypass_none(url)

        # Try specified strategy first
        bypass_func = self.get_bypass_strategy(strategy)

        for attempt in range(self.config.max_retries):
            logger.info(f"Attempting Cloudflare bypass (attempt {attempt + 1}/{self.config.max_retries}) with strategy: {strategy or self.config.strategy}")

            try:
                result = bypass_func(url)
                if result and result.get('success'):
                    logger.info(f"Cloudflare bypass successful using {result.get('strategy')}")
                    return result
            except Exception as e:
                logger.warning(f"Bypass attempt {attempt + 1} failed: {e}")

            # Wait before retry
            if attempt < self.config.max_retries - 1:
                wait = self.config.wait_time * (attempt + 1)
                logger.info(f"Waiting {wait}s before retry...")
                time.sleep(wait)

        return {
            'success': False,
            'html': None,
            'error': 'All bypass attempts failed',
            'strategy': strategy or self.config.strategy
        }

    def _bypass_none(self, url: str) -> Dict:
        """Standard request without bypass."""
        import requests

        response = requests.get(url, timeout=30)
        return {
            'success': response.status_code == 200 and not self.is_cloudflare_protected(response),
            'html': response.text if response.status_code == 200 else None,
            'response': response,
            'strategy': 'none'
        }

    def _bypass_cloudscraper(self, url: str) -> Dict:
        """
        Bypass using cloudscraper library.
        Works for simple Cloudflare challenges (~30% success).
        """
        try:
            import cloudscraper

            scraper = cloudscraper.create_scraper(
                browser={
                    'browser': 'chrome',
                    'platform': 'windows',
                    'desktop': True
                }
            )

            response = scraper.get(url, timeout=30)

            if response.status_code == 200:
                return {
                    'success': not self.is_cloudflare_protected(response),
                    'html': response.text,
                    'response': response,
                    'strategy': 'cloudscraper'
                }

        except ImportError:
            logger.warning("cloudscraper not installed. Run: pip install cloudscraper")
        except Exception as e:
            logger.warning(f"cloudscraper bypass failed: {e}")

        return {'success': False, 'strategy': 'cloudscraper'}

    def _bypass_undetected(self, url: str) -> Dict:
        """
        Bypass using undetected-chromedriver.
        Uses a modified ChromeDriver that bypasses detection (~70% success).
        """
        try:
            import undetected_chromedriver as uc

            options = uc.ChromeOptions()
            options.headless = True
            options.add_argument('--disable-gpu')
            options.add_argument('--no-sandbox')

            driver = uc.Chrome(options=options, version_main=None)
            driver.get(url)

            # Wait for potential challenge
            time.sleep(self.config.wait_time)

            html = driver.page_source
            driver.quit()

            return {
                'success': not self.is_cloudflare_protected({'text': html}),
                'html': html,
                'strategy': 'undetected'
            }

        except ImportError:
            logger.warning("undetected-chromedriver not installed. Run: pip install undetected-chromedriver")
        except Exception as e:
            logger.warning(f"undetected-chromedriver bypass failed: {e}")

        return {'success': False, 'strategy': 'undetected'}

    def _bypass_scraperapi(self, url: str) -> Dict:
        """
        Bypass using ScraperAPI (paid service, ~99% success).
        """
        if not self.config.scraperapi_key:
            logger.warning("ScraperAPI key not configured. Add 'scraperapi_key' to cloudflare_bypass config.")
            return {'success': False, 'strategy': 'scraperapi'}

        import requests

        api_url = f"http://api.scraperapi.com/?api_key={self.config.scraperapi_key}&url={url}&country_code=us"

        try:
            response = requests.get(api_url, timeout=60)

            return {
                'success': response.status_code == 200,
                'html': response.text,
                'response': response,
                'strategy': 'scraperapi'
            }
        except Exception as e:
            logger.warning(f"ScraperAPI bypass failed: {e}")
            return {'success': False, 'strategy': 'scraperapi'}

    def _bypass_brightdata(self, url: str) -> Dict:
        """
        Bypass using Bright Data proxy (paid service, ~99% success).
        """
        if not self.config.brightdata_key:
            logger.warning("Bright Data key not configured. Add 'brightdata_key' to cloudflare_bypass config.")
            return {'success': False, 'strategy': 'brightdata'}

        import requests

        # Bright Data zone format: username:password
        zone = self.config.brightdata_key
        proxy = f"http://{zone}@brd.superproxy.io:22225"

        try:
            response = requests.get(
                url,
                proxies={'http': proxy, 'https': proxy},
                timeout=60
            )

            return {
                'success': response.status_code == 200,
                'html': response.text,
                'response': response,
                'strategy': 'brightdata'
            }
        except Exception as e:
            logger.warning(f"Bright Data bypass failed: {e}")
            return {'success': False, 'strategy': 'brightdata'}

    def _bypass_oxylabs(self, url: str) -> Dict:
        """
        Bypass using Oxylabs residential proxies (paid service, ~99% success).
        """
        if not self.config.oxylabs_key:
            logger.warning("Oxylabs key not configured. Add 'oxylabs_key' to cloudflare_bypass config.")
            return {'success': False, 'strategy': 'oxylabs'}

        import requests

        proxy = f"http://{self.config.oxylabs_key}:@pr.oxylabs.io:7777"

        try:
            response = requests.get(
                url,
                proxies={'http': proxy, 'https': proxy},
                timeout=60
            )

            return {
                'success': response.status_code == 200,
                'html': response.text,
                'response': response,
                'strategy': 'oxylabs'
            }
        except Exception as e:
            logger.warning(f"Oxylabs bypass failed: {e}")
            return {'success': False, 'strategy': 'oxylabs'}

    def _bypass_infatica(self, url: str) -> Dict:
        """
        Bypass using Infatica residential proxies (paid service, ~95% success).
        More affordable option.
        """
        if not self.config.infatica_key:
            logger.warning("Infatica key not configured. Add 'infatica_key' to cloudflare_bypass config.")
            return {'success': False, 'strategy': 'infatica'}

        import requests

        proxy = f"http://{self.config.infatica_key}:@proxy.infatica.io:10000"

        try:
            response = requests.get(
                url,
                proxies={'http': proxy, 'https': proxy},
                timeout=60
            )

            return {
                'success': response.status_code == 200,
                'html': response.text,
                'response': response,
                'strategy': 'infatica'
            }
        except Exception as e:
            logger.warning(f"Infatica bypass failed: {e}")
            return {'success': False, 'strategy': 'infatica'}

    def get_browser_bypass(self, url: str, use_undetected: bool = True) -> Optional[str]:
        """
        Get HTML using browser automation.
        Most reliable for Cloudflare but slowest.
        """
        if use_undetected:
            result = self._bypass_undetected(url)
            if result.get('success'):
                return result.get('html')
        else:
            # Fall back to Playwright with extended wait
            result = self._playwright_bypass(url)
            if result.get('success'):
                return result.get('html')

        return None

    def _playwright_bypass(self, url: str) -> Dict:
        """
        Bypass using Playwright with extended wait.
        Less reliable than undetected-chromedriver.
        """
        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
                )
                page = context.new_page()

                # Inject stealth scripts
                page.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                    Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                    Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
                    window.chrome = { runtime: {}, loadTimes: function() {}, cricket: function() {} };
                """)

                page.goto(url, timeout=90000, wait_until='domcontentloaded')

                # Wait extra time for Cloudflare
                time.sleep(self.config.wait_time * 3)

                html = page.content()
                browser.close()

                return {
                    'success': not self.is_cloudflare_protected({'text': html}),
                    'html': html,
                    'strategy': 'playwright'
                }

        except Exception as e:
            logger.warning(f"Playwright bypass failed: {e}")
            return {'success': False, 'strategy': 'playwright'}


def create_bypasser(config: Dict = None) -> CloudflareBypasser:
    """Factory function to create a configured CloudflareBypasser."""
    return CloudflareBypasser(config)
