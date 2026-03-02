"""ML training, model registry, drift detection, serving, scheduling, and metrics.

Public API::

    from dataenginex.ml import (
        BaseTrainer, SklearnTrainer, TrainingResult,
        ModelRegistry, ModelArtifact, ModelStage,
        DriftDetector, DriftReport,
        DriftScheduler, DriftMonitorConfig, DriftCheckResult,
        ModelServer, PredictionRequest, PredictionResponse,
        model_prediction_total, model_prediction_latency_seconds,
        model_drift_psi, model_drift_alerts_total,
    )
"""

from __future__ import annotations

from .drift import DriftDetector, DriftReport
from .metrics import (
    model_drift_alerts_total,
    model_drift_psi,
    model_prediction_latency_seconds,
    model_prediction_total,
)
from .registry import ModelArtifact, ModelRegistry, ModelStage
from .scheduler import DriftCheckResult, DriftMonitorConfig, DriftScheduler
from .serving import ModelServer, PredictionRequest, PredictionResponse
from .training import BaseTrainer, SklearnTrainer, TrainingResult

__all__ = [
    # Training
    "BaseTrainer",
    "SklearnTrainer",
    "TrainingResult",
    # Registry
    "ModelArtifact",
    "ModelRegistry",
    "ModelStage",
    # Drift
    "DriftDetector",
    "DriftReport",
    # Scheduler
    "DriftCheckResult",
    "DriftMonitorConfig",
    "DriftScheduler",
    # Serving
    "ModelServer",
    "PredictionRequest",
    "PredictionResponse",
    # Metrics
    "model_drift_alerts_total",
    "model_drift_psi",
    "model_prediction_latency_seconds",
    "model_prediction_total",
]
