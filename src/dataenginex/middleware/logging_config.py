"""Structured logging configuration for DataEngineX.

Uses **loguru** as the primary logging backend, integrated with **structlog**
for structured context in the FastAPI application.  All stdlib ``logging``
output is intercepted and routed through loguru so that every log line—
regardless of origin—gets the same formatting and sink configuration.

Functions:
    configure_logging: Configure loguru + structlog sinks.
    get_logger: Obtain a configured ``structlog.BoundLogger``.
    add_app_context: Structlog processor adding app name and version.

Constants:
    APP_VERSION: Current application version.
    APP_NAME: Application name (from ``$APP_NAME`` or ``"dataenginex"``).
"""

from __future__ import annotations

import logging
import os
import sys
from types import FrameType
from typing import Any, cast

import structlog
from loguru import logger as _loguru_logger
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
# Intercept stdlib logging → loguru
# ---------------------------------------------------------------------------


class _InterceptHandler(logging.Handler):
    """Route all stdlib ``logging`` calls into **loguru**.

    This ensures third-party libraries that use ``logging.getLogger``
    (e.g. uvicorn, httpx) also appear in loguru output.
    """

    def emit(self, record: logging.LogRecord) -> None:  # noqa: D102
        # Map stdlib level to loguru level name
        try:
            level = _loguru_logger.level(record.levelname).name
        except ValueError:
            level = str(record.levelno)

        # Find caller from where the logged message originated
        frame: FrameType | None = logging.currentframe()
        depth = 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        _loguru_logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def add_app_context(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Add application context to log entries."""
    event_dict["app"] = APP_NAME
    event_dict["version"] = APP_VERSION
    return event_dict


def configure_logging(log_level: str = "INFO", json_logs: bool = True) -> None:
    """Configure loguru + structlog for the application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_logs: If True, output JSON logs; otherwise use coloured console
    """
    # -- loguru sink ---------------------------------------------------------
    _loguru_logger.remove()  # Drop default stderr handler

    if json_logs:
        _loguru_logger.add(
            sys.stdout,
            level=log_level.upper(),
            serialize=True,  # JSON output
            backtrace=False,
            diagnose=False,
        )
    else:
        _loguru_logger.add(
            sys.stdout,
            level=log_level.upper(),
            format=(
                "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
                "<level>{message}</level>"
            ),
            colorize=True,
        )

    # -- Intercept stdlib logging → loguru -----------------------------------
    logging.basicConfig(handlers=[_InterceptHandler()], level=0, force=True)

    # -- structlog (for FastAPI middleware / structured context) --------------
    processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
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

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, log_level.upper())),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
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
