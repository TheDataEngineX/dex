"""ML model serving router — ``/api/v1/`` prediction and model endpoints.

Provides REST endpoints for model inference and model registry queries.
All endpoints emit Prometheus metrics for latency and throughput monitoring.

Endpoints:
    POST /api/v1/predict            — Run prediction against a registered model
    GET  /api/v1/models             — List all registered models
    GET  /api/v1/models/{name}      — Get metadata for a specific model
"""

from __future__ import annotations

from typing import Any

import structlog
from dataenginex.ml.metrics import (
    model_prediction_latency_seconds,
    model_prediction_total,
)
from dataenginex.ml.registry import ModelRegistry
from dataenginex.ml.serving import ModelServer, PredictionRequest, PredictionResponse
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

__all__ = [
    "get_model_server",
    "ml_router",
    "set_model_server",
]

logger = structlog.get_logger(__name__)

ml_router = APIRouter(prefix="/api/v1", tags=["ml"])

# ---------------------------------------------------------------------------
# Module-level model server — shared across requests.
# Populate via ``set_model_server()`` from application startup.
# ---------------------------------------------------------------------------

_model_server: ModelServer | None = None
_model_registry: ModelRegistry | None = None


def set_model_server(
    server: ModelServer,
    registry: ModelRegistry | None = None,
) -> None:
    """Configure the module-level model server and optional registry.

    Call this at application startup to enable the ML endpoints.
    """
    global _model_server, _model_registry  # noqa: PLW0603
    _model_server = server
    _model_registry = registry or server._registry


def get_model_server() -> ModelServer | None:
    """Return the active model server, or ``None`` if not configured."""
    return _model_server


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class PredictRequestBody(BaseModel):
    """HTTP request body for the ``/predict`` endpoint."""

    model_name: str = Field(..., description="Name of the model to use")
    version: str | None = Field(None, description="Model version (latest if omitted)")
    features: list[dict[str, Any]] = Field(..., description="List of feature dicts for prediction")
    request_id: str | None = Field(None, description="Optional client request ID")


class PredictResponseBody(BaseModel):
    """HTTP response body from the ``/predict`` endpoint."""

    model_name: str
    version: str
    predictions: list[Any]
    latency_ms: float
    request_id: str
    served_at: str


class ModelMetadataResponse(BaseModel):
    """HTTP response body for model metadata."""

    name: str
    version: str
    stage: str
    metrics: dict[str, Any]
    parameters: dict[str, Any]
    created_at: str
    description: str = ""


class ModelListResponse(BaseModel):
    """HTTP response body for model listing."""

    models: list[ModelMetadataResponse]
    total: int


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@ml_router.post("/predict", response_model=PredictResponseBody)
async def predict(body: PredictRequestBody) -> PredictResponseBody:
    """Run a prediction against a registered model.

    Emits ``model_prediction_total`` and ``model_prediction_latency_seconds``
    Prometheus metrics.
    """
    if _model_server is None:
        raise HTTPException(status_code=503, detail="Model server not configured")

    request = PredictionRequest(
        model_name=body.model_name,
        version=body.version,
        features=body.features,
        request_id=body.request_id or "",
    )

    try:
        result: PredictionResponse = _model_server.predict(request)
    except KeyError as exc:
        model_prediction_total.labels(
            model=body.model_name,
            version=body.version or "latest",
            status="not_found",
        ).inc()
        logger.warning("model_not_found", model=body.model_name, error=str(exc))
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        model_prediction_total.labels(
            model=body.model_name,
            version=body.version or "latest",
            status="error",
        ).inc()
        logger.error("prediction_failed", model=body.model_name, error=str(exc))
        raise HTTPException(status_code=500, detail="Prediction failed") from exc

    # Record success metrics
    version = result.version
    model_prediction_total.labels(model=result.model_name, version=version, status="success").inc()
    model_prediction_latency_seconds.labels(model=result.model_name, version=version).observe(
        result.latency_ms / 1000.0
    )

    logger.info(
        "prediction_served",
        model=result.model_name,
        version=version,
        latency_ms=result.latency_ms,
    )

    return PredictResponseBody(
        model_name=result.model_name,
        version=result.version,
        predictions=result.predictions,
        latency_ms=result.latency_ms,
        request_id=result.request_id,
        served_at=result.served_at.isoformat(),
    )


@ml_router.get("/models", response_model=ModelListResponse)
async def list_models() -> ModelListResponse:
    """List all registered models and their metadata."""
    if _model_registry is None:
        raise HTTPException(status_code=503, detail="Model registry not configured")

    model_names: list[str] = _model_registry.list_models()
    models: list[ModelMetadataResponse] = []
    for name in model_names:
        artifact = _model_registry.get_latest(name)
        if artifact is not None:
            models.append(
                ModelMetadataResponse(
                    name=artifact.name,
                    version=artifact.version,
                    stage=artifact.stage.value,
                    metrics=artifact.metrics,
                    parameters=artifact.parameters,
                    created_at=artifact.created_at.isoformat(),
                    description=artifact.description,
                )
            )
    return ModelListResponse(models=models, total=len(models))


@ml_router.get("/models/{name}", response_model=ModelMetadataResponse)
async def get_model_metadata(
    name: str,
    version: str | None = None,
) -> ModelMetadataResponse:
    """Get metadata for a specific model.

    If *version* is omitted, returns the latest registered version.
    """
    if _model_registry is None:
        raise HTTPException(status_code=503, detail="Model registry not configured")

    if version is not None:
        artifact = _model_registry.get(name, version)
    else:
        artifact = _model_registry.get_latest(name)

    if artifact is None:
        raise HTTPException(
            status_code=404,
            detail=f"Model '{name}' version '{version or 'latest'}' not found",
        )

    return ModelMetadataResponse(
        name=artifact.name,
        version=artifact.version,
        stage=artifact.stage.value,
        metrics=artifact.metrics,
        parameters=artifact.parameters,
        created_at=artifact.created_at.isoformat(),
        description=artifact.description,
    )
