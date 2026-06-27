import logging
import sys
from typing import Any, cast

import structlog
from structlog.typing import FilteringBoundLogger


def configure_logging(level: str = "INFO") -> None:
    """Configure structured console logging for local development and services."""

    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=level.upper())
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
        cache_logger_on_first_use=True,
    )


def get_logger(name: str, **context: Any) -> FilteringBoundLogger:
    return cast(FilteringBoundLogger, structlog.get_logger(name).bind(**context))
