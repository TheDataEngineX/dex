"""ML router — ``/api/v1/ml``."""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request

from dataenginex.api.rbac import Role, require_role
from dataenginex.api.schemas import (
    ExperimentListResponse,
    FeatureGetResponse,
    FeatureSaveRequest,
    ModelListResponse,
    PredictionRequest,
    PredictionResponse,
    PromoteRequest,
)
from dataenginex.middleware.domain_metrics import ml_model_predictions_total
from dataenginex.ml.registry import ModelStage

_RequireEditor = Depends(require_role(Role.EDITOR))

logger = structlog.get_logger()

router = APIRouter(prefix="/ml", tags=["ml"])


# --- Experiments ---


@router.get("/experiments", response_model=ExperimentListResponse)
def list_experiments(request: Request) -> ExperimentListResponse:
    """List all ML tracking experiments."""
    tracker = request.app.state.tracker
    experiments = tracker.list_experiments()
    return ExperimentListResponse(experiments=experiments, count=len(experiments))


@router.post("/experiments/{name}")
def create_experiment(name: str, request: Request, _: Any = _RequireEditor) -> dict[str, Any]:
    """Create a new tracking experiment by name."""
    tracker = request.app.state.tracker
    exp_id = tracker.create_experiment(name)
    return {"id": exp_id, "name": name}


@router.get("/experiments/{name}/runs")
def list_runs(name: str, request: Request) -> dict[str, Any]:
    """List all runs for a named experiment."""
    tracker = request.app.state.tracker
    experiments = tracker.list_experiments()
    exp = next((e for e in experiments if e["name"] == name), None)
    if exp is None:
        raise HTTPException(status_code=404, detail=f"Experiment '{name}' not found")
    runs = tracker.list_runs(exp["id"])
    return {"experiment": name, "runs": runs, "count": len(runs)}


# --- Models ---


@router.get("/models", response_model=ModelListResponse)
def list_models(request: Request) -> ModelListResponse:
    """List all registered models with their available versions."""
    registry = request.app.state.model_registry
    names: list[str] = registry.list_models()
    models: list[dict[str, Any]] = [
        {"name": n, "versions": registry.list_versions(n)} for n in names
    ]
    return ModelListResponse(models=models, count=len(models))


@router.get("/models/{name}")
def get_model(name: str, request: Request) -> dict[str, Any]:
    """Get the latest version of a registered model."""
    registry = request.app.state.model_registry
    model = registry.get_latest(name)
    if model is None:
        raise HTTPException(status_code=404, detail=f"Model '{name}' not found")
    return {
        "name": model.name,
        "version": model.version,
        "stage": model.stage,
        "metrics": model.metrics,
        "created_at": model.created_at.isoformat() if model.created_at else None,
    }


@router.post("/models/{name}/promote")
def promote_model(
    name: str,
    body: PromoteRequest,
    request: Request,
    _: Any = _RequireEditor,
) -> dict[str, Any]:
    """Promote a model to a target stage (staging, production, archived)."""
    registry = request.app.state.model_registry
    model = registry.get_latest(name)
    if model is None:
        raise HTTPException(status_code=404, detail=f"Model '{name}' not found")
    try:
        target = ModelStage(body.stage)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid stage: {body.stage!r}") from exc
    registry.promote(name, model.version, target)
    return {"name": name, "version": model.version, "stage": body.stage, "promoted": True}


# --- Predictions ---


@router.post("/predictions", response_model=PredictionResponse)
def predict(body: PredictionRequest, request: Request) -> PredictionResponse:
    """Run inference on a deployed model."""
    engine = request.app.state.serving_engine
    registry = request.app.state.model_registry
    model = registry.get_latest(body.model_name)
    version = model.version if model else "unknown"
    try:
        result = engine.predict(body.model_name, body.features)
    except Exception as exc:
        ml_model_predictions_total.labels(
            model=body.model_name, version=version, status="error"
        ).inc()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    ml_model_predictions_total.labels(model=body.model_name, version=version, status="ok").inc()
    return PredictionResponse(model_name=body.model_name, prediction=result)


# --- Features ---


@router.get("/features")
def list_feature_groups(request: Request) -> dict[str, Any]:
    """List all registered feature groups."""
    fs = request.app.state.feature_store
    if fs is None:
        return {"groups": [], "count": 0}
    groups = fs.list_feature_groups()
    return {"groups": groups, "count": len(groups)}


@router.get("/features/{group}", response_model=FeatureGetResponse)
def get_features(group: str, request: Request, entity_ids: str = "") -> FeatureGetResponse:
    """Retrieve features for a group, optionally filtered by comma-separated entity IDs."""
    fs = request.app.state.feature_store
    ids = [eid.strip() for eid in entity_ids.split(",") if eid.strip()] if entity_ids else []
    features = fs.get_features(group, ids) if ids else []
    result: list[dict[str, Any]] = features if isinstance(features, list) else []
    return FeatureGetResponse(feature_group=group, features=result)


@router.post("/features/{group}")
def save_features(
    group: str,
    body: FeatureSaveRequest,
    request: Request,
    _: Any = _RequireEditor,
) -> dict[str, Any]:
    """Save a batch of feature rows to a feature group."""
    fs = request.app.state.feature_store
    fs.save_features(group, body.data, body.entity_key)
    return {"feature_group": group, "saved": len(body.data)}


# --- Drift ---


@router.get("/drift/{pipeline_name}")
def check_drift(pipeline_name: str, request: Request) -> dict[str, Any]:
    """Return drift detection status for a pipeline (requires at least one prior run)."""
    config = request.app.state.config
    if pipeline_name not in config.data.pipelines:
        raise HTTPException(status_code=404, detail=f"Pipeline '{pipeline_name}' not found")
    return {
        "pipeline": pipeline_name,
        "status": "no_baseline",
        "reports": [],
        "message": "Run pipeline at least once to establish baseline",
    }
