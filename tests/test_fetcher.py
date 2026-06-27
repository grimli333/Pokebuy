import os
import pytest

from pokebuy.collectors.browser import PokemonCenterBrowserFetcher
from pokebuy.collectors.fetcher import is_blocked_response
from pokebuy.config import Settings


def test_detects_datadome_blocked_page_without_403() -> None:
    assert is_blocked_response(
        200,
        {},
        "<html>Please enable JavaScript<script src='https://ct.captcha-delivery.com/c.js'></script>",
    )


@pytest.mark.skipif(
    not os.path.exists("/Applications/Google Chrome.app") and not os.environ.get("CHROME_PATH"),
    reason="Google Chrome not installed",
)
def test_browser_fetcher_about_blank() -> None:
    settings = Settings()
    fetcher = PokemonCenterBrowserFetcher(settings, headless=True)
    res = fetcher.fetch("about:blank")
    # since about:blank does not trigger network, status code might be None, but it should succeed
    assert res.fetch_status.value == "success"
    assert "about:blank" in res.url


@pytest.mark.skipif(
    not os.path.exists("/Applications/Google Chrome.app") and not os.environ.get("CHROME_PATH"),
    reason="Google Chrome not installed",
)
def test_browser_fetcher_live_httpbin() -> None:
    settings = Settings()
    fetcher = PokemonCenterBrowserFetcher(settings, headless=True)
    res = fetcher.fetch("https://httpbin.org/html")
    assert res.status_code == 200
    assert res.fetch_status.value == "success"
    assert "httpbin.org" in res.url
    assert "h1" in res.text.lower()
