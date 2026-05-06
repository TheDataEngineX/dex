"""Data router — ``/api/v1/data``."""

from __future__ import annotations

from typing import Any

import duckdb
import structlog
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

logger = structlog.get_logger()

router = APIRouter(prefix="/data", tags=["data"])


class SQLQueryRequest(BaseModel):
    sql: str
    limit: int = 1000


# --- SQL Console ---


@router.post("/query")
def execute_query(body: SQLQueryRequest, request: Request) -> dict[str, Any]:
    """Execute a DuckDB SQL query and return results."""
    try:
        conn = duckdb.connect(":memory:")
        rel = conn.execute(body.sql)
        columns = [desc[0] for desc in (rel.description or [])]
        rows = [dict(zip(columns, row, strict=True)) for row in rel.fetchmany(body.limit)]
        conn.close()
        return {"columns": columns, "rows": rows, "count": len(rows)}
    except duckdb.Error as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# --- Sources ---


@router.get("/sources")
def list_sources(request: Request) -> dict[str, Any]:
    """List all configured data sources."""
    config = request.app.state.config
    sources = [
        {"name": name, "type": src.type, "path": src.path}
        for name, src in config.data.sources.items()
    ]
    return {"sources": sources, "count": len(sources)}


@router.get("/sources/{source_name}")
def get_source(source_name: str, request: Request) -> dict[str, Any]:
    """Get source details."""
    config = request.app.state.config
    if source_name not in config.data.sources:
        raise HTTPException(status_code=404, detail=f"Source '{source_name}' not found")
    src = config.data.sources[source_name]
    return {
        "name": source_name,
        "type": src.type,
        "path": src.path,
        "query": src.query,
        "options": src.options,
    }


# --- Warehouse ---


@router.get("/warehouse/layers")
def list_warehouse_layers(request: Request) -> dict[str, Any]:
    """List medallion layers with table counts."""
    from pathlib import Path

    layers = []
    for layer_name in ("bronze", "silver", "gold"):
        layer_path = Path(".dex/lakehouse") / layer_name
        table_count = len(list(layer_path.glob("*.parquet"))) if layer_path.exists() else 0
        layers.append({"name": layer_name, "table_count": table_count})
    return {"layers": layers}


@router.get("/warehouse/layers/{layer}/tables")
def list_warehouse_tables(layer: str, request: Request) -> dict[str, Any]:
    """List tables in a medallion layer."""
    from pathlib import Path

    valid_layers = ("bronze", "silver", "gold")
    if layer not in valid_layers:
        raise HTTPException(
            status_code=404,
            detail=f"Layer '{layer}' not found. Valid: {valid_layers}",
        )
    layer_path = Path(".dex/lakehouse") / layer
    tables = []
    if layer_path.exists():
        for f in layer_path.glob("*.parquet"):
            tables.append({"name": f.stem, "path": str(f), "size_bytes": f.stat().st_size})
    return {"layer": layer, "tables": tables, "count": len(tables)}


# --- Lineage ---


@router.get("/lineage")
def list_lineage(request: Request) -> dict[str, Any]:
    """List lineage events."""
    lineage = request.app.state.lineage
    events = [ev.to_dict() for ev in lineage.all_events]
    return {"events": events, "count": len(events)}


@router.get("/lineage/{event_id}")
def get_lineage_event(event_id: str, request: Request) -> dict[str, Any]:
    """Get a specific lineage event."""
    lineage = request.app.state.lineage
    event = lineage.get_event(event_id)
    if event is None:
        raise HTTPException(status_code=404, detail=f"Lineage event '{event_id}' not found")
    return event.to_dict()  # type: ignore[no-any-return]


# --- Quality ---


@router.get("/quality/summary")
def quality_summary(request: Request) -> dict[str, Any]:
    """Aggregate quality metrics across pipelines."""
    config = request.app.state.config
    pipelines_quality: list[dict[str, Any]] = []
    for name, pipe_cfg in config.data.pipelines.items():
        pipelines_quality.append(
            {
                "pipeline": name,
                "has_quality_gate": pipe_cfg.quality is not None,
            }
        )
    return {"pipelines": pipelines_quality}


@router.get("/quality/{pipeline_name}")
def quality_pipeline(pipeline_name: str, request: Request) -> dict[str, Any]:
    """Quality results for a specific pipeline."""
    config = request.app.state.config
    if pipeline_name not in config.data.pipelines:
        raise HTTPException(status_code=404, detail=f"Pipeline '{pipeline_name}' not found")
    pipe_cfg = config.data.pipelines[pipeline_name]
    return {
        "pipeline": pipeline_name,
        "has_quality_gate": pipe_cfg.quality is not None,
        "quality_config": pipe_cfg.quality.model_dump() if pipe_cfg.quality else None,
    }
