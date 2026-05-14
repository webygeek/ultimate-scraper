"""
JavaScript Injection - Custom JS scripts for page manipulation.
"""
from typing import List, Dict, Any, Optional
from loguru import logger


class JSInjector:
    """
    Inject custom JavaScript into pages.
    """

    # Built-in scripts
    BUILT_IN_SCRIPTS = {
        "scroll": """
            async function scrollToBottom() {
                await new Promise(resolve => {
                    let totalHeight = 0;
                    const distance = 100;
                    const timer = setInterval(() => {
                        const scrollHeight = document.body.scrollHeight;
                        window.scrollBy(0, distance);
                        totalHeight += distance;
                        if(totalHeight >= scrollHeight) {
                            clearInterval(timer);
                            resolve();
                        }
                    }, 100);
                });
            }
            scrollToBottom();
        """,

        "lazy_load": """
            async function triggerLazyLoad() {
                window.scrollTo(0, 0);
                await new Promise(resolve => {
                    let count = 0;
                    const timer = setInterval(() => {
                        window.scrollBy(0, 500);
                        count++;
                        if (count > 20) {
                            clearInterval(timer);
                            resolve();
                        }
                    }, 200);
                });
            }
            triggerLazyLoad();
        """,

        "click_modals": """
            async function closeModals() {
                const modalSelectors = [
                    '[class*="modal"] button',
                    '[class*="popup"] button',
                    '[class*="close"]',
                    '[aria-label="close"]',
                    '.cookie-accept',
                    '[class*="consent"] button',
                ];
                for (const selector of modalSelectors) {
                    const buttons = document.querySelectorAll(selector);
                    buttons.forEach(btn => btn.click());
                }
            }
            closeModals();
        """,

        "accept_cookies": """
            async function acceptCookies() {
                const selectors = [
                    '[class*="cookie"] button',
                    '[class*="consent"] button',
                    '#onetrust-accept-btn-handler',
                    '.cookie-consent-accept',
                    '[aria-label="Accept cookies"]',
                ];
                for (const selector of selectors) {
                    const btn = document.querySelector(selector);
                    if (btn) btn.click();
                }
            }
            acceptCookies();
        """,

        "expand_comments": """
            async function expandComments() {
                const selectors = [
                    '[class*="more"]',
                    '[class*="show"]',
                    '[class*="reply"]',
                    '[class*="expand"]',
                ];
                for (const selector of selectors) {
                    const buttons = document.querySelectorAll(selector);
                    buttons.forEach(btn => btn.click());
                }
            }
            expandComments();
        """,

        "remove_popups": """
            function removePopups() {
                const selectors = [
                    '[class*="popup"]',
                    '[class*="modal"]',
                    '[class*="overlay"]',
                    '[class*="banner"]',
                ];
                selectors.forEach(sel => {
                    document.querySelectorAll(sel).forEach(el => el.remove());
                });
            }
            removePopups();
        """,

        "get_page_height": """
            return document.body.scrollHeight;
        """,

        "get_all_links": """
            return Array.from(document.querySelectorAll('a[href]')).map(a => ({
                href: a.href,
                text: a.textContent.trim(),
                visible: a.offsetParent !== null
            }));
        """,

        "get_form_fields": """
            return Array.from(document.querySelectorAll('input, textarea, select')).map(el => ({
                name: el.name,
                type: el.type || el.tagName,
                id: el.id,
                class: el.className,
                value: el.value,
                required: el.required
            }));
        """,

        "wait_for_content": """
            async function waitForContent(selector) {
                const start = Date.now();
                while (Date.now() - start < 10000) {
                    const el = document.querySelector(selector);
                    if (el) return true;
                    await new Promise(r => setTimeout(r, 100));
                }
                return false;
            }
            return waitForContent(arguments[0]);
        """,

        "inject_credentials": """
            function injectCredentials(username, password) {
                const usernameField = document.querySelector('input[type="text"], input[type="email"]');
                const passwordField = document.querySelector('input[type="password"]');
                if (usernameField) {
                    usernameField.value = username;
                    usernameField.dispatchEvent(new Event('input', { bubbles: true }));
                }
                if (passwordField) {
                    passwordField.value = password;
                    passwordField.dispatchEvent(new Event('input', { bubbles: true }));
                }
            }
            injectCredentials(arguments[0], arguments[1]);
        """,
    }

    def __init__(self):
        self.custom_scripts: Dict[str, str] = {}

    def add_script(self, name: str, script: str):
        """Add a custom script."""
        self.custom_scripts[name] = script

    def get_script(self, name: str) -> Optional[str]:
        """Get a script by name."""
        if name in self.custom_scripts:
            return self.custom_scripts[name]
        if name in self.BUILT_IN_SCRIPTS:
            return self.BUILT_IN_SCRIPTS[name]
        return None

    def run_script(
        self,
        page: Any,
        script_name: str,
        *args,
    ) -> Any:
        """Run a script in a browser page."""
        script = self.get_script(script_name)
        if not script:
            logger.warning(f"Script not found: {script_name}")
            return None

        try:
            result = page.evaluate(script, *args)
            return result
        except Exception as e:
            logger.error(f"Script execution failed: {e}")
            return None

    def run_multiple(
        self,
        page: Any,
        script_names: List[str],
        delay: float = 0.5,
    ):
        """Run multiple scripts in sequence."""
        import asyncio

        results = []
        for name in script_names:
            result = self.run_script(page, name)
            results.append(result)
            if delay > 0:
                page.wait_for_timeout(int(delay * 1000))
        return results

    def create_scroll_script(
        self,
        scroll_count: int = 3,
        distance: int = 300,
        delay: int = 500,
    ) -> str:
        """Create custom scroll script."""
        return f"""
            async function scrollPage() {{
                for (let i = 0; i < {scroll_count}; i++) {{
                    window.scrollBy(0, {distance});
                    await new Promise(r => setTimeout(r, {delay}));
                }}
            }}
            scrollPage();
        """

    def create_click_script(self, selector: str) -> str:
        """Create script to click element."""
        return f"""
            const el = document.querySelector('{selector}');
            if (el) el.click();
        """

    def create_type_script(self, selector: str, text: str) -> str:
        """Create script to type into element."""
        escaped_text = text.replace("'", "\\'")
        return f"""
            const el = document.querySelector('{selector}');
            if (el) {{
                el.value = '{escaped_text}';
                el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                el.dispatchEvent(new Event('change', {{ bubbles: true }}));
            }}
        """

    def create_wait_script(self, selector: str, timeout: int = 10000) -> str:
        """Create script to wait for element."""
        return f"""
            async function waitForElement() {{
                const start = Date.now();
                while (Date.now() - start < {timeout}) {{
                    if (document.querySelector('{selector}')) return true;
                    await new Promise(r => setTimeout(r, 100));
                }}
                return false;
            }}
            return waitForElement();
        """

    def create_screenshot_script(self, full_page: bool = False) -> str:
        """Create screenshot capture script."""
        return f"""
            return document.body.scrollHeight;
        """


class CDPBrowser:
    """
    Chrome DevTools Protocol browser for advanced control.
    """

    def __init__(self, config: Dict = None):
        self.config = config or {}

    async def launch(self, headless: bool = True):
        """Launch browser with CDP."""
        try:
            from playwright.sync_api import sync_playwright

            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(headless=headless)
            self.context = self.browser.new_context()
            self.page = self.context.new_page()
            return True
        except Exception as e:
            logger.error(f"Browser launch failed: {e}")
            return False

    def navigate(self, url: str):
        """Navigate to URL."""
        if self.page:
            self.page.goto(url, wait_until="networkidle")

    def execute_cdp(self, command: str, **params):
        """Execute CDP command."""
        if self.page:
            try:
                return self.page.evaluate(f"""
                    async () => {{
                        const result = await window.__playwright_cdp__(
                            '{command}',
                            {json.dumps(params)}
                        );
                        return result;
                    }}
                """)
            except:
                pass
        return None

    def set_geolocation(self, latitude: float, longitude: float):
        """Set geolocation."""
        if self.context:
            self.context.set_geolocation({
                "latitude": latitude,
                "longitude": longitude,
            })

    def set_timezone(self, timezone: str):
        """Set timezone."""
        if self.context:
            self.context.set_timezone(timezone)

    def set_locale(self, locale: str):
        """Set locale."""
        if self.context:
            self.context.set_locale(locale)

    def inject_js(self, script: str):
        """Inject JavaScript."""
        if self.page:
            self.page.evaluate(script)

    def close(self):
        """Close browser."""
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
