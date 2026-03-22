"""
Rate-limiting middleware for DEX API.

Implements a token-bucket algorithm per client IP.  Configuration:

    DEX_RATE_LIMIT_ENABLED   — "true" to enable (default "false")
    DEX_RATE_LIMIT_RPM       — Requests per minute per IP (default 60)
    DEX_RATE_LIMIT_BURST     — Maximum burst size (default 10)
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any

import structlog
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

logger = structlog.get_logger()
__all__ = [
    "RateLimiter",
    "RateLimitMiddleware",
]


@dataclass
class _Bucket:
    """Token bucket for a single client."""

    tokens: float
    last_refill: float
    capacity: float
    refill_rate: float  # tokens per second

    def consume(self) -> bool:
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now
        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True
        return False


class RateLimiter:
    """In-memory token-bucket rate limiter.

    Parameters
    ----------
    requests_per_minute:
        Sustained request rate per client.
    burst:
        Maximum instantaneous burst size.
    """

    def __init__(self, requests_per_minute: int = 60, burst: int = 10) -> None:
        self.rpm = requests_per_minute
        self.burst = burst
        self._buckets: dict[str, _Bucket] = {}

    def allow(self, client_id: str) -> bool:
        """Return ``True`` if *client_id* has remaining tokens; consume one token."""
        bucket = self._buckets.get(client_id)
        if bucket is None:
            bucket = _Bucket(
                tokens=float(self.burst),
                last_refill=time.monotonic(),
                capacity=float(self.burst),
                refill_rate=self.rpm / 60.0,
            )
            self._buckets[client_id] = bucket
        return bucket.consume()

    def get_stats(self) -> dict[str, Any]:
        """Return current rate-limiter configuration and client count."""
        return {
            "rpm": self.rpm,
            "burst": self.burst,
            "active_clients": len(self._buckets),
        }

    def cleanup(self, max_age_seconds: float = 300.0) -> int:
        """Evict buckets idle for more than *max_age_seconds*."""
        now = time.monotonic()
        stale = [k for k, b in self._buckets.items() if now - b.last_refill > max_age_seconds]
        for k in stale:
            del self._buckets[k]
        return len(stale)


# Paths exempt from rate limiting
_EXEMPT_PATHS: set[str] = {"/health", "/ready", "/startup", "/metrics"}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Starlette middleware applying per-IP rate limiting."""

    def __init__(self, app: Any) -> None:  # noqa: ANN401
        super().__init__(app)
        rpm = int(os.getenv("DEX_RATE_LIMIT_RPM", "60"))
        burst = int(os.getenv("DEX_RATE_LIMIT_BURST", "10"))
        self._limiter = RateLimiter(requests_per_minute=rpm, burst=burst)
        self._enabled = os.getenv("DEX_RATE_LIMIT_ENABLED", "false").lower() == "true"

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Enforce per-IP rate limits; return 429 when tokens are exhausted."""
        if not self._enabled:
            return await call_next(request)

        if request.url.path in _EXEMPT_PATHS:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        if not self._limiter.allow(client_ip):
            logger.warning("rate limit exceeded", client_ip=client_ip)
            return JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limit_exceeded",
                    "message": "Too many requests — please slow down",
                },
                headers={"Retry-After": "60"},
            )

        return await call_next(request)
