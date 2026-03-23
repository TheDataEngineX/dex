"""Pipelines router — ``/api/v1/pipelines``."""

from __future__ import annotations

import time
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException, Request

from dataenginex.api.schemas import PipelineResultResponse

logger = structlog.get_logger()

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


@router.post("/{pipeline_name}/run", response_model=PipelineResultResponse)
def run_pipeline(pipeline_name: str, request: Request) -> PipelineResultResponse:
    """Execute a pipeline run."""
    config = request.app.state.config
    if pipeline_name not in config.data.pipelines:
        raise HTTPException(status_code=404, detail=f"Pipeline '{pipeline_name}' not found")

    runner = request.app.state.pipeline_runner
    start = time.monotonic()
    result = runner.run(pipeline_name)
    duration_ms = (time.monotonic() - start) * 1000

    return PipelineResultResponse(
        pipeline=pipeline_name,
        success=result.success,
        rows_input=result.rows_input,
        rows_output=result.rows_output,
        steps_completed=result.steps_completed,
        duration_ms=round(duration_ms, 2),
        error=result.error,
    )
