# Phase 6A: DEX Engine Integration — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire all DEX engine components (ML, AI, Data, System) end-to-end through FastAPI lifespan, middleware, and routers so every subsystem is accessible via API.

**Architecture:** Add an async lifespan context manager to `create_app()` that initializes all backends from `DexConfig`. Wire 4 middleware layers. Create 4 new router modules (data, ml, ai, system). Update pipeline run from stub to real execution. Extend config validation with registry checks.

**Tech Stack:** Python 3.13 · FastAPI · DuckDB · Pydantic · structlog · pytest · mypy --strict

**Spec:** `docs/superpowers/specs/2026-03-22-phase-6-integration-design.md` (Part 1)

---

## File Structure

| Action | File | Responsibility |
|--------|------|---------------|
| Modify | `src/dataenginex/core/interfaces.py` | Add `list_experiments()` to `BaseTracker` |
| Modify | `src/dataenginex/ml/tracking/builtin.py` | Implement `list_experiments()` |
| Modify | `src/dataenginex/ai/agents/builtin.py` | Change `run()` return type: `str` → `dict` |
| Modify | `src/dataenginex/api/factory.py` | Lifespan context manager + middleware stack + new routers |
| Modify | `src/dataenginex/api/routers/pipelines.py` | Real pipeline execution via `PipelineRunner` |
| Modify | `src/dataenginex/config/loader.py` | Registry-aware validation warnings |
| Create | `src/dataenginex/api/routers/data.py` | Data endpoints (sources, warehouse, lineage, quality) |
| Create | `src/dataenginex/api/routers/ml.py` | ML endpoints (experiments, models, predictions, features, drift) |
| Create | `src/dataenginex/api/routers/ai.py` | AI endpoints (agents, chat, tools, collections, retrieval) |
| Create | `src/dataenginex/api/routers/system.py` | System endpoints (components, logs) |
| Create | `src/dataenginex/api/schemas.py` | Pydantic response/request models for all routers |
| Modify | `tests/unit/test_api_factory.py` | Lifespan + middleware tests |
| Create | `tests/unit/test_data_router.py` | Data router tests |
| Create | `tests/unit/test_ml_router.py` | ML router tests |
| Create | `tests/unit/test_ai_router.py` | AI router tests |
| Create | `tests/unit/test_system_router.py` | System router tests |
| Modify | `tests/unit/test_config_loader.py` | Enhanced validation tests |

---

## Task 1: Interface Changes — BaseTracker.list_experiments()

**Files:**
- Modify: `src/dataenginex/core/interfaces.py:75-106`
- Modify: `src/dataenginex/ml/tracking/builtin.py`
- Test: `tests/unit/test_builtin_tracker.py`

- [ ] **Step 1: Write failing test for list_experiments**

```python
# tests/unit/test_builtin_tracker.py — add to existing test class

def test_list_experiments(tmp_path: Path) -> None:
    tracker = BuiltinTracker(storage_dir=str(tmp_path / "tracking"))
    # Empty initially
    assert tracker.list_experiments() == []
    # Create experiments
    tracker.create_experiment("exp-1")
    tracker.create_experiment("exp-2")
    result = tracker.list_experiments()
    assert len(result) == 2
    names = [e["name"] for e in result]
    assert "exp-1" in names
    assert "exp-2" in names
    # Each entry has id and name
    for exp in result:
        assert "id" in exp
        assert "name" in exp
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_builtin_tracker.py::test_list_experiments -v`
Expected: FAIL — `AttributeError: 'BuiltinTracker' has no attribute 'list_experiments'`

- [ ] **Step 3: Add abstract method to BaseTracker**

In `src/dataenginex/core/interfaces.py`, add after `list_runs` (line 105):

```python
    @abstractmethod
    def list_experiments(self) -> list[dict[str, Any]]:
        """List all experiments. Returns list of dicts with at least 'id' and 'name'."""
```

- [ ] **Step 4: Implement in BuiltinTracker**

In `src/dataenginex/ml/tracking/builtin.py`, add method to `BuiltinTracker`:

```python
    def list_experiments(self) -> list[dict[str, Any]]:
        """List all experiments with their IDs and names."""
        data = self._load()
        return [
            {"id": exp_id, "name": exp["name"]}
            for exp_id, exp in data.get("experiments", {}).items()
        ]
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_builtin_tracker.py::test_list_experiments -v`
Expected: PASS

- [ ] **Step 6: Run full tracker test suite + typecheck**

Run: `uv run pytest tests/unit/test_builtin_tracker.py -v && uv run poe typecheck`
Expected: All pass

- [ ] **Step 7: Commit**

```bash
git add src/dataenginex/core/interfaces.py src/dataenginex/ml/tracking/builtin.py tests/unit/test_builtin_tracker.py
git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" -m "feat: add list_experiments() to BaseTracker and BuiltinTracker"
```

---

## Task 2: Interface Changes — BuiltinAgentRuntime.run() Returns Dict

**Files:**
- Modify: `src/dataenginex/core/interfaces.py:208-218`
- Modify: `src/dataenginex/ai/agents/builtin.py`
- Test: `tests/unit/test_builtin_agent.py` (find existing or create)

- [ ] **Step 1: Write failing test for run() dict return**

```python
# tests/unit/test_builtin_agent.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from dataenginex.ai.agents.builtin import BuiltinAgentRuntime


@dataclass
class MockLLMResponse:
    text: str


class MockLLM:
    """Mock LLM that implements the chat() interface used by BuiltinAgentRuntime."""

    def chat(self, messages: list[Any]) -> MockLLMResponse:
        return MockLLMResponse(text="ANSWER: Hello world")


@pytest.mark.asyncio()
async def test_run_returns_dict() -> None:
    agent = BuiltinAgentRuntime(
        llm=MockLLM(),
        system_prompt="You are a test agent.",
        tools=None,
        max_iterations=5,
    )
    result = await agent.run("Hello")
    assert isinstance(result, dict)
    assert "response" in result
    assert "iterations" in result
    assert "tool_calls" in result
    assert isinstance(result["response"], str)
    assert isinstance(result["iterations"], int)
    assert isinstance(result["tool_calls"], int)
    assert result["response"] == "Hello world"
    assert result["iterations"] >= 1
    assert result["tool_calls"] == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_builtin_agent.py::test_run_returns_dict -v`
Expected: FAIL — `AssertionError: assert isinstance('Hello world', dict)` (currently returns `str`)

- [ ] **Step 3: Update BaseAgentRuntime ABC**

In `src/dataenginex/core/interfaces.py`, change line 212:

```python
# Before:
    async def run(self, message: str, **kwargs: Any) -> str:
        """Execute agent with message and return response."""

# After:
    async def run(self, message: str, **kwargs: Any) -> dict[str, Any]:
        """Execute agent with message. Returns dict with 'response', 'iterations', 'tool_calls'."""
```

- [ ] **Step 4: Update BuiltinAgentRuntime.run()**

In `src/dataenginex/ai/agents/builtin.py`, modify the `run()` method to track tool_calls count and return a dict:

```python
    async def run(self, message: str, **kwargs: Any) -> dict[str, Any]:
        """Execute the agent loop and return structured result."""
        self._history.append({"role": "user", "content": message})
        response = ""
        iterations = 0
        tool_calls = 0

        for i in range(self.max_iterations):
            iterations = i + 1
            step_result = await self.step(message, **kwargs)

            if step_result.get("tool"):
                tool_calls += 1

            if step_result.get("done"):
                response = step_result.get("response", "")
                break
        else:
            response = f"Max iterations ({self.max_iterations}) reached"

        self._history.append({"role": "assistant", "content": response})
        return {
            "response": response,
            "iterations": iterations,
            "tool_calls": tool_calls,
        }
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_builtin_agent.py::test_run_returns_dict -v`
Expected: PASS

- [ ] **Step 6: Fix any callers of agent.run() that expect str**

Search for callers:
Run: `rg "await.*\.run\(" src/dataenginex/ --type py` and `rg "agent.*\.run\(" src/dataenginex/ --type py`

Update any caller that does `result = await agent.run(msg)` and uses `result` as a string to use `result["response"]` instead. Known caller: `src/dataenginex/cli/train.py` (if it calls agents).

- [ ] **Step 7: Run full test suite + typecheck**

Run: `uv run poe test && uv run poe typecheck`
Expected: All pass

- [ ] **Step 8: Commit**

```bash
git add src/dataenginex/core/interfaces.py src/dataenginex/ai/agents/builtin.py tests/unit/test_builtin_agent.py
git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" -m "feat: BuiltinAgentRuntime.run() returns dict with response/iterations/tool_calls"
```

---

## Task 3: Pydantic Response/Request Schemas

**Files:**
- Create: `src/dataenginex/api/schemas.py`
- Test: `tests/unit/test_api_schemas.py`

- [ ] **Step 1: Write tests for schema validation**

```python
# tests/unit/test_api_schemas.py
from __future__ import annotations

from dataenginex.api.schemas import (
    AgentChatRequest,
    AgentChatResponse,
    AgentDetailResponse,
    AgentListResponse,
    ComponentHealthResponse,
    DriftReportResponse,
    ExperimentListResponse,
    FeatureGetResponse,
    FeatureSaveRequest,
    ModelDetailResponse,
    ModelListResponse,
    PipelineResultResponse,
    PredictionRequest,
    PredictionResponse,
    PromoteRequest,
    QualitySummaryResponse,
    ServiceUnavailableResponse,
    SourceListResponse,
    ToolDetailResponse,
    ToolListResponse,
    WarehouseLayerResponse,
)


class TestSchemaValidation:
    def test_pipeline_result_response(self) -> None:
        resp = PipelineResultResponse(
            pipeline="ingest",
            success=True,
            rows_input=100,
            rows_output=95,
            steps_completed=3,
            duration_ms=1200.5,
        )
        assert resp.pipeline == "ingest"
        assert resp.success is True

    def test_service_unavailable_response(self) -> None:
        resp = ServiceUnavailableResponse(
            error="service_unavailable",
            component="llm",
            message="LLM provider not running",
        )
        assert resp.component == "llm"

    def test_agent_chat_request(self) -> None:
        req = AgentChatRequest(message="Hello")
        assert req.message == "Hello"

    def test_agent_chat_response(self) -> None:
        resp = AgentChatResponse(
            agent="data-analyst",
            response="The answer is 42",
            iterations=2,
            tool_calls=1,
        )
        assert resp.iterations == 2

    def test_prediction_request(self) -> None:
        req = PredictionRequest(model_name="my-model", features={"x": 1.0})
        assert req.model_name == "my-model"

    def test_promote_request(self) -> None:
        req = PromoteRequest(stage="production")
        assert req.stage == "production"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_api_schemas.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'dataenginex.api.schemas'`

- [ ] **Step 3: Create schemas module**

```python
# src/dataenginex/api/schemas.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_api_schemas.py -v`
Expected: PASS

- [ ] **Step 5: Typecheck**

Run: `uv run poe typecheck`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/dataenginex/api/schemas.py tests/unit/test_api_schemas.py
git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" -m "feat: add Pydantic request/response schemas for all API routers"
```

---

## Task 4: Lifespan Context Manager

**Files:**
- Modify: `src/dataenginex/api/factory.py`
- Test: `tests/unit/test_api_factory.py`

- [ ] **Step 1: Write failing test for lifespan initialization**

Add to `tests/unit/test_api_factory.py`:

```python
from unittest.mock import MagicMock, patch


class TestLifespan:
    def test_pipeline_runner_initialized(self, client) -> None:
        """After app startup, pipeline_runner should be on app.state."""
        assert hasattr(client.app.state, "pipeline_runner")
        assert client.app.state.pipeline_runner is not None

    def test_tracker_initialized(self, client) -> None:
        """After app startup, tracker should be on app.state."""
        assert hasattr(client.app.state, "tracker")
        assert client.app.state.tracker is not None

    def test_feature_store_initialized(self, client) -> None:
        """After app startup, feature_store should be on app.state."""
        assert hasattr(client.app.state, "feature_store")
        assert client.app.state.feature_store is not None

    def test_serving_engine_initialized(self, client) -> None:
        """After app startup, serving_engine should be on app.state."""
        assert hasattr(client.app.state, "serving_engine")
        assert client.app.state.serving_engine is not None

    def test_agents_dict_initialized(self, client) -> None:
        """After app startup, agents dict should exist (may be empty)."""
        assert hasattr(client.app.state, "agents")
        assert isinstance(client.app.state.agents, dict)

    def test_llm_graceful_degradation(self) -> None:
        """LLM failure should not prevent app startup."""
        config = DexConfig(project=ProjectConfig(name="test-degraded"))
        with patch(
            "dataenginex.api.factory.get_llm_provider",
            side_effect=Exception("Ollama not running"),
        ):
            app = create_app(config)
            with TestClient(app) as tc:
                assert tc.app.state.llm is None

    def test_lineage_initialized(self, client) -> None:
        """After app startup, lineage should be on app.state."""
        assert hasattr(client.app.state, "lineage")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_api_factory.py::TestLifespan -v`
Expected: FAIL — `AssertionError: assert hasattr(...)` (no lifespan sets these)

- [ ] **Step 3: Implement lifespan in factory.py**

Replace the contents of `src/dataenginex/api/factory.py`:

```python
"""FastAPI application factory.

Creates a fully configured DEX API from ``DexConfig``.

Usage::

    from dataenginex.api.factory import create_app
    app = create_app(config)
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from dataenginex.config.schema import DexConfig

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[no-untyped-def]
    """Initialize all backends at startup, tear down on shutdown."""
    config: DexConfig = app.state.config

    # 1. Data backends
    from dataenginex.data.pipeline.runner import PipelineRunner
    from dataenginex.warehouse.lineage import PersistentLineage

    app.state.pipeline_runner = PipelineRunner(config)
    app.state.lineage = PersistentLineage(".dex/lineage.json")

    # 2. ML backends
    from dataenginex.ml.features import feature_store_registry
    from dataenginex.ml.registry import ModelRegistry
    from dataenginex.ml.serving_engine import serving_registry
    from dataenginex.ml.tracking import tracker_registry

    tracker_cls = tracker_registry.get(config.ml.tracking.backend)
    app.state.tracker = tracker_cls()

    fs_cls = feature_store_registry.get(config.ml.features.backend)
    app.state.feature_store = fs_cls(**config.ml.features.options)

    app.state.model_registry = ModelRegistry(model_dir=".dex/models")

    serving_cls = serving_registry.get(config.ml.serving.engine)
    app.state.serving_engine = serving_cls(
        model_registry=app.state.model_registry,
        model_dir=".dex/models",
    )

    # 3. AI backends (graceful — server starts even if LLM unavailable)
    from dataenginex.ai.tools.builtin import register_builtin_tools
    from dataenginex.ml.llm import get_llm_provider

    register_builtin_tools()

    try:
        app.state.llm = get_llm_provider(
            config.ai.llm.provider,
            model=config.ai.llm.model,
        )
        logger.info("llm provider ready", provider=config.ai.llm.provider)
    except Exception:
        app.state.llm = None
        logger.warning("LLM provider unavailable, agent endpoints degraded")

    # 4. Agents — each gets its own LLM (or per-agent model override)
    from dataenginex.ai.agents import agent_registry
    from dataenginex.ai.tools import tool_registry

    app.state.agents = {}
    for name, agent_cfg in config.ai.agents.items():
        if app.state.llm is None:
            logger.warning("skipping agent %s — no LLM available", name)
            continue
        agent_llm = app.state.llm
        if agent_cfg.model:
            try:
                agent_llm = get_llm_provider(
                    config.ai.llm.provider,
                    model=agent_cfg.model,
                )
            except Exception:
                logger.warning("agent %s model override failed, using default", name)
        agent_cls = agent_registry.get(agent_cfg.runtime)
        # BuiltinAgentRuntime expects ToolRegistry, not list[ToolSpec].
        # Pass the global tool_registry — agents share the same tool set.
        # Per-agent tool filtering can be added later if needed.
        app.state.agents[name] = agent_cls(
            llm=agent_llm,
            system_prompt=agent_cfg.system_prompt,
            tools=tool_registry,
            max_iterations=agent_cfg.max_iterations,
        )
        logger.info("agent initialized", agent=name, runtime=agent_cfg.runtime)

    logger.info("lifespan startup complete")

    yield  # --- app runs ---

    # Shutdown
    if hasattr(app.state, "feature_store") and hasattr(app.state.feature_store, "close"):
        app.state.feature_store.close()
    logger.info("shutdown complete")


def create_app(config: DexConfig | None = None, **kwargs: Any) -> FastAPI:
    """Build a configured FastAPI application.

    Args:
        config: DexConfig instance. If None, uses minimal defaults.
        **kwargs: Extra FastAPI constructor kwargs.

    Returns:
        A FastAPI application instance.
    """
    from dataenginex.api.routers.health import router as health_router
    from dataenginex.api.routers.pipelines import router as pipelines_router
    from dataenginex.api.routers.root import router as root_router

    if config is None:
        from dataenginex.config.schema import ProjectConfig

        config = DexConfig(project=ProjectConfig(name="dataenginex"))

    app = FastAPI(
        title=config.project.name,
        version=config.project.version,
        description=config.project.description or "DataEngineX API",
        lifespan=lifespan,
        **kwargs,
    )

    # Store config on app state (lifespan reads it)
    app.state.config = config

    # CORS (innermost — must be last added, which means first in the chain)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.server.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(root_router)
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(pipelines_router, prefix="/api/v1")

    logger.info(
        "app created",
        name=config.project.name,
        version=config.project.version,
    )

    return app
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_api_factory.py -v`
Expected: All PASS (existing tests + new TestLifespan)

- [ ] **Step 5: Typecheck**

Run: `uv run poe typecheck`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/dataenginex/api/factory.py tests/unit/test_api_factory.py
git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" -m "feat: add lifespan context manager — initializes all backends at startup"
```

---

## Task 5: Middleware Stack

**Files:**
- Modify: `src/dataenginex/api/factory.py`
- Test: `tests/unit/test_api_factory.py`

- [ ] **Step 1: Write failing test for middleware presence**

Add to `tests/unit/test_api_factory.py`:

```python
class TestMiddleware:
    def test_request_logging_middleware(self, client) -> None:
        """Request logging middleware adds X-Request-ID header."""
        resp = client.get("/")
        assert "x-request-id" in resp.headers

    def test_metrics_middleware_tracks_requests(self, client) -> None:
        """Metrics middleware should track HTTP requests."""
        client.get("/")
        resp = client.get("/metrics")
        assert resp.status_code == 200
        # Prometheus metrics should contain request counter
        assert b"http_requests_total" in resp.content
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_api_factory.py::TestMiddleware -v`
Expected: FAIL — no X-Request-ID header (middleware not wired)

- [ ] **Step 3: Wire middleware in factory.py**

Add middleware calls in `create_app()`, **after** CORS and **before** router includes. Middleware is added in reverse order (last added = outermost):

```python
    # Middleware stack (outermost → innermost):
    # RequestLogging → Metrics → Auth → RateLimit → CORS
    # Added in reverse order because FastAPI wraps last-added as outermost.

    # Rate limiting (innermost of our custom middleware)
    import os
    if os.environ.get("DEX_RATE_LIMIT_ENABLED", "").lower() == "true":
        from dataenginex.api.rate_limit import RateLimitMiddleware
        app.add_middleware(RateLimitMiddleware)

    # Auth
    if config.server.auth.enabled:
        from dataenginex.api.auth import AuthMiddleware
        app.add_middleware(AuthMiddleware)

    # Prometheus metrics
    if config.observability.metrics:
        from dataenginex.middleware.metrics_middleware import PrometheusMetricsMiddleware
        app.add_middleware(PrometheusMetricsMiddleware)

    # Request logging (outermost — added last)
    from dataenginex.middleware.request_logging import RequestLoggingMiddleware
    app.add_middleware(RequestLoggingMiddleware)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_api_factory.py::TestMiddleware -v`
Expected: PASS

- [ ] **Step 5: Run full factory test suite**

Run: `uv run pytest tests/unit/test_api_factory.py -v`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add src/dataenginex/api/factory.py tests/unit/test_api_factory.py
git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" -m "feat: wire middleware stack — request logging, metrics, auth, rate limiting"
```

---

## Task 6: Pipeline Run — Real Execution

**Files:**
- Modify: `src/dataenginex/api/routers/pipelines.py`
- Modify: `tests/unit/test_api_factory.py`

- [ ] **Step 1: Write failing test for real pipeline execution**

Add to `tests/unit/test_api_factory.py`:

```python
class TestPipelineExecution:
    def test_run_pipeline_returns_result(self, client) -> None:
        """POST /api/v1/pipelines/{name}/run returns PipelineResult fields."""
        resp = client.post("/api/v1/pipelines/ingest/run")
        assert resp.status_code == 200
        data = resp.json()
        # Should have PipelineResult fields, not stub "triggered"
        assert "success" in data
        assert "rows_input" in data
        assert "rows_output" in data
        assert "steps_completed" in data
        assert "pipeline" in data
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_api_factory.py::TestPipelineExecution -v`
Expected: FAIL — `AssertionError: assert 'success' in {'pipeline': 'ingest', 'status': 'triggered', ...}`

- [ ] **Step 3: Update pipelines router**

Replace `src/dataenginex/api/routers/pipelines.py`:

```python
"""Pipelines router — ``/api/v1/pipelines``."""

from __future__ import annotations

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

    import time

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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_api_factory.py::TestPipelineExecution -v`
Expected: PASS (or may need mock `pipeline_runner` on app.state — adjust fixture if needed)

- [ ] **Step 5: Update existing pipeline test**

The existing `test_run_pipeline` expects `"status": "triggered"`. Update it to match the new response shape:

```python
    def test_run_pipeline(self, client) -> None:
        resp = client.post("/api/v1/pipelines/ingest/run")
        assert resp.status_code == 200
        data = resp.json()
        assert "pipeline" in data
        assert data["pipeline"] == "ingest"
        assert "success" in data
```

- [ ] **Step 6: Run full test suite**

Run: `uv run pytest tests/unit/test_api_factory.py -v && uv run poe typecheck`
Expected: All PASS

- [ ] **Step 7: Commit**

```bash
git add src/dataenginex/api/routers/pipelines.py tests/unit/test_api_factory.py
git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" -m "feat: pipeline run endpoint executes real PipelineRunner instead of stub"
```

---

## Task 7: Data Router

**Files:**
- Create: `src/dataenginex/api/routers/data.py`
- Create: `tests/unit/test_data_router.py`
- Modify: `src/dataenginex/api/factory.py` (include router)

- [ ] **Step 1: Write tests for data router**

```python
# tests/unit/test_data_router.py
"""Tests for the data router — /api/v1/data."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from dataenginex.api.routers.data import router
from dataenginex.config.schema import (
    DataConfig,
    DexConfig,
    PipelineConfig,
    ProjectConfig,
    SourceConfig,
)


@pytest.fixture()
def app() -> FastAPI:
    config = DexConfig(
        project=ProjectConfig(name="test-data"),
        data=DataConfig(
            sources={"movies": SourceConfig(type="csv", path="movies.csv")},
            pipelines={"ingest": PipelineConfig(source="movies")},
        ),
    )
    app = FastAPI()
    app.state.config = config

    # Mock lineage
    mock_lineage = MagicMock()
    mock_lineage.all_events = []
    mock_lineage.get_event.return_value = None
    app.state.lineage = mock_lineage

    app.include_router(router, prefix="/api/v1")
    return app


@pytest.fixture()
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


class TestSourcesEndpoints:
    def test_list_sources(self, client: TestClient) -> None:
        resp = client.get("/api/v1/data/sources")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1
        assert data["sources"][0]["name"] == "movies"

    def test_get_source(self, client: TestClient) -> None:
        resp = client.get("/api/v1/data/sources/movies")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "movies"
        assert data["type"] == "csv"

    def test_get_source_not_found(self, client: TestClient) -> None:
        resp = client.get("/api/v1/data/sources/nonexistent")
        assert resp.status_code == 404


class TestLineageEndpoints:
    def test_list_lineage(self, client: TestClient) -> None:
        resp = client.get("/api/v1/data/lineage")
        assert resp.status_code == 200
        data = resp.json()
        assert "events" in data

    def test_get_lineage_event_not_found(self, client: TestClient) -> None:
        resp = client.get("/api/v1/data/lineage/nonexistent")
        assert resp.status_code == 404


class TestWarehouseEndpoints:
    def test_list_layers(self, client: TestClient) -> None:
        resp = client.get("/api/v1/data/warehouse/layers")
        assert resp.status_code == 200
        data = resp.json()
        assert "layers" in data
        # Default medallion layers
        layer_names = [l["name"] for l in data["layers"]]
        assert "bronze" in layer_names


class TestQualityEndpoints:
    def test_quality_summary(self, client: TestClient) -> None:
        resp = client.get("/api/v1/data/quality/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert "pipelines" in data
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_data_router.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'dataenginex.api.routers.data'`

- [ ] **Step 3: Create data router**

```python
# src/dataenginex/api/routers/data.py
"""Data router — ``/api/v1/data``."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request

router = APIRouter(prefix="/data", tags=["data"])


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
        raise HTTPException(status_code=404, detail=f"Layer '{layer}' not found. Valid: {valid_layers}")
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
    return event.to_dict()


# --- Quality ---

@router.get("/quality/summary")
def quality_summary(request: Request) -> dict[str, Any]:
    """Aggregate quality metrics across pipelines."""
    config = request.app.state.config
    pipelines_quality: list[dict[str, Any]] = []
    for name, pipe_cfg in config.data.pipelines.items():
        pipelines_quality.append({
            "pipeline": name,
            "has_quality_gate": pipe_cfg.quality is not None,
        })
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
```

- [ ] **Step 4: Include router in factory.py**

Add to `create_app()` router includes:

```python
    from dataenginex.api.routers.data import router as data_router
    app.include_router(data_router, prefix="/api/v1")
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_data_router.py -v`
Expected: All PASS

- [ ] **Step 6: Typecheck**

Run: `uv run poe typecheck`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/dataenginex/api/routers/data.py tests/unit/test_data_router.py src/dataenginex/api/factory.py
git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" -m "feat: add data router — sources, lineage, quality endpoints"
```

---

## Task 8: ML Router

**Files:**
- Create: `src/dataenginex/api/routers/ml.py`
- Create: `tests/unit/test_ml_router.py`
- Modify: `src/dataenginex/api/factory.py` (include router)

- [ ] **Step 1: Write tests for ML router**

```python
# tests/unit/test_ml_router.py
"""Tests for the ML router — /api/v1/ml."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from dataenginex.api.routers.ml import router


@pytest.fixture()
def app() -> FastAPI:
    app = FastAPI()

    # Mock tracker
    mock_tracker = MagicMock()
    mock_tracker.list_experiments.return_value = [
        {"id": "abc123", "name": "exp-1"},
    ]
    mock_tracker.create_experiment.return_value = "abc123"
    mock_tracker.list_runs.return_value = []
    app.state.tracker = mock_tracker

    # Mock model registry
    mock_registry = MagicMock()
    mock_registry.list_all.return_value = []
    app.state.model_registry = mock_registry

    # Mock serving engine
    mock_serving = MagicMock()
    mock_serving.list_models.return_value = []
    app.state.serving_engine = mock_serving

    # Mock feature store
    mock_fs = MagicMock()
    mock_fs.list_feature_groups.return_value = ["user_features"]
    mock_fs.get_features.return_value = []
    app.state.feature_store = mock_fs

    app.include_router(router, prefix="/api/v1")
    return app


@pytest.fixture()
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


class TestExperiments:
    def test_list_experiments(self, client: TestClient) -> None:
        resp = client.get("/api/v1/ml/experiments")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1

    def test_create_experiment(self, client: TestClient) -> None:
        resp = client.post("/api/v1/ml/experiments/new-exp")
        assert resp.status_code == 200


class TestModels:
    def test_list_models(self, client: TestClient) -> None:
        resp = client.get("/api/v1/ml/models")
        assert resp.status_code == 200
        data = resp.json()
        assert "models" in data


class TestFeatures:
    def test_list_feature_groups(self, client: TestClient) -> None:
        resp = client.get("/api/v1/ml/features")
        assert resp.status_code == 200
        data = resp.json()
        assert "groups" in data


class TestPredictions:
    def test_predict(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/ml/predictions",
            json={"model_name": "test", "features": {"x": 1.0}},
        )
        assert resp.status_code == 200
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_ml_router.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Create ML router**

```python
# src/dataenginex/api/routers/ml.py
"""ML router — ``/api/v1/ml``."""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter, HTTPException, Request

from dataenginex.api.schemas import (
    ExperimentListResponse,
    FeatureGetResponse,
    FeatureSaveRequest,
    ModelListResponse,
    PredictionRequest,
    PredictionResponse,
    PromoteRequest,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/ml", tags=["ml"])


# --- Experiments ---

@router.get("/experiments", response_model=ExperimentListResponse)
def list_experiments(request: Request) -> ExperimentListResponse:
    """List all experiments."""
    tracker = request.app.state.tracker
    experiments = tracker.list_experiments()
    return ExperimentListResponse(experiments=experiments, count=len(experiments))


@router.post("/experiments/{name}")
def create_experiment(name: str, request: Request) -> dict[str, Any]:
    """Create a new experiment."""
    tracker = request.app.state.tracker
    exp_id = tracker.create_experiment(name)
    return {"id": exp_id, "name": name}


@router.get("/experiments/{name}/runs")
def list_runs(name: str, request: Request) -> dict[str, Any]:
    """List runs for an experiment."""
    tracker = request.app.state.tracker
    # Find experiment ID by name
    experiments = tracker.list_experiments()
    exp = next((e for e in experiments if e["name"] == name), None)
    if exp is None:
        raise HTTPException(status_code=404, detail=f"Experiment '{name}' not found")
    runs = tracker.list_runs(exp["id"])
    return {"experiment": name, "runs": runs, "count": len(runs)}


# --- Models ---

@router.get("/models", response_model=ModelListResponse)
def list_models(request: Request) -> ModelListResponse:
    """List registered models."""
    registry = request.app.state.model_registry
    models = registry.list_all() if hasattr(registry, "list_all") else []
    return ModelListResponse(models=models, count=len(models))


@router.get("/models/{name}")
def get_model(name: str, request: Request) -> dict[str, Any]:
    """Get model details."""
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
def promote_model(name: str, body: PromoteRequest, request: Request) -> dict[str, Any]:
    """Promote a model to a new stage."""
    registry = request.app.state.model_registry
    model = registry.get_latest(name)
    if model is None:
        raise HTTPException(status_code=404, detail=f"Model '{name}' not found")
    model.stage = body.stage
    registry.register(model)
    return {"name": name, "stage": body.stage, "promoted": True}


# --- Predictions ---

@router.post("/predictions", response_model=PredictionResponse)
def predict(body: PredictionRequest, request: Request) -> PredictionResponse:
    """Run a prediction."""
    engine = request.app.state.serving_engine
    try:
        result = engine.predict(body.model_name, body.features)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return PredictionResponse(
        model_name=body.model_name,
        prediction=result,
    )


# --- Features ---

@router.get("/features")
def list_feature_groups(request: Request) -> dict[str, Any]:
    """List all feature groups."""
    fs = request.app.state.feature_store
    groups = fs.list_feature_groups()
    return {"groups": groups, "count": len(groups)}


@router.get("/features/{group}", response_model=FeatureGetResponse)
def get_features(
    group: str,
    request: Request,
    entity_ids: str = "",
) -> FeatureGetResponse:
    """Get features for entity IDs (comma-separated query param)."""
    fs = request.app.state.feature_store
    ids = [eid.strip() for eid in entity_ids.split(",") if eid.strip()] if entity_ids else []
    features = fs.get_features(group, ids) if ids else []
    result = features if isinstance(features, list) else []
    return FeatureGetResponse(feature_group=group, features=result)


@router.post("/features/{group}")
def save_features(group: str, body: FeatureSaveRequest, request: Request) -> dict[str, Any]:
    """Save features to a feature group."""
    fs = request.app.state.feature_store
    fs.save_features(group, body.data, body.entity_key)
    return {"feature_group": group, "saved": len(body.data)}


# --- Drift ---

@router.get("/drift/{pipeline_name}")
def check_drift(pipeline_name: str, request: Request) -> dict[str, Any]:
    """Check drift status for a pipeline."""
    config = request.app.state.config
    if pipeline_name not in config.data.pipelines:
        raise HTTPException(status_code=404, detail=f"Pipeline '{pipeline_name}' not found")

    from dataenginex.ml.drift import DriftDetector

    detector = DriftDetector(
        psi_threshold=config.ml.drift.threshold,
    )
    # Drift requires reference and current data
    # For now, return no_baseline until pipeline has run and stored reference
    return {
        "pipeline": pipeline_name,
        "status": "no_baseline",
        "reports": [],
        "message": "Run pipeline at least once to establish baseline",
    }
```

- [ ] **Step 4: Include router in factory.py**

Add to `create_app()`:

```python
    from dataenginex.api.routers.ml import router as ml_router
    app.include_router(ml_router, prefix="/api/v1")
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_ml_router.py -v`
Expected: All PASS

- [ ] **Step 6: Typecheck**

Run: `uv run poe typecheck`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/dataenginex/api/routers/ml.py tests/unit/test_ml_router.py src/dataenginex/api/factory.py
git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" -m "feat: add ML router — experiments, models, predictions, features, drift endpoints"
```

---

## Task 9: AI Router

**Files:**
- Create: `src/dataenginex/api/routers/ai.py`
- Create: `tests/unit/test_ai_router.py`
- Modify: `src/dataenginex/api/factory.py` (include router)

- [ ] **Step 1: Write tests for AI router**

```python
# tests/unit/test_ai_router.py
"""Tests for the AI router — /api/v1/ai."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from dataenginex.api.routers.ai import router
from dataenginex.config.schema import AgentConfig, AiConfig, DexConfig, ProjectConfig


@pytest.fixture()
def app() -> FastAPI:
    config = DexConfig(
        project=ProjectConfig(name="test-ai"),
        ai=AiConfig(
            agents={
                "data-analyst": AgentConfig(
                    runtime="builtin",
                    system_prompt="You analyze data.",
                    tools=["query_sql"],
                    max_iterations=5,
                ),
            },
        ),
    )
    app = FastAPI()
    app.state.config = config

    # Mock agents
    mock_agent = AsyncMock()
    mock_agent.run.return_value = {
        "response": "The answer is 42",
        "iterations": 2,
        "tool_calls": 1,
    }
    app.state.agents = {"data-analyst": mock_agent}
    app.state.llm = MagicMock()

    app.include_router(router, prefix="/api/v1")
    return app


@pytest.fixture()
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


class TestAgentEndpoints:
    def test_list_agents(self, client: TestClient) -> None:
        resp = client.get("/api/v1/ai/agents")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1

    def test_get_agent(self, client: TestClient) -> None:
        resp = client.get("/api/v1/ai/agents/data-analyst")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "data-analyst"
        assert data["runtime"] == "builtin"

    def test_get_agent_not_found(self, client: TestClient) -> None:
        resp = client.get("/api/v1/ai/agents/nonexistent")
        assert resp.status_code == 404

    def test_agent_chat(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/ai/agents/data-analyst/chat",
            json={"message": "What is 6 * 7?"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["agent"] == "data-analyst"
        assert data["response"] == "The answer is 42"
        assert data["iterations"] == 2
        assert data["tool_calls"] == 1

    def test_agent_chat_not_found(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/ai/agents/nonexistent/chat",
            json={"message": "Hello"},
        )
        assert resp.status_code == 404


class TestToolEndpoints:
    def test_list_tools(self, client: TestClient) -> None:
        resp = client.get("/api/v1/ai/tools")
        assert resp.status_code == 200
        data = resp.json()
        assert "tools" in data
        assert "count" in data
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_ai_router.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Create AI router**

```python
# src/dataenginex/api/routers/ai.py
"""AI router — ``/api/v1/ai``."""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter, HTTPException, Request

from dataenginex.api.schemas import (
    AgentChatRequest,
    AgentChatResponse,
    AgentDetailResponse,
    AgentListResponse,
    ServiceUnavailableResponse,
    ToolListResponse,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/ai", tags=["ai"])


# --- Agents ---

@router.get("/agents", response_model=AgentListResponse)
def list_agents(request: Request) -> AgentListResponse:
    """List all configured agents."""
    config = request.app.state.config
    agents = [
        {
            "name": name,
            "runtime": cfg.runtime,
            "model": cfg.model,
            "tools": cfg.tools,
            "max_iterations": cfg.max_iterations,
        }
        for name, cfg in config.ai.agents.items()
    ]
    return AgentListResponse(agents=agents, count=len(agents))


@router.get("/agents/{name}", response_model=AgentDetailResponse)
def get_agent(name: str, request: Request) -> AgentDetailResponse:
    """Get agent configuration details."""
    config = request.app.state.config
    if name not in config.ai.agents:
        raise HTTPException(status_code=404, detail=f"Agent '{name}' not found")
    cfg = config.ai.agents[name]
    return AgentDetailResponse(
        name=name,
        runtime=cfg.runtime,
        model=cfg.model,
        tools=cfg.tools,
        max_iterations=cfg.max_iterations,
    )


@router.post("/agents/{name}/chat", response_model=AgentChatResponse)
async def agent_chat(name: str, body: AgentChatRequest, request: Request) -> AgentChatResponse:
    """Send a message to an agent and get a sync response."""
    agents = request.app.state.agents
    if name not in agents:
        if name in request.app.state.config.ai.agents:
            raise HTTPException(
                status_code=503,
                detail={"error": "service_unavailable", "component": "agent", "message": f"Agent '{name}' not initialized (LLM unavailable)"},
            )
        raise HTTPException(status_code=404, detail=f"Agent '{name}' not found")

    agent = agents[name]
    result = await agent.run(body.message)
    return AgentChatResponse(
        agent=name,
        response=result["response"],
        iterations=result["iterations"],
        tool_calls=result["tool_calls"],
    )


# --- Tools ---

@router.get("/tools", response_model=ToolListResponse)
def list_tools(request: Request) -> ToolListResponse:
    """List all registered tools."""
    from dataenginex.ai.tools import tool_registry

    tools = []
    for tool_name in tool_registry.list():
        spec = tool_registry.get(tool_name)
        tools.append({
            "name": spec.name,
            "description": spec.description,
            "parameters": spec.parameters,
        })
    return ToolListResponse(tools=tools, count=len(tools))


@router.get("/tools/{name}")
def get_tool(name: str, request: Request) -> dict[str, Any]:
    """Get tool details."""
    from dataenginex.ai.tools import tool_registry

    if name not in tool_registry._tools:
        raise HTTPException(status_code=404, detail=f"Tool '{name}' not found")
    spec = tool_registry.get(name)
    return {
        "name": spec.name,
        "description": spec.description,
        "parameters": spec.parameters,
    }
```

- [ ] **Step 4: Include router in factory.py**

Add to `create_app()`:

```python
    from dataenginex.api.routers.ai import router as ai_router
    app.include_router(ai_router, prefix="/api/v1")
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_ai_router.py -v`
Expected: All PASS

- [ ] **Step 6: Typecheck**

Run: `uv run poe typecheck`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/dataenginex/api/routers/ai.py tests/unit/test_ai_router.py src/dataenginex/api/factory.py
git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" -m "feat: add AI router — agents, chat, tools endpoints"
```

---

## Task 10: System Router

**Files:**
- Create: `src/dataenginex/api/routers/system.py`
- Create: `tests/unit/test_system_router.py`
- Modify: `src/dataenginex/api/factory.py` (include router)

- [ ] **Step 1: Write tests for system router**

```python
# tests/unit/test_system_router.py
"""Tests for the system router — /api/v1/system."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from dataenginex.api.routers.system import router


@pytest.fixture()
def app() -> FastAPI:
    app = FastAPI()

    # Mock app state with various backends
    app.state.tracker = MagicMock()
    app.state.feature_store = MagicMock()
    app.state.serving_engine = MagicMock()
    app.state.llm = MagicMock()
    app.state.agents = {"test-agent": MagicMock()}
    app.state.pipeline_runner = MagicMock()

    app.include_router(router, prefix="/api/v1")
    return app


@pytest.fixture()
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


class TestComponentHealth:
    def test_list_components(self, client: TestClient) -> None:
        resp = client.get("/api/v1/system/components")
        assert resp.status_code == 200
        data = resp.json()
        assert "components" in data
        names = [c["name"] for c in data["components"]]
        assert "tracker" in names
        assert "feature_store" in names
        assert "llm" in names

    def test_llm_unavailable_shows_degraded(self) -> None:
        app = FastAPI()
        app.state.tracker = MagicMock()
        app.state.feature_store = MagicMock()
        app.state.serving_engine = MagicMock()
        app.state.llm = None
        app.state.agents = {}
        app.state.pipeline_runner = MagicMock()
        app.include_router(router, prefix="/api/v1")
        client = TestClient(app)

        resp = client.get("/api/v1/system/components")
        data = resp.json()
        llm = next(c for c in data["components"] if c["name"] == "llm")
        assert llm["status"] == "unavailable"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_system_router.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Create system router**

```python
# src/dataenginex/api/routers/system.py
"""System router — ``/api/v1/system``."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

from dataenginex.api.schemas import ComponentHealthResponse

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/components", response_model=ComponentHealthResponse)
def list_components(request: Request) -> ComponentHealthResponse:
    """Per-component health status."""
    components: list[dict[str, Any]] = []

    # Check each backend on app.state
    state = request.app.state

    # Tracker
    components.append({
        "name": "tracker",
        "status": "healthy" if hasattr(state, "tracker") and state.tracker else "unavailable",
    })

    # Feature store
    components.append({
        "name": "feature_store",
        "status": "healthy" if hasattr(state, "feature_store") and state.feature_store else "unavailable",
    })

    # Serving engine
    components.append({
        "name": "serving_engine",
        "status": "healthy" if hasattr(state, "serving_engine") and state.serving_engine else "unavailable",
    })

    # LLM
    components.append({
        "name": "llm",
        "status": "healthy" if hasattr(state, "llm") and state.llm else "unavailable",
    })

    # Pipeline runner
    components.append({
        "name": "pipeline_runner",
        "status": "healthy" if hasattr(state, "pipeline_runner") and state.pipeline_runner else "unavailable",
    })

    # Agents
    agent_count = len(state.agents) if hasattr(state, "agents") else 0
    components.append({
        "name": "agents",
        "status": "healthy" if agent_count > 0 else "none_configured",
        "count": agent_count,
    })

    return ComponentHealthResponse(components=components)


@router.get("/logs")
def get_logs(
    request: Request,
    level: str | None = None,
    limit: int = 100,
    component: str | None = None,
) -> dict[str, Any]:
    """Recent structured log entries.

    Note: Full implementation requires a ring-buffer log processor.
    This returns an empty list as a placeholder until that is wired.
    """
    return {"logs": [], "count": 0, "message": "Log buffer not yet configured"}
```

- [ ] **Step 4: Include router in factory.py**

Add to `create_app()`:

```python
    from dataenginex.api.routers.system import router as system_router
    app.include_router(system_router, prefix="/api/v1")
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_system_router.py -v`
Expected: All PASS

- [ ] **Step 6: Typecheck**

Run: `uv run poe typecheck`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/dataenginex/api/routers/system.py tests/unit/test_system_router.py src/dataenginex/api/factory.py
git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" -m "feat: add system router — component health and logs endpoints"
```

---

## Task 11: Config Validation Enhancement

**Files:**
- Modify: `src/dataenginex/config/loader.py`
- Modify: `tests/unit/test_config_loader.py`

- [ ] **Step 1: Write failing tests for registry validation**

Add to `tests/unit/test_config_loader.py`:

```python
class TestRegistryValidation:
    def test_warns_on_unknown_tracker_backend(self) -> None:
        config = DexConfig(
            project=ProjectConfig(name="test"),
            ml=MlConfig(tracking=TrackerConfig(backend="nonexistent")),
        )
        warnings = validate_config(config)
        assert any("tracker" in w.lower() and "nonexistent" in w for w in warnings)

    def test_warns_on_unknown_agent_runtime(self) -> None:
        config = DexConfig(
            project=ProjectConfig(name="test"),
            ai=AiConfig(
                agents={"bot": AgentConfig(runtime="nonexistent", system_prompt="test")},
            ),
        )
        warnings = validate_config(config)
        assert any("agent" in w.lower() and "nonexistent" in w for w in warnings)

    def test_valid_config_no_warnings(self) -> None:
        config = DexConfig(project=ProjectConfig(name="test"))
        warnings = validate_config(config)
        assert len(warnings) == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_config_loader.py::TestRegistryValidation -v`
Expected: FAIL — no registry checks in `validate_config()`

- [ ] **Step 3: Extend validate_config()**

In `src/dataenginex/config/loader.py`, extend the `validate_config()` function:

```python
def validate_config(config: DexConfig) -> list[str]:
    """Run cross-reference validation on a loaded config.

    Returns a list of warning/error messages (empty = valid).
    Registry checks are warnings — extras may register backends at import time.
    """
    errors: list[str] = []

    source_names = set(config.data.sources.keys())
    pipeline_names = set(config.data.pipelines.keys())

    for pipe_name, pipe_cfg in config.data.pipelines.items():
        if pipe_cfg.source and pipe_cfg.source not in source_names:
            errors.append(f"Pipeline '{pipe_name}' references undefined source '{pipe_cfg.source}'")
        for dep in pipe_cfg.depends_on:
            if dep not in pipeline_names:
                errors.append(f"Pipeline '{pipe_name}' depends_on undefined pipeline '{dep}'")

    # Registry checks (warnings — extras register at import time)
    from dataenginex.ai.agents import agent_registry
    from dataenginex.ai.tools import tool_registry
    from dataenginex.ml.features import feature_store_registry
    from dataenginex.ml.serving_engine import serving_registry
    from dataenginex.ml.tracking import tracker_registry

    if config.ml.tracking.backend not in tracker_registry:
        errors.append(
            f"Warning: tracker backend '{config.ml.tracking.backend}' not found in registry "
            f"(available: {tracker_registry.list()})"
        )

    if config.ml.features.backend not in feature_store_registry:
        errors.append(
            f"Warning: feature store backend '{config.ml.features.backend}' not found in registry "
            f"(available: {feature_store_registry.list()})"
        )

    if config.ml.serving.engine not in serving_registry:
        errors.append(
            f"Warning: serving engine '{config.ml.serving.engine}' not found in registry "
            f"(available: {serving_registry.list()})"
        )

    for agent_name, agent_cfg in config.ai.agents.items():
        if agent_cfg.runtime not in agent_registry:
            errors.append(
                f"Warning: agent '{agent_name}' runtime '{agent_cfg.runtime}' not found in registry "
                f"(available: {agent_registry.list()})"
            )
        for tool_name in agent_cfg.tools:
            if tool_name not in tool_registry._tools:
                errors.append(
                    f"Warning: agent '{agent_name}' references unknown tool '{tool_name}'"
                )

    if errors:
        logger.warning("config validation issues", count=len(errors))

    return errors
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_config_loader.py -v`
Expected: All PASS

- [ ] **Step 5: Typecheck**

Run: `uv run poe typecheck`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/dataenginex/config/loader.py tests/unit/test_config_loader.py
git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" -m "feat: extend config validation with registry checks for backends and tools"
```

---

## Task 12: Integration Test — Full App Lifecycle

**Files:**
- Create: `tests/integration/test_full_app.py`

- [ ] **Step 1: Write integration test**

```python
# tests/integration/test_full_app.py
"""Integration test — full app lifecycle with lifespan."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from dataenginex.api.factory import create_app
from dataenginex.config.schema import (
    DataConfig,
    DexConfig,
    PipelineConfig,
    ProjectConfig,
    SourceConfig,
)


@pytest.fixture()
def full_app():
    config = DexConfig(
        project=ProjectConfig(name="integration-test", version="0.0.1"),
        data=DataConfig(
            sources={"movies": SourceConfig(type="csv", path="tests/fixtures/movies.csv")},
            pipelines={"ingest": PipelineConfig(source="movies")},
        ),
    )
    return create_app(config)


@pytest.fixture()
def client(full_app):
    with TestClient(full_app) as c:
        yield c


class TestFullAppLifecycle:
    def test_health(self, client) -> None:
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200

    def test_system_components(self, client) -> None:
        resp = client.get("/api/v1/system/components")
        assert resp.status_code == 200
        data = resp.json()
        assert any(c["name"] == "tracker" for c in data["components"])

    def test_list_pipelines(self, client) -> None:
        resp = client.get("/api/v1/pipelines/")
        assert resp.status_code == 200
        assert resp.json()["count"] == 1

    def test_data_sources(self, client) -> None:
        resp = client.get("/api/v1/data/sources")
        assert resp.status_code == 200
        assert resp.json()["count"] == 1

    def test_ml_experiments_empty(self, client) -> None:
        resp = client.get("/api/v1/ml/experiments")
        assert resp.status_code == 200
        assert resp.json()["count"] == 0

    def test_ai_agents_empty(self, client) -> None:
        resp = client.get("/api/v1/ai/agents")
        assert resp.status_code == 200
        assert resp.json()["count"] == 0

    def test_ai_tools_registered(self, client) -> None:
        resp = client.get("/api/v1/ai/tools")
        assert resp.status_code == 200
        assert resp.json()["count"] >= 1  # at least builtin tools
```

- [ ] **Step 2: Run integration test**

Run: `uv run pytest tests/integration/test_full_app.py -v`
Expected: All PASS

- [ ] **Step 3: Run full validation pipeline**

Run:
```bash
uv run poe lint
uv run poe typecheck
uv run poe test
```
Expected: All PASS

- [ ] **Step 4: Commit**

```bash
git add tests/integration/test_full_app.py
git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" -m "test: add integration test for full app lifecycle with all routers"
```

---

## Task 13: Final Validation

- [ ] **Step 1: Run full validation pipeline**

```bash
uv run poe lint
uv run poe typecheck
uv run poe test
uv run dex validate examples/dex.yaml
```

- [ ] **Step 2: Smoke test — start server and hit endpoints**

```bash
uv run poe dev &
sleep 3
curl http://localhost:17000/
curl http://localhost:17000/api/v1/health
curl http://localhost:17000/api/v1/system/components
curl http://localhost:17000/api/v1/data/sources
curl http://localhost:17000/api/v1/ml/experiments
curl http://localhost:17000/api/v1/ai/agents
curl http://localhost:17000/api/v1/ai/tools
kill %1
```

Expected: All return 200 with JSON responses

- [ ] **Step 3: Commit any fixes from validation**

If any issues found, fix and commit.
