"""Pipelines router — ``/api/v1/pipelines``."""

from __future__ import annotations

import os
import time
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from dataenginex.api.rbac import Role, require_role
from dataenginex.api.schemas import PipelineResultResponse
from dataenginex.middleware.domain_metrics import (
    pipeline_run_duration_seconds,
    pipeline_runs_total,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/pipelines", tags=["pipelines"])

_RequireEditor = Depends(require_role(Role.EDITOR))

_REDIS_URL = os.getenv("DEX_REDIS_URL", "redis://localhost:6379")


def _arq_available() -> bool:
    try:
        import arq  # noqa: F401

        return True
    except ImportError:
        return False


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
async def run_pipeline(
    pipeline_name: str,
    request: Request,
    _: Any = _RequireEditor,
) -> dict[str, Any]:
    """Enqueue a pipeline run and return a job_id for polling.

    When ARQ/Redis is available the run is async — poll ``GET /jobs/{job_id}``
    for status.  When Redis is unavailable the run executes synchronously for
    backwards compatibility (dev environments without Redis).
    """
    config = request.app.state.config
    if pipeline_name not in config.data.pipelines:
        raise HTTPException(status_code=404, detail=f"Pipeline '{pipeline_name}' not found")

    if _arq_available():
        try:
            from arq.connections import RedisSettings, create_pool

            pool = await create_pool(RedisSettings.from_dsn(_REDIS_URL))
            job = await pool.enqueue_job("run_pipeline", pipeline_name)
            await pool.aclose()
            if job is None:
                raise RuntimeError("ARQ returned no job handle")
            logger.info("pipeline.enqueued", pipeline=pipeline_name, job_id=job.job_id)
            return {"pipeline": pipeline_name, "job_id": job.job_id, "status": "queued"}
        except Exception as exc:
            logger.warning("arq.enqueue.failed", error=str(exc), fallback="sync")

    # Synchronous fallback (dev / no Redis)
    runner = request.app.state.pipeline_runner
    start = time.monotonic()
    result = runner.run(pipeline_name)
    duration_seconds = time.monotonic() - start
    status_str = "success" if result.success else "failure"

    pipeline_runs_total.labels(pipeline=pipeline_name, status=status_str).inc()
    pipeline_run_duration_seconds.labels(pipeline=pipeline_name).observe(duration_seconds)

    return {
        "pipeline": pipeline_name,
        "job_id": None,
        "status": status_str,
        "result": PipelineResultResponse(
            pipeline=pipeline_name,
            success=result.success,
            rows_input=result.rows_input,
            rows_output=result.rows_output,
            steps_completed=result.steps_completed,
            duration_ms=round(duration_seconds * 1000, 2),
            error=result.error,
        ).model_dump(),
    }


@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str, _: Any = _RequireEditor) -> dict[str, Any]:
    """Poll async job status by job_id returned from ``/run``."""
    if not _arq_available():
        raise HTTPException(
            status_code=503, detail="Async job queue not available (Redis required)"
        )

    try:
        from arq.connections import RedisSettings, create_pool
        from arq.jobs import Job, JobStatus

        pool = await create_pool(RedisSettings.from_dsn(_REDIS_URL))
        job = Job(job_id, pool)
        status = await job.status()
        await pool.aclose()

        if status == JobStatus.complete:
            result = await job.result()
            status_str = "success" if result.get("success") else "failure"
            return {"job_id": job_id, "status": status_str, "result": result}
        if status == JobStatus.not_found:
            raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
        return {"job_id": job_id, "status": status.value, "result": None}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/{pipeline_name}/runs/{run_id}/logs/stream")
async def stream_pipeline_logs(
    pipeline_name: str,
    run_id: str,
    _: Any = _RequireEditor,
) -> StreamingResponse:
    """Stream pipeline run logs as Server-Sent Events.

    Clients connect with ``EventSource`` and receive log lines as they arrive.
    Uses Redis pub/sub channel ``pipeline:{pipeline_name}:{run_id}:logs``.
    """
    if not _arq_available():
        raise HTTPException(status_code=503, detail="Log streaming requires Redis")

    channel = f"pipeline:{pipeline_name}:{run_id}:logs"

    def _decode_message(data: Any) -> str:
        return data.decode() if isinstance(data, bytes) else str(data)

    async def _sse_generator() -> Any:
        try:
            import redis.asyncio as aioredis

            r = aioredis.from_url(_REDIS_URL)  # type: ignore[no-untyped-call]
            pubsub = r.pubsub()
            await pubsub.subscribe(channel)
            yield f'data: {{"channel": "{channel}", "status": "connected"}}\n\n'
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                data = _decode_message(message["data"])
                if data == "__done__":
                    yield 'data: {"status": "done"}\n\n'
                    break
                yield f"data: {data}\n\n"
            await pubsub.unsubscribe(channel)
            await r.aclose()
        except Exception as exc:
            yield f'data: {{"error": "{exc}"}}\n\n'

    return StreamingResponse(
        _sse_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
