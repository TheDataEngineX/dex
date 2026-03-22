"""Pipelines router — ``/api/v1/pipelines``."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request

router = APIRouter(prefix="/pipelines", tags=["pipelines"])


@router.get("/")
def list_pipelines(request: Request) -> dict[str, Any]:
    """List all configured pipelines."""
    config = request.app.state.config
    pipelines = list(config.data.pipelines.keys())
    return {"pipelines": pipelines, "count": len(pipelines)}


@router.get("/{pipeline_name}")
def get_pipeline(pipeline_name: str, request: Request) -> dict[str, Any]:
    """Get pipeline configuration by name."""
    config = request.app.state.config
    if pipeline_name not in config.data.pipelines:
        raise HTTPException(status_code=404, detail=f"Pipeline '{pipeline_name}' not found")

    pipeline = config.data.pipelines[pipeline_name]
    return {
        "name": pipeline_name,
        "source": pipeline.source,
        "transforms": len(pipeline.transforms),
        "has_quality_gate": pipeline.quality is not None,
        "schedule": pipeline.schedule,
        "depends_on": pipeline.depends_on,
    }


@router.post("/{pipeline_name}/run")
def run_pipeline(pipeline_name: str, request: Request) -> dict[str, Any]:
    """Trigger a pipeline run."""
    config = request.app.state.config
    if pipeline_name not in config.data.pipelines:
        raise HTTPException(status_code=404, detail=f"Pipeline '{pipeline_name}' not found")

    return {
        "pipeline": pipeline_name,
        "status": "triggered",
        "message": f"Pipeline '{pipeline_name}' run triggered",
    }
