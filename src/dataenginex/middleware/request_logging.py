"""FastAPI middleware for request tracking and logging.

Provides ``RequestLoggingMiddleware`` that generates a unique
``X-Request-ID`` for each request, binds structured context via
``structlog.contextvars``, and logs request start/completion events.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Callable
from typing import Any, cast

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from structlog.contextvars import bind_contextvars, clear_contextvars

__all__ = [
    "RequestLoggingMiddleware",
]


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all HTTP requests with request ID tracking."""

    def __init__(self, app: Callable[..., Any]) -> None:
        """Initialize middleware."""
        super().__init__(app)
        self.logger = structlog.get_logger(__name__)

    async def dispatch(self, request: Request, call_next: Callable[..., Any]) -> Response:
        """Process request and add logging context."""
        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # Bind context for this request
        clear_contextvars()
        bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            client_host=request.client.host if request.client else None,
        )

        # Log request start
        start_time = time.time()
        self.logger.info(
            "request_started",
            query_params=dict(request.query_params),
        )

        try:
            # Process request
            response = await call_next(request)

            # Calculate duration
            duration = time.time() - start_time

            # Log successful response
            self.logger.info(
                "request_completed",
                status_code=response.status_code,
                duration_seconds=round(duration, 3),
            )

            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id

            return cast(Response, response)

        except Exception as exc:
            # Log error
            duration = time.time() - start_time
            self.logger.error(
                "request_failed",
                error=str(exc),
                error_type=type(exc).__name__,
                duration_seconds=round(duration, 3),
                exc_info=True,
            )
            raise

        finally:
            # Clear context
            clear_contextvars()
