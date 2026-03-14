"""Middleware for Prometheus metrics collection.

Provides ``PrometheusMetricsMiddleware`` that automatically records
request counts, durations, in-flight gauges, and exception counters
for every HTTP request (except ``/metrics`` itself).
"""

from __future__ import annotations

import os
import time
from collections.abc import Callable
from typing import Any, cast

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from .metrics import (
    http_exceptions_total,
    http_request_duration_seconds,
    http_requests_in_flight,
    http_requests_total,
)

__all__ = [
    "PrometheusMetricsMiddleware",
]


class PrometheusMetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to collect Prometheus metrics for HTTP requests."""

    async def dispatch(self, request: Request, call_next: Callable[..., Any]) -> Response:
        """Process request and collect metrics."""
        # Skip metrics collection for the /metrics endpoint itself
        if request.url.path == "/metrics":
            return cast(Response, await call_next(request))

        method = request.method
        path = request.url.path
        environment = os.getenv("ENVIRONMENT", "dev").lower()

        # Track in-flight requests
        http_requests_in_flight.labels(environment=environment).inc()

        start_time = time.time()

        try:
            # Process request
            response = await call_next(request)
            status = response.status_code

            # Record request metrics
            http_requests_total.labels(
                method=method,
                endpoint=path,
                status=str(status),
                environment=environment,
            ).inc()

            return cast(Response, response)

        except Exception as exc:
            # Track exceptions
            http_exceptions_total.labels(
                exception_type=type(exc).__name__,
                environment=environment,
            ).inc()
            http_requests_total.labels(
                method=method,
                endpoint=path,
                status="500",
                environment=environment,
            ).inc()
            raise

        finally:
            # Record duration
            duration = time.time() - start_time
            http_request_duration_seconds.labels(
                method=method,
                endpoint=path,
                environment=environment,
            ).observe(duration)

            # Decrement in-flight counter
            http_requests_in_flight.labels(environment=environment).dec()
