"""ML training, model registry, drift detection, serving, scheduling, metrics, vectorstore & LLM.

Public API::

    from dataenginex.ml import (
        BaseTrainer, SklearnTrainer, TrainingResult,
        ModelRegistry, ModelArtifact, ModelStage,
        MLflowModelRegistry, MLflowRegistryError,
        DriftDetector, DriftReport,
        DriftScheduler, DriftMonitorConfig, DriftCheckResult,
        ModelServer, PredictionRequest, PredictionResponse,
        model_prediction_total, model_prediction_latency_seconds,
        model_drift_psi, model_drift_alerts_total,
        # Vector store (Issue #94)
        VectorStoreBackend, InMemoryBackend, QdrantBackend,
        Document, SearchResult, RAGPipeline,
        # LLM (Issue #95)
        LLMProvider, OllamaProvider, OpenAICompatibleProvider, MockProvider,
        LLMConfig, LLMResponse, ChatMessage,
        get_llm_provider,
        llm_request_latency_seconds, llm_tokens_total,
    )
"""

from __future__ import annotations

from .drift import DriftDetector, DriftReport
from .llm import (
    ChatMessage,
    LLMConfig,
    LLMProvider,
    LLMResponse,
    MockProvider,
    OllamaProvider,
    OpenAICompatibleProvider,
    get_llm_provider,
    llm_request_latency_seconds,
    llm_tokens_total,
)
from .metrics import (
    model_drift_alerts_total,
    model_drift_psi,
    model_prediction_latency_seconds,
    model_prediction_total,
)
from .mlflow_registry import MLflowModelRegistry, MLflowRegistryError
from .registry import ModelArtifact, ModelRegistry, ModelStage
from .scheduler import DriftCheckResult, DriftMonitorConfig, DriftScheduler
from .serving import ModelServer, PredictionRequest, PredictionResponse
from .training import BaseTrainer, SklearnTrainer, TrainingResult
from .vectorstore import (
    Document,
    InMemoryBackend,
    QdrantBackend,
    RAGPipeline,
    SearchResult,
    VectorStoreBackend,
)

__all__ = [
    # Training
    "BaseTrainer",
    "SklearnTrainer",
    "TrainingResult",
    # Registry
    "ModelArtifact",
    "ModelRegistry",
    "ModelStage",
    "MLflowModelRegistry",
    "MLflowRegistryError",
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
    # Vector store (Issue #94)
    "QdrantBackend",
    "Document",
    "InMemoryBackend",
    "RAGPipeline",
    "SearchResult",
    "VectorStoreBackend",
    # LLM (Issue #95)
    "ChatMessage",
    "LLMConfig",
    "LLMProvider",
    "LLMResponse",
    "MockProvider",
    "OllamaProvider",
    "OpenAICompatibleProvider",
    "get_llm_provider",
    "llm_request_latency_seconds",
    "llm_tokens_total",
]
