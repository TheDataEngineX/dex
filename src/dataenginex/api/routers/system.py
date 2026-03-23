"""System router — ``/api/v1/system``."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

from dataenginex.api.schemas import ComponentHealthResponse

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/components", response_model=ComponentHealthResponse)
def list_components(request: Request) -> ComponentHealthResponse:
    """Per-component health status."""
    state = request.app.state

    def _status(attr: str) -> str:
        return "healthy" if hasattr(state, attr) and getattr(state, attr) else "unavailable"

    components: list[dict[str, Any]] = [
        {"name": "tracker", "status": _status("tracker")},
        {"name": "feature_store", "status": _status("feature_store")},
        {"name": "serving_engine", "status": _status("serving_engine")},
        {"name": "llm", "status": _status("llm")},
        {"name": "pipeline_runner", "status": _status("pipeline_runner")},
    ]
    agent_count = len(state.agents) if hasattr(state, "agents") else 0
    components.append(
        {
            "name": "agents",
            "status": "healthy" if agent_count > 0 else "none_configured",
            "count": agent_count,
        }
    )
    return ComponentHealthResponse(components=components)


@router.get("/logs")
def get_logs(
    request: Request,
    level: str | None = None,
    limit: int = 100,
    component: str | None = None,
) -> dict[str, Any]:
    """Recent structured log entries. Placeholder until ring-buffer is wired."""
    return {"logs": [], "count": 0, "message": "Log buffer not yet configured"}
