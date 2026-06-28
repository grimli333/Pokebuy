import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Protocol, cast

from curl_cffi import requests as curl_requests

from pokebuy.config import Settings
from pokebuy.debug import redact_headers, write_debug_artifact
from pokebuy.logging import get_logger
from pokebuy.models import FetchStatus


@dataclass(frozen=True)
class FetchResult:
    url: str
    status_code: int | None
    text: str
    fetch_status: FetchStatus
    fetch_error: str | None
    headers: dict[str, str]


class HttpResponse(Protocol):
    status_code: int
    text: str
    headers: Mapping[object, object]
    url: object


class RequestFunc(Protocol):
    def __call__(
        self,
        url: str,
        *,
        impersonate: str,
        headers: dict[str, str],
        timeout: float,
        allow_redirects: bool,
    ) -> HttpResponse:
        pass


SleepFunc = Callable[[float], None]

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
LOGGER = get_logger("pokebuy.collectors.fetcher")


class PokemonCenterFetcher:
    def __init__(
        self,
        settings: Settings,
        *,
        request_get: RequestFunc | None = None,
        sleep: SleepFunc | None = None,
    ) -> None:
        self._settings = settings
        self._request_get = request_get or cast(RequestFunc, curl_requests.get)
        self._sleep = sleep or time.sleep

    def fetch(self, url: str) -> FetchResult:
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        max_attempts = self._settings.http_max_attempts
        last_error: str | None = None
        LOGGER.debug("http_fetch_start", url=url, max_attempts=max_attempts)

        for attempt in range(1, max_attempts + 1):
            try:
                LOGGER.debug("http_fetch_attempt", url=url, attempt=attempt)
                response = self._request_get(
                    url,
                    impersonate="chrome",
                    headers=headers,
                    timeout=self._settings.http_timeout_seconds,
                    allow_redirects=True,
                )
            except Exception as exc:
                last_error = str(exc)
                LOGGER.debug("http_fetch_exception", url=url, attempt=attempt, error=last_error)
                if attempt >= max_attempts:
                    return FetchResult(
                        url=url,
                        status_code=None,
                        text="",
                        fetch_status=FetchStatus.ERROR,
                        fetch_error=last_error,
                        headers={},
                    )
                delay = self._retry_delay(attempt, {})
                LOGGER.debug("http_fetch_retry_sleep", url=url, attempt=attempt, delay=delay)
                self._sleep(delay)
                continue

            response_headers = {
                str(k): str(v) for k, v in response.headers.items() if v is not None
            }
            html_path = write_debug_artifact(
                self._settings,
                prefix=f"http-{attempt}-{response.status_code}",
                suffix=".html",
                content=response.text,
                redact=self._settings.debug_redact_html,
            )
            LOGGER.debug(
                "http_fetch_response",
                url=str(response.url),
                attempt=attempt,
                status_code=response.status_code,
                headers=redact_headers(response_headers),
                body_length=len(response.text),
                debug_html_path=str(html_path) if html_path else None,
            )
            blocked = is_blocked_response(response.status_code, response_headers, response.text)
            if blocked:
                LOGGER.debug(
                    "http_fetch_blocked",
                    url=str(response.url),
                    status_code=response.status_code,
                )
                return FetchResult(
                    url=str(response.url),
                    status_code=response.status_code,
                    text=response.text,
                    fetch_status=FetchStatus.BLOCKED,
                    fetch_error="Pokemon Center returned bot-protection or CAPTCHA HTML",
                    headers=response_headers,
                )
            if response.status_code == 404:
                LOGGER.debug("http_fetch_not_found", url=str(response.url))
                return FetchResult(
                    url=str(response.url),
                    status_code=response.status_code,
                    text=response.text,
                    fetch_status=FetchStatus.NOT_FOUND,
                    fetch_error="product page returned 404",
                    headers=response_headers,
                )
            if response.status_code in RETRYABLE_STATUS_CODES and attempt < max_attempts:
                delay = self._retry_delay(attempt, response_headers)
                LOGGER.debug(
                    "http_fetch_retryable_status",
                    url=str(response.url),
                    attempt=attempt,
                    status_code=response.status_code,
                    delay=delay,
                )
                self._sleep(delay)
                continue
            if response.status_code >= 400:
                LOGGER.debug(
                    "http_fetch_error_status",
                    url=str(response.url),
                    status_code=response.status_code,
                )
                return FetchResult(
                    url=str(response.url),
                    status_code=response.status_code,
                    text=response.text,
                    fetch_status=FetchStatus.ERROR,
                    fetch_error=f"product page returned HTTP {response.status_code}",
                    headers=response_headers,
                )
            LOGGER.debug(
                "http_fetch_success",
                url=str(response.url),
                status_code=response.status_code,
            )
            return FetchResult(
                url=str(response.url),
                status_code=response.status_code,
                text=response.text,
                fetch_status=FetchStatus.SUCCESS,
                fetch_error=None,
                headers=response_headers,
            )

        return FetchResult(
            url=url,
            status_code=None,
            text="",
            fetch_status=FetchStatus.ERROR,
            fetch_error=last_error or "fetch failed without a response",
            headers={},
        )

    def _retry_delay(self, attempt: int, headers: dict[str, str]) -> float:
        retry_after = parse_retry_after_seconds(headers.get("Retry-After"))
        if retry_after is not None:
            return min(retry_after, self._settings.http_retry_after_max_seconds)
        return float(self._settings.http_retry_backoff_seconds * (2 ** (attempt - 1)))


def is_blocked_response(status_code: int, headers: dict[str, str], body: str) -> bool:
    lower_headers = {key.lower(): value for key, value in headers.items()}
    lower_body = body.lower()
    has_block_evidence = (
        "x-datadome" in lower_headers
        or "captcha-delivery.com" in lower_body
        or "please enable js" in lower_body
        or "enable javascript" in lower_body
        or "pardon our interruption" in lower_body
    )
    return has_block_evidence or status_code == 403


def parse_retry_after_seconds(value: str | None) -> float | None:
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        return None
    try:
        return max(0.0, float(stripped))
    except ValueError:
        pass

    try:
        retry_at = parsedate_to_datetime(stripped)
    except (TypeError, ValueError):
        return None
    if retry_at.tzinfo is None:
        retry_at = retry_at.replace(tzinfo=UTC)
    return max(0.0, (retry_at - datetime.now(UTC)).total_seconds())
