"""Structured logging configuration for DataEngineX.

Uses **structlog** as the sole logging backend.  All stdlib ``logging``
output is intercepted and rendered through structlog so that every log
line — regardless of origin — gets the same formatting and sink
configuration.

The key design constraint: structlog must use ``PrintLoggerFactory`` (direct
stdout write) rather than ``stdlib.LoggerFactory`` to avoid re-entering the
``_InterceptHandler`` and causing infinite recursion.

Functions:
    configure_logging: Configure structlog sinks.
    get_logger: Obtain a configured ``structlog.BoundLogger``.
    add_app_context: Structlog processor adding app name and version.

Constants:
    APP_VERSION: Current application version.
    APP_NAME: Application name (from ``$APP_NAME`` or ``"dataenginex"``).
"""

from __future__ import annotations

import logging
import os
from typing import Any, cast

import structlog
from structlog.types import EventDict, Processor

__all__ = [
    "APP_NAME",
    "APP_VERSION",
    "add_app_context",
    "configure_logging",
    "get_logger",
]

try:
    from importlib.metadata import version as get_version

    APP_VERSION = get_version("dataenginex")
except Exception:
    APP_VERSION = os.getenv("APP_VERSION", "unknown")

APP_NAME = os.getenv("APP_NAME", "dataenginex")


# ---------------------------------------------------------------------------
# Intercept stdlib logging → structlog
# ---------------------------------------------------------------------------


class _InterceptHandler(logging.Handler):
    """Route third-party stdlib ``logging`` calls into **structlog**.

    Uses structlog's bound logger directly — structlog is configured with
    ``PrintLoggerFactory`` so no stdlib ``logging`` call is made, which
    avoids the infinite-recursion loop that occurs with ``LoggerFactory``.
    """

    def emit(self, record: logging.LogRecord) -> None:  # noqa: D102
        from collections.abc import Callable  # noqa: PLC0415

        level = record.levelname.lower()
        bound = structlog.get_logger(record.name)
        log_fn: Callable[..., None] = getattr(bound, level, bound.info)
        log_fn(record.getMessage(), exc_info=record.exc_info or None)


def add_app_context(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Add application context to log entries."""
    event_dict["app"] = APP_NAME
    event_dict["version"] = APP_VERSION
    return event_dict


def configure_logging(log_level: str = "INFO", json_logs: bool = True) -> None:
    """Configure structlog for the application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_logs: If True, output JSON logs; otherwise use coloured console
    """
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Route all stdlib logging through our intercept handler.
    # Set stdlib root to WARNING so that structlog's own internal calls
    # (which may touch stdlib) don't re-enter the handler.
    logging.basicConfig(
        handlers=[_InterceptHandler()],
        level=numeric_level,
        force=True,
    )

    processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        add_app_context,
        structlog.processors.StackInfoRenderer(),
    ]

    if json_logs:
        processors.append(structlog.processors.format_exc_info)
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    # Use PrintLoggerFactory (direct stdout) — NOT stdlib.LoggerFactory.
    # stdlib.LoggerFactory routes back through logging.Logger which triggers
    # _InterceptHandler again, causing infinite recursion.
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a configured structlog logger instance.

    Args:
        name: Logger name (typically ``__name__`` of the calling module)

    Returns:
        Configured structlog logger
    """
    return cast(structlog.stdlib.BoundLogger, structlog.get_logger(name))
