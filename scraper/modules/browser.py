"""
Self-contained browser automation with built-in anti-detection.
Uses Playwright with custom stealth configuration - no external services.
"""
import os
import random
import time
from typing import Optional
from dataclasses import dataclass
from loguru import logger


@dataclass
class BrowserConfig:
    """Configuration for browser automation."""
    headless: bool = True
    slow_mo: int = 100
    viewport_width: int = 1920
    viewport_height: int = 1080
    accept_downloads: bool = False
    stealth: bool = True
    human_behavior: bool = True


class BuiltInStealthBrowser:
    """
    Self-contained browser automation with built-in stealth features.
    No external stealth libraries required - all anti-detection is custom.
    """

    def __init__(self, config: dict):
        self.config = config
        self.browser_config = BrowserConfig(
            headless=config.get("browser", {}).get("headless", True),
            slow_mo=config.get("browser", {}).get("slow_mo", 100),
            viewport_width=config.get("browser", {}).get("viewport", {}).get("width", 1920),
            viewport_height=config.get("browser", {}).get("viewport", {}).get("height", 1080),
            stealth=config.get("anti_detection", {}).get("stealth_mode", True),
            human_behavior=config.get("browser", {}).get("human_behavior", True),
        )

        self._browser = None
        self._context = None
        self._page = None
        self._playwright = None
        self._stealth_scripts_loaded = False

    def start(self) -> bool:
        """Initialize Playwright."""
        try:
            from playwright.sync_api import sync_playwright
            self._playwright = sync_playwright().start()
            return True
        except ImportError:
            logger.error("Playwright not installed. Run: pip install playwright && python -m playwright install chromium")
            return False
        except Exception as e:
            logger.error(f"Failed to start Playwright: {e}")
            return False

    def launch(self) -> Optional[object]:
        """Launch browser with anti-detection args."""
        if not self._playwright:
            if not self.start():
                return None

        try:
            # Anti-detection arguments
            args = self._get_stealth_args()

            self._browser = self._playwright.chromium.launch(
                headless=self.browser_config.headless,
                slow_mow=self.browser_config.slow_mo,
                args=args,
            )
            return self._browser
        except Exception as e:
            logger.error(f"Failed to launch browser: {e}")
            return None

    def _get_stealth_args(self) -> list:
        """Get Chromium arguments for anti-detection."""
        args = [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-accelerated-2d-canvas",
            "--no-first-run",
            "--no-zygote",
            "--disable-gpu",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process",
            "--disable-extensions",
            "--disable-default-apps",
            "--disable-notifications",
            "--disable-sync",
            "--disable-translate",
            "--metrics-recording-only",
            "--mute-audio",
            "--no-default-browser-check",
        ]

        # Randomize window size slightly
        width = self.browser_config.viewport_width + random.randint(-50, 50)
        height = self.browser_config.viewport_height + random.randint(-50, 50)
        args.append(f"--window-size={width},{height}")

        return args

    def new_context(self) -> Optional[object]:
        """Create a new browser context with anti-fingerprinting."""
        if not self._browser:
            self.launch()
            if not self._browser:
                return None

        try:
            # Vary viewport dimensions
            viewport = {
                "width": self.browser_config.viewport_width + random.randint(-100, 100),
                "height": self.browser_config.viewport_height + random.randint(-100, 100),
            }

            user_agent = self._get_random_user_agent()

            self._context = self._browser.new_context(
                viewport=viewport,
                user_agent=user_agent,
                accept_downloads=self.browser_config.accept_downloads,
                locale="en-US",
                timezone_id="America/New_York",
                permissions=["geolocation"],
                color_scheme="light",
                device_scale_factor=random.choice([1, 1.5, 2]),
                has_touch=False,
                is_mobile=False,
            )

            # Add extra headers
            self._context.set_extra_http_headers({
                "Accept-Language": "en-US,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
            })

            return self._context
        except Exception as e:
            logger.error(f"Failed to create context: {e}")
            return None

    def new_page(self) -> Optional[object]:
        """Create a new page and inject stealth scripts."""
        if not self._context:
            self.new_context()
            if not self._context:
                return None

        try:
            self._page = self._context.new_page()

            # Inject stealth scripts
            if self.browser_config.stealth and not self._stealth_scripts_loaded:
                self._inject_stealth_scripts()

            return self._page
        except Exception as e:
            logger.error(f"Failed to create page: {e}")
            return None

    def _inject_stealth_scripts(self):
        """Inject JavaScript to hide automation signals."""
        stealth_scripts = [
            # Remove navigator.webdriver
            """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
                configurable: true
            });
            """,
            # Mock plugins
            """
            Object.defineProperty(navigator, 'plugins', {
                get: () => [
                    { name: 'Chrome PDF Plugin', description: 'Portable Document Format', filename: 'internal-pdf-viewer' },
                    { name: 'Chrome PDF Viewer', description: '', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai' },
                    { name: 'Native Client', description: 'Portable Native Client', filename: 'internal-nacl-plugin' }
                ],
                configurable: true
            });
            """,
            # Mock languages
            """
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en', 'en'],
                configurable: true
            });
            """,
            # Remove automation properties
            """
            window.chrome = { runtime: {}, loadTimes: function() {}, cricket: function() {} };
            """,
            # Remove CDP detection
            """
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
            """,
            # Override permissions
            """
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
            """,
            # Canvas fingerprinting protection
            """
            const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
            HTMLCanvasElement.prototype.toDataURL = function(...args) {
                const ctx = this.getContext('2d');
                if (ctx) {
                    const imageData = ctx.getImageData(0, 0, this.width, this.height);
                    for (let i = 0; i < imageData.data.length; i += 4) {
                        imageData.data[i] += (Math.random() - 0.5) * 0.1;
                    }
                    ctx.putImageData(imageData, 0, 0);
                }
                return originalToDataURL.apply(this, args);
            };
            """,
            # WebGL fingerprinting protection
            """
            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(param) {
                if (param === 37445) return 'Intel Inc. Intel Open Source Technology Center'; // VENDOR
                if (param === 37446) return 'Mesa DRI Intel(R) Ivybridge Mobile'; // RENDERER
                return getParameter.apply(this, arguments);
            };
            """,
        ]

        try:
            for script in stealth_scripts:
                self._page.evaluate(script)
            self._stealth_scripts_loaded = True
            logger.debug("Stealth scripts injected successfully")
        except Exception as e:
            logger.debug(f"Stealth script injection failed: {e}")

    def _get_random_user_agent(self) -> str:
        """Get a random user agent string."""
        config_agents = self.config.get("anti_detection", {}).get("user_agents", [])

        if config_agents:
            return random.choice(config_agents)

        return random.choice([
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        ])

    def navigate_and_wait(
        self,
        url: str,
        wait_selector: Optional[str] = None,
        wait_timeout: int = 30000,
        scroll_count: int = 2,
    ) -> Optional[str]:
        """Navigate to URL and wait for content."""
        if not self._page:
            self.new_page()
            if not self._page:
                return None

        try:
            self._page.goto(url, timeout=wait_timeout, wait_until="domcontentloaded")

            if wait_selector:
                try:
                    self._page.wait_for_selector(wait_selector, timeout=wait_timeout)
                except Exception:
                    pass

            # Human-like behavior
            if self.browser_config.human_behavior:
                self._human_scroll(scroll_count)
                self._human_mouse_movement()

            return self._page.content()

        except Exception as e:
            logger.error(f"Navigation failed: {e}")
            return None

    def _human_scroll(self, count: int = 2):
        """Simulate human-like scrolling."""
        if not self._page:
            return

        try:
            for _ in range(count):
                for _ in range(3):
                    self._page.evaluate(f"window.scrollBy(0, {random.randint(200, 500)})")
                    time.sleep(random.uniform(0.2, 0.5))
                time.sleep(random.uniform(0.3, 0.8))
                self._page.evaluate("window.scrollBy(0, -200)")
                time.sleep(random.uniform(0.1, 0.3))
        except Exception:
            pass

    def _human_mouse_movement(self):
        """Simulate random mouse movements."""
        if not self._page:
            return

        try:
            for _ in range(random.randint(2, 5)):
                x = random.randint(100, 800)
                y = random.randint(100, 600)
                self._page.mouse.move(x, y)
                time.sleep(random.uniform(0.05, 0.15))
        except Exception:
            pass

    def click_element(self, selector: str, timeout: int = 5000) -> bool:
        """Click an element with human-like behavior."""
        if not self._page:
            return False

        try:
            element = self._page.wait_for_selector(selector, timeout=timeout)
            if element:
                element.hover()
                time.sleep(random.uniform(0.1, 0.3))
                box = element.bounding_box()
                if box:
                    offset_x = random.randint(-3, 3)
                    offset_y = random.randint(-3, 3)
                    self._page.mouse.click(
                        box["x"] + box["width"] / 2 + offset_x,
                        box["y"] + box["height"] / 2 + offset_y
                    )
                    return True
        except Exception:
            pass
        return False

    def fill_input(self, selector: str, text: str, typing_delay: float = 0.1):
        """Fill input with human-like typing."""
        if not self._page:
            return

        try:
            element = self._page.wait_for_selector(selector, timeout=5000)
            if element:
                element.click()
                time.sleep(random.uniform(0.1, 0.2))
                element.fill("")
                for char in text:
                    element.type(char, delay=random.uniform(typing_delay * 0.5, typing_delay * 1.5))
        except Exception:
            pass

    def wait_for_navigation(self, timeout: int = 30000) -> bool:
        """Wait for navigation to complete."""
        if not self._page:
            return False
        try:
            self._page.wait_for_load_state("networkidle", timeout=timeout)
            return True
        except Exception:
            return False

    def get_page_html(self) -> Optional[str]:
        """Get current page HTML."""
        if self._page:
            return self._page.content()
        return None

    def take_screenshot(self, path: str, full_page: bool = False):
        """Take screenshot of current page."""
        if self._page:
            self._page.screenshot(path=path, full_page=full_page)

    def close(self):
        """Clean up browser resources."""
        try:
            if self._page:
                self._page.close()
                self._page = None
            if self._context:
                self._context.close()
                self._context = None
            if self._browser:
                self._browser.close()
                self._browser = None
            if self._playwright:
                self._playwright.stop()
                self._playwright = None
            self._stealth_scripts_loaded = False
        except Exception as e:
            logger.debug(f"Cleanup error: {e}")

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


# Backwards compatibility alias
BrowserManager = BuiltInStealthBrowser
