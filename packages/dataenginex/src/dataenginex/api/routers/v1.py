"""
Versioned API router — ``/api/v1/`` endpoints for DEX.

Groups data-pipeline, warehouse, and system endpoints under a versioned
prefix so that breaking changes can be introduced via ``/api/v2/`` later.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from dataenginex.api.pagination import PaginatedResponse, paginate
from dataenginex.core.quality import QualityStore

__all__ = [
    "get_quality_store",
    "router",
    "set_quality_store",
]

router = APIRouter(prefix="/api/v1", tags=["v1"])

# Module-level quality store — shared across requests.
# Populate via ``set_quality_store()`` from application startup.
_quality_store: QualityStore = QualityStore()


def set_quality_store(store: QualityStore) -> None:
    """Replace the module-level quality store (call at app startup)."""
    global _quality_store  # noqa: PLW0603
    _quality_store = store


def get_quality_store() -> QualityStore:
    """Return the active quality store."""
    return _quality_store


# ---------------------------------------------------------------------------
# Data pipeline endpoints
# ---------------------------------------------------------------------------


@router.get("/data/sources", response_model=PaginatedResponse)
def list_data_sources(cursor: str | None = None, limit: int = 20) -> PaginatedResponse:
    """List registered data sources (derived from pipeline config)."""
    from dataenginex.core.pipeline_config import PipelineConfig

    sources: list[dict[str, Any]] = [
        {"name": name, "type": cfg.get("type", "unknown"), "status": "active"}
        for name, cfg in PipelineConfig.CAREERDEX_JOB_SOURCES.items()
    ]
    return paginate(sources, cursor=cursor, limit=limit)


@router.get("/data/quality")
def data_quality_summary() -> dict[str, Any]:
    """Return a summary of data quality metrics from the quality store.

    Returns live metrics when a ``QualityStore`` has been populated via
    ``QualityGate.evaluate()``.  Falls back to zeros when no evaluations
    have been recorded yet.
    """
    return _quality_store.summary()


@router.get("/data/quality/{layer}")
def data_quality_layer(layer: str, limit: int = 10) -> dict[str, Any]:
    """Return quality history for a specific medallion layer.

    Args:
        layer: One of ``bronze``, ``silver``, ``gold``.
        limit: Maximum number of history entries to return.
    """
    latest = _quality_store.latest(layer)
    return {
        "layer": layer,
        "latest": latest.to_dict() if latest else None,
        "history": _quality_store.history(layer, limit=limit),
    }


# ---------------------------------------------------------------------------
# Warehouse endpoints
# ---------------------------------------------------------------------------


@router.get("/warehouse/layers")
def list_warehouse_layers() -> dict[str, Any]:
    """Return medallion layer configuration."""
    from dataenginex.core.medallion_architecture import MedallionArchitecture

    layers = MedallionArchitecture.get_all_layers()
    return {
        "layers": [
            {
                "name": lc.layer_name,
                "description": lc.description,
                "purpose": lc.purpose,
                "format": lc.storage_format.value,
                "quality_threshold": lc.quality_threshold,
                "retention_days": lc.retention_days,
            }
            for lc in layers
        ]
    }


@router.get("/warehouse/lineage/{event_id}")
def get_lineage(event_id: str) -> dict[str, Any]:
    """Look up a lineage event by ID (placeholder)."""
    return {
        "event_id": event_id,
        "message": "Lineage tracking available — connect PersistentLineage for live data",
    }


# ---------------------------------------------------------------------------
# System endpoints
# ---------------------------------------------------------------------------


@router.get("/system/config")
def system_config() -> dict[str, Any]:
    """Return non-sensitive system configuration."""
    from dataenginex.core.pipeline_config import PipelineConfig

    return {
        "schedule": PipelineConfig.EXECUTION_SCHEDULE,
        "expected_jobs_per_cycle": PipelineConfig.EXPECTED_JOBS_PER_CYCLE,
        "timeout_minutes": PipelineConfig.TIMEOUT_MINUTES,
        "sources": list(PipelineConfig.CAREERDEX_JOB_SOURCES.keys()),
    }
