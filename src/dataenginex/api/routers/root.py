"""Root router — ``/`` and ``/metrics``."""

from __future__ import annotations

from fastapi import APIRouter, Response

router = APIRouter(tags=["root"])


@router.get("/")
def root() -> dict[str, str]:
    """Root endpoint."""
    return {"service": "dataenginex", "status": "running"}


@router.get("/metrics")
def metrics() -> Response:
    """Prometheus metrics endpoint."""
    try:
        from dataenginex.middleware.metrics import get_metrics

        data, content_type = get_metrics()
        return Response(content=data, media_type=content_type)
    except ImportError:
        return Response(content="# metrics not available\n", media_type="text/plain")
