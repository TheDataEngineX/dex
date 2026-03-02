"""Health check utilities for DEX."""

from __future__ import annotations

import asyncio
import os
import time
from dataclasses import dataclass
from enum import StrEnum

import httpx

__all__ = [
    "ComponentHealth",
    "HealthChecker",
    "HealthStatus",
]


class HealthStatus(StrEnum):
    """Supported health statuses."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class ComponentHealth:
    """Health status of a single dependency component.

    Attributes:
        name: Component identifier (e.g. ``"database"``, ``"cache"``).
        status: Current health status.
        message: Optional human-readable message.
        duration_ms: Time taken for the health check in milliseconds.
    """

    name: str
    status: HealthStatus
    message: str | None = None
    duration_ms: float | None = None

    def to_dict(self) -> dict[str, object | None]:
        """Serialize to a plain dictionary suitable for JSON responses."""
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "duration_ms": self.duration_ms,
        }


class HealthChecker:
    """Runs health checks for DEX dependencies."""

    def __init__(self, timeout_seconds: float = 1.0) -> None:
        self.timeout_seconds = timeout_seconds

    async def check_all(self) -> list[ComponentHealth]:
        """Run all dependency health checks concurrently."""
        return [
            await self.check_database(),
            await self.check_cache(),
            await self.check_external_api(),
        ]

    def overall_status(self, components: list[ComponentHealth]) -> HealthStatus:
        """Derive an aggregate status from individual component results."""
        if any(c.status == HealthStatus.UNHEALTHY for c in components):
            return HealthStatus.UNHEALTHY
        if any(c.status == HealthStatus.DEGRADED for c in components):
            return HealthStatus.DEGRADED
        return HealthStatus.HEALTHY

    async def check_database(self) -> ComponentHealth:
        """Check database connectivity via TCP probe."""
        host = os.getenv("DEX_DB_HOST")
        port = os.getenv("DEX_DB_PORT")
        if not host or not port:
            return ComponentHealth(
                name="database",
                status=HealthStatus.SKIPPED,
                message="database not configured",
            )

        start = time.perf_counter()
        ok, message = await self._tcp_check(host, int(port))
        duration_ms = (time.perf_counter() - start) * 1000
        return ComponentHealth(
            name="database",
            status=HealthStatus.HEALTHY if ok else HealthStatus.UNHEALTHY,
            message=message,
            duration_ms=round(duration_ms, 2),
        )

    async def check_cache(self) -> ComponentHealth:
        """Check cache connectivity via TCP probe."""
        host = os.getenv("DEX_CACHE_HOST")
        port = os.getenv("DEX_CACHE_PORT")
        if not host or not port:
            return ComponentHealth(
                name="cache",
                status=HealthStatus.SKIPPED,
                message="cache not configured",
            )

        start = time.perf_counter()
        ok, message = await self._tcp_check(host, int(port))
        duration_ms = (time.perf_counter() - start) * 1000
        return ComponentHealth(
            name="cache",
            status=HealthStatus.HEALTHY if ok else HealthStatus.UNHEALTHY,
            message=message,
            duration_ms=round(duration_ms, 2),
        )

    async def check_external_api(self) -> ComponentHealth:
        """Check external API reachability via HTTP GET."""
        url = os.getenv("DEX_EXTERNAL_API_URL")
        if not url:
            return ComponentHealth(
                name="external_api",
                status=HealthStatus.SKIPPED,
                message="external API not configured",
            )

        start = time.perf_counter()
        timeout = httpx.Timeout(self.timeout_seconds)
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(url)
            ok = response.status_code < 500
            message = f"status_code={response.status_code}"
        except httpx.HTTPError as exc:
            ok = False
            message = f"error={exc.__class__.__name__}"
        duration_ms = (time.perf_counter() - start) * 1000
        return ComponentHealth(
            name="external_api",
            status=HealthStatus.HEALTHY if ok else HealthStatus.UNHEALTHY,
            message=message,
            duration_ms=round(duration_ms, 2),
        )

    async def _tcp_check(self, host: str, port: int) -> tuple[bool, str]:
        try:
            await asyncio.wait_for(
                asyncio.open_connection(host, port), timeout=self.timeout_seconds
            )
            return True, "reachable"
        except (TimeoutError, ConnectionRefusedError, OSError) as exc:
            return False, f"error={exc.__class__.__name__}"
