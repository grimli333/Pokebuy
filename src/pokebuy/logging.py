import logging
import sys
from pathlib import Path
from typing import Any, cast

import structlog
from structlog.typing import FilteringBoundLogger


def configure_logging(
    level: str = "INFO",
    *,
    log_file_enabled: bool = False,
    log_file_path: Path | None = None,
) -> None:
    """Configure structured console logging for local development and services."""

    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stderr)]
    if log_file_enabled:
        path = log_file_path or Path("pokebuy.log")
        path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(path, encoding="utf-8"))

    logging.basicConfig(
        format="%(message)s",
        handlers=handlers,
        level=level.upper(),
        force=True,
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(level.upper()),
        ),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=False,
    )


def get_logger(name: str, **context: Any) -> FilteringBoundLogger:
    return cast(FilteringBoundLogger, structlog.get_logger(name, **context))
