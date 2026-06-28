import re
from datetime import UTC, datetime
from pathlib import Path

import typer

from pokebuy.config import Settings

SENSITIVE_HEADER_NAMES = {
    "authorization",
    "cookie",
    "proxy-authorization",
    "set-cookie",
}

SENSITIVE_HTML_PATTERNS = [
    re.compile(r"('cookie'\s*:\s*')[^']+(')", re.IGNORECASE),
    re.compile(r'("cookie"\s*:\s*")[^"]+(")', re.IGNORECASE),
]


def redact_headers(headers: dict[str, str]) -> dict[str, str]:
    return {
        key: "[redacted]" if key.lower() in SENSITIVE_HEADER_NAMES else value
        for key, value in headers.items()
    }


def redact_debug_html(html: str) -> str:
    redacted = html
    for pattern in SENSITIVE_HTML_PATTERNS:
        redacted = pattern.sub(r"\1[redacted]\2", redacted)
    return redacted


def write_debug_artifact(
    settings: Settings,
    *,
    prefix: str,
    suffix: str,
    content: str,
    redact: bool = False,
) -> Path | None:
    if not settings.debug_enabled:
        return None

    settings.debug_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ")
    safe_prefix = re.sub(r"[^A-Za-z0-9_.-]+", "-", prefix).strip("-") or "artifact"
    path = settings.debug_dir / f"{timestamp}-{safe_prefix}{suffix}"
    path.write_text(redact_debug_html(content) if redact else content, encoding="utf-8")
    return path


def maybe_print_debug_html(settings: Settings, html: str) -> None:
    if not settings.debug_enabled or not settings.debug_print_html:
        return

    output = redact_debug_html(html) if settings.debug_redact_html else html
    typer.echo("----- POKEBUY DEBUG HTML BEGIN -----", err=True)
    typer.echo(output, err=True)
    typer.echo("----- POKEBUY DEBUG HTML END -----", err=True)
