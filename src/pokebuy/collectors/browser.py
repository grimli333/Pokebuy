from playwright.sync_api import BrowserContext, Playwright, sync_playwright
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from pokebuy.collectors.fetcher import FetchResult, is_blocked_response
from pokebuy.config import Settings
from pokebuy.models import FetchStatus


class PokemonCenterBrowserFetcher:
    def __init__(
        self,
        settings: Settings,
        *,
        headless: bool | None = None,
        manual_wait_seconds: float | None = None,
        use_persistent_profile: bool = False,
    ) -> None:
        self._settings = settings
        self._headless = settings.browser_headless if headless is None else headless
        self._manual_wait_seconds = (
            settings.browser_manual_wait_seconds
            if manual_wait_seconds is None
            else manual_wait_seconds
        )
        self._use_persistent_profile = use_persistent_profile

    def fetch(self, url: str) -> FetchResult:
        timeout_ms = self._settings.browser_timeout_seconds * 1000
        try:
            with sync_playwright() as playwright:
                context = self._new_context(playwright, timeout_ms)
                try:
                    page = context.new_page()
                    response = page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
                    try:
                        page.wait_for_load_state("networkidle", timeout=timeout_ms)
                    except PlaywrightTimeoutError:
                        pass
                    if self._manual_wait_seconds > 0:
                        page.wait_for_timeout(self._manual_wait_seconds * 1000)
                    html = page.content()
                    final_url = page.url
                    status_code = response.status if response else None
                    headers = response.headers if response else {}
                finally:
                    context.close()
        except PlaywrightError as exc:
            return FetchResult(
                url=url,
                status_code=None,
                text="",
                fetch_status=FetchStatus.ERROR,
                fetch_error=f"browser fetch failed: {_first_error_line(exc)}",
                headers={},
            )

        if status_code == 404:
            return FetchResult(
                url=final_url,
                status_code=status_code,
                text=html,
                fetch_status=FetchStatus.NOT_FOUND,
                fetch_error="product page returned 404",
                headers=headers,
            )
        if status_code is not None and is_blocked_response(status_code, headers, html):
            return FetchResult(
                url=final_url,
                status_code=status_code,
                text=html,
                fetch_status=FetchStatus.BLOCKED,
                fetch_error="Pokemon Center returned bot-protection or CAPTCHA HTML",
                headers=headers,
            )
        if status_code is not None and status_code >= 400:
            return FetchResult(
                url=final_url,
                status_code=status_code,
                text=html,
                fetch_status=FetchStatus.ERROR,
                fetch_error=f"product page returned HTTP {status_code}",
                headers=headers,
            )
        return FetchResult(
            url=final_url,
            status_code=status_code,
            text=html,
            fetch_status=FetchStatus.SUCCESS,
            fetch_error=None,
            headers=headers,
        )

    def _new_context(self, playwright: Playwright, timeout_ms: float) -> BrowserContext:
        chromium = playwright.chromium
        user_agent = (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"
        )
        if self._use_persistent_profile:
            self._settings.browser_profile_dir.mkdir(parents=True, exist_ok=True)
            return chromium.launch_persistent_context(
                user_data_dir=str(self._settings.browser_profile_dir),
                executable_path=chromium.executable_path,
                headless=self._headless,
                timeout=timeout_ms,
                user_agent=user_agent,
                locale="en-US",
            )

        browser = chromium.launch(
            executable_path=chromium.executable_path,
            headless=self._headless,
            timeout=timeout_ms,
        )
        return browser.new_context(user_agent=user_agent, locale="en-US")


def warm_pokemon_center_session(
    settings: Settings,
    *,
    url: str,
    headless: bool | None = None,
    manual_wait_seconds: float = 300.0,
) -> str:
    headless_value = settings.browser_headless if headless is None else headless
    timeout_ms = settings.browser_timeout_seconds * 1000
    settings.browser_profile_dir.mkdir(parents=True, exist_ok=True)
    settings.browser_state_dir.mkdir(parents=True, exist_ok=True)
    storage_state_path = settings.browser_state_dir / "pokemon-center-storage-state.json"

    try:
        with sync_playwright() as playwright:
            context = playwright.chromium.launch_persistent_context(
                user_data_dir=str(settings.browser_profile_dir),
                executable_path=playwright.chromium.executable_path,
                headless=headless_value,
                timeout=timeout_ms,
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"
                ),
                locale="en-US",
            )
            try:
                page = context.new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
                if manual_wait_seconds > 0:
                    page.wait_for_timeout(manual_wait_seconds * 1000)
                context.storage_state(path=str(storage_state_path))
            finally:
                context.close()
    except PlaywrightError as exc:
        return f"session warm failed: {_first_error_line(exc)}"

    return (
        f"saved browser profile at {settings.browser_profile_dir}; "
        f"storage state at {storage_state_path}"
    )


def _first_error_line(exc: PlaywrightError) -> str:
    first_line = str(exc).splitlines()[0].strip()
    if "Executable doesn't exist" in first_line:
        return "Playwright browser executable is missing; run `uv run playwright install chromium`"
    return first_line
