import os
from dataclasses import dataclass
from typing import cast

import pytest

from pokebuy.collectors.browser import PokemonCenterBrowserFetcher
from pokebuy.collectors.fetcher import PokemonCenterFetcher, RequestFunc, is_blocked_response
from pokebuy.config import Settings


@dataclass(frozen=True)
class FakeResponse:
    status_code: int
    text: str = "<html>ok</html>"
    headers: dict[str, str] | None = None
    url: str = "https://www.pokemoncenter.com/product/10-1/example"

    def __post_init__(self) -> None:
        if self.headers is None:
            object.__setattr__(self, "headers", {})


def test_detects_datadome_blocked_page_without_403() -> None:
    assert is_blocked_response(
        200,
        {},
        "<html>Please enable JavaScript<script src='https://ct.captcha-delivery.com/c.js'></script>",
    )


def test_allows_product_page_with_datadome_asset_reference() -> None:
    html = """
    <html>
      <head>
        <link rel="preconnect" href="//js.datadome.co">
        <script type="application/ld+json">
          {"@type": "Product", "offers": {"availability": "http://schema.org/OutOfStock"}}
        </script>
      </head>
      <body>Pokemon Center product page</body>
    </html>
    """

    assert not is_blocked_response(200, {}, html)


def test_fetcher_retries_retryable_status() -> None:
    responses = [
        FakeResponse(503, headers={"Retry-After": "2"}),
        FakeResponse(200, text="<html>ok after retry</html>"),
    ]
    sleeps: list[float] = []

    def fake_get(*_args: object, **_kwargs: object) -> FakeResponse:
        return responses.pop(0)

    fetcher = PokemonCenterFetcher(
        Settings(http_max_attempts=2),
        request_get=cast(RequestFunc, fake_get),
        sleep=sleeps.append,
    )

    result = fetcher.fetch("https://www.pokemoncenter.com/product/10-1/example")

    assert result.fetch_status.value == "success"
    assert result.text == "<html>ok after retry</html>"
    assert sleeps == [2.0]


def test_fetcher_does_not_retry_blocked_response() -> None:
    calls = 0

    def fake_get(*_args: object, **_kwargs: object) -> FakeResponse:
        nonlocal calls
        calls += 1
        return FakeResponse(
            403,
            text="<html>Please enable JS<script src='https://ct.captcha-delivery.com/c.js'></script>",
        )

    fetcher = PokemonCenterFetcher(
        Settings(http_max_attempts=3),
        request_get=cast(RequestFunc, fake_get),
        sleep=lambda _delay: None,
    )

    result = fetcher.fetch("https://www.pokemoncenter.com/product/10-1/example")

    assert result.fetch_status.value == "blocked"
    assert calls == 1


def test_fetcher_retries_exceptions_with_backoff() -> None:
    calls = 0
    sleeps: list[float] = []

    def fake_get(*_args: object, **_kwargs: object) -> FakeResponse:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("temporary network failure")
        return FakeResponse(200, text="<html>recovered</html>")

    fetcher = PokemonCenterFetcher(
        Settings(http_max_attempts=2, http_retry_backoff_seconds=0.5),
        request_get=cast(RequestFunc, fake_get),
        sleep=sleeps.append,
    )

    result = fetcher.fetch("https://www.pokemoncenter.com/product/10-1/example")

    assert result.fetch_status.value == "success"
    assert result.text == "<html>recovered</html>"
    assert sleeps == [0.5]


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
