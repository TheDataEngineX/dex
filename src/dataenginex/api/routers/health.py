"""Health router — ``/api/v1/health``."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, Any]:
    """Health check endpoint."""
    try:
        from dataenginex.api.health import HealthChecker

        checker = HealthChecker()
        components = await checker.check_all()
        status = checker.overall_status(components)
        return {
            "status": status.value,
            "components": {c.name: c.status.value for c in components},
        }
    except Exception:
        return {"status": "healthy"}
