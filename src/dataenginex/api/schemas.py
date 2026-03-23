"""Pydantic request/response models for all API routers."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

# --- Shared ---


class ServiceUnavailableResponse(BaseModel):
    error: str = "service_unavailable"
    component: str
    message: str


# --- Pipelines ---


class PipelineResultResponse(BaseModel):
    pipeline: str
    success: bool
    rows_input: int = 0
    rows_output: int = 0
    steps_completed: int = 0
    duration_ms: float = 0.0
    error: str | None = None


# --- Data ---


class SourceListResponse(BaseModel):
    sources: list[dict[str, Any]]
    count: int


class WarehouseLayerResponse(BaseModel):
    layers: list[dict[str, Any]]


class QualitySummaryResponse(BaseModel):
    pipelines: list[dict[str, Any]]
    overall_pass_rate: float = 0.0


# --- ML ---


class ExperimentListResponse(BaseModel):
    experiments: list[dict[str, Any]]
    count: int


class ModelListResponse(BaseModel):
    models: list[dict[str, Any]]
    count: int


class ModelDetailResponse(BaseModel):
    name: str
    versions: list[dict[str, Any]]
    current_stage: str | None = None


class PromoteRequest(BaseModel):
    stage: str


class PredictionRequest(BaseModel):
    model_name: str
    features: dict[str, Any]


class PredictionResponse(BaseModel):
    model_name: str
    prediction: Any
    model_version: str | None = None


class FeatureGetResponse(BaseModel):
    feature_group: str
    features: list[dict[str, Any]]


class FeatureSaveRequest(BaseModel):
    entity_key: str
    data: list[dict[str, Any]]


class DriftReportResponse(BaseModel):
    pipeline: str
    status: str
    reports: list[dict[str, Any]] = []
    message: str | None = None


# --- AI ---


class AgentListResponse(BaseModel):
    agents: list[dict[str, Any]]
    count: int


class AgentDetailResponse(BaseModel):
    name: str
    runtime: str
    model: str | None = None
    tools: list[str]
    max_iterations: int


class AgentChatRequest(BaseModel):
    message: str


class AgentChatResponse(BaseModel):
    agent: str
    response: str
    iterations: int
    tool_calls: int


class ToolListResponse(BaseModel):
    tools: list[dict[str, Any]]
    count: int


class ToolDetailResponse(BaseModel):
    name: str
    description: str
    parameters: dict[str, Any] = {}


# --- System ---


class ComponentHealthResponse(BaseModel):
    components: list[dict[str, Any]]
