from dataclasses import dataclass

import httpx

from pokebuy.config import Settings
from pokebuy.models import FetchStatus


@dataclass(frozen=True)
class FetchResult:
    url: str
    status_code: int | None
    text: str
    fetch_status: FetchStatus
    fetch_error: str | None
    headers: dict[str, str]


class PokemonCenterFetcher:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def fetch(self, url: str) -> FetchResult:
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"
            ),
        }
        try:
            with httpx.Client(
                follow_redirects=True,
                timeout=self._settings.http_timeout_seconds,
                headers=headers,
            ) as client:
                response = client.get(url)
        except httpx.HTTPError as exc:
            return FetchResult(
                url=url,
                status_code=None,
                text="",
                fetch_status=FetchStatus.ERROR,
                fetch_error=str(exc),
                headers={},
            )

        response_headers = dict(response.headers)
        blocked = is_blocked_response(response.status_code, response_headers, response.text)
        if blocked:
            return FetchResult(
                url=str(response.url),
                status_code=response.status_code,
                text=response.text,
                fetch_status=FetchStatus.BLOCKED,
                fetch_error="Pokemon Center returned bot-protection or CAPTCHA HTML",
                headers=response_headers,
            )
        if response.status_code == 404:
            return FetchResult(
                url=str(response.url),
                status_code=response.status_code,
                text=response.text,
                fetch_status=FetchStatus.NOT_FOUND,
                fetch_error="product page returned 404",
                headers=response_headers,
            )
        if response.is_error:
            return FetchResult(
                url=str(response.url),
                status_code=response.status_code,
                text=response.text,
                fetch_status=FetchStatus.ERROR,
                fetch_error=f"product page returned HTTP {response.status_code}",
                headers=response_headers,
            )
        return FetchResult(
            url=str(response.url),
            status_code=response.status_code,
            text=response.text,
            fetch_status=FetchStatus.SUCCESS,
            fetch_error=None,
            headers=response_headers,
        )


def is_blocked_response(status_code: int, headers: dict[str, str], body: str) -> bool:
    lower_headers = {key.lower(): value for key, value in headers.items()}
    lower_body = body.lower()
    return status_code == 403 and (
        "x-datadome" in lower_headers
        or "captcha-delivery.com" in lower_body
        or "please enable js" in lower_body
        or "datadome" in lower_body
    )
