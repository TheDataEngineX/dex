# Phase 6: Integration & DEX Studio Redesign

**Date:** 2026-03-22
**Status:** Approved
**Scope:** Wire all DEX engine components end-to-end through FastAPI lifespan, routers, and middleware. Redesign DEX Studio from scratch as a unified Data + ML + AI platform.

---

## Problem

Phases 1-5 built all subsystem components independently. Two critical gaps remain:

1. **DEX Engine (dex):** Components exist but aren't connected. `create_app()` doesn't initialize backends, no ML/AI/Data API endpoints, middleware not wired, pipeline run is a stub.

2. **DEX Studio (dex-studio):** Current 6-page structure with flat sidebar doesn't scale to the full Data + ML + AI surface. Needs a complete redesign to support all current features and future growth.

**Lockstep rule:** No Studio page without a DEX API endpoint. No DEX API endpoint without a Studio page.

---

## Part 1: DEX Engine Integration

### 1.1 Lifespan Context Manager

**File:** `src/dataenginex/api/factory.py`

AsyncContextManager lifespan that initializes all backends from `DexConfig` at startup:

```python
# Startup (pseudocode — registry.get() returns class, then instantiate)
async def lifespan(app: FastAPI):
    config = app.state.config

    # 1. ML backends
    tracker_cls = tracker_registry.get(config.ml.tracker)
    app.state.tracker = tracker_cls()

    fs_cls = feature_store_registry.get(config.ml.features.backend)
    app.state.feature_store = fs_cls(**config.ml.features.options)

    app.state.model_registry = ModelRegistry(model_dir=".dex/models")

    serving_cls = serving_registry.get(config.ml.serving.engine)
    app.state.serving_engine = serving_cls(
        model_registry=app.state.model_registry,
        model_dir=".dex/models",
    )

    # 2. Data backends
    app.state.pipeline_runner = PipelineRunner(config)

    # 3. AI backends (graceful — server starts even if LLM unavailable)
    register_builtin_tools()
    try:
        llm_config = LLMConfig(model=config.ai.llm.model)
        llm = get_llm_provider(config.ai.llm.provider, llm_config)
        app.state.llm = llm
    except Exception:
        app.state.llm = None
        logger.warning("LLM provider unavailable, agent endpoints degraded")

    # 4. Agents — each gets its own LLM (or per-agent model override)
    app.state.agents = {}
    for name, agent_cfg in config.ai.agents.items():
        agent_llm = app.state.llm  # default
        if agent_cfg.model and app.state.llm is not None:
            agent_llm_config = LLMConfig(model=agent_cfg.model)
            agent_llm = get_llm_provider(config.ai.llm.provider, agent_llm_config)
        agent_cls = agent_registry.get(agent_cfg.runtime)
        agent_tools = [tool_registry.get(t) for t in agent_cfg.tools if t in tool_registry._tools]
        app.state.agents[name] = agent_cls(
            llm=agent_llm,
            system_prompt=agent_cfg.system_prompt,
            tools=agent_tools,
            max_iterations=agent_cfg.max_iterations,
        )

    yield  # --- app runs ---

    # Shutdown
    if hasattr(app.state.feature_store, "close"):
        app.state.feature_store.close()
    logger.info("shutdown complete")
```

**Key decisions:**
- `BackendRegistry.get(name)` returns the class; caller instantiates with kwargs. No `create()` convenience method needed.
- LLM and agents use try/except with graceful degradation — server starts even if Ollama isn't running.
- Per-agent model overrides resolved from `AgentConfig.model` field.
- `feature_store.close()` guarded with `hasattr` since `BaseFeatureStore` ABC doesn't mandate it.
- Health endpoint reports per-component status (LLM available, tracker healthy, etc.).

### 1.2 Middleware Stack

**File:** `src/dataenginex/api/factory.py`

Wire existing middleware (no new code — just `app.add_middleware()` calls). Order outermost → innermost:

| Middleware | Condition | Source |
|-----------|-----------|--------|
| `RequestLoggingMiddleware` | Always | `middleware/request_logging.py` |
| `PrometheusMetricsMiddleware` | `config.observability.metrics` | `middleware/metrics_middleware.py` |
| `AuthMiddleware` | `config.server.auth.enabled` | `api/auth.py` |
| `RateLimitMiddleware` | `DEX_RATE_LIMIT_ENABLED` env var | `api/rate_limit.py` |
| `CORSMiddleware` | Already wired | built-in |

### 1.3 Interface Changes

Before adding routers, the following ABC changes are required:

- **`BaseTracker`** — add `list_experiments() -> list[dict]` abstract method. `BuiltinTracker` already stores experiments internally; expose via this method.
- **`BuiltinAgentRuntime.run()`** — currently returns `str`. Update to return `dict` with `{"response": str, "iterations": int, "tool_calls": int}` so the chat router can assemble the full response without tracking state itself.

### 1.4 Data Routers

**New file:** `src/dataenginex/api/routers/data.py`
**Prefix:** `/api/v1/data`

| Endpoint | Method | Purpose | Backend |
|----------|--------|---------|---------|
| `/sources` | GET | List configured sources | `app.state.config.data.sources` |
| `/sources/{name}` | GET | Source details + connection test | config + connector |
| `/warehouse/layers` | GET | List medallion layers with table counts | `LakehouseStorage` |
| `/warehouse/layers/{layer}/tables` | GET | Tables in a layer with row counts | `LakehouseStorage` |
| `/lineage` | GET | List lineage events | `LineageTracker` |
| `/lineage/{event_id}` | GET | Lineage detail for event | `LineageTracker` |
| `/quality/summary` | GET | Aggregate quality metrics | quality gates results |
| `/quality/{pipeline}` | GET | Quality results for a pipeline | quality gates |

### 1.5 ML Routers

**New file:** `src/dataenginex/api/routers/ml.py`
**Prefix:** `/api/v1/ml`

| Endpoint | Method | Purpose | Backend |
|----------|--------|---------|---------|
| `/experiments` | GET | List experiments | `app.state.tracker.list_experiments()` |
| `/experiments/{name}` | POST | Create experiment | `app.state.tracker` |
| `/experiments/{name}/runs` | GET | List runs | `app.state.tracker` |
| `/models` | GET | List models | `app.state.model_registry` |
| `/models/{name}` | GET | Model details (versions, stage) | `app.state.model_registry` |
| `/models/{name}/promote` | POST | Promote model stage | `app.state.model_registry` |
| `/predictions` | POST | Run prediction | `app.state.serving_engine` |
| `/features/{group}` | GET | Get features by entity keys | `app.state.feature_store` |
| `/features/{group}` | POST | Save features | `app.state.feature_store` |
| `/drift/{pipeline}` | GET | Check drift status | see below |

**Drift endpoint design:** `DriftDetector` is stateless — it compares reference vs current data on demand. The endpoint:

1. Gets pipeline name from URL
2. Loads reference data from the pipeline's gold-layer table (baseline snapshot)
3. Loads current data from the pipeline's latest run output
4. Runs `DriftDetector.detect(reference, current, config.ml.drift.monitor)` with columns from drift config
5. Returns PSI scores per feature + whether threshold exceeded

If no reference data exists yet, returns `{"status": "no_baseline", "message": "Run pipeline at least once to establish baseline"}`.

All endpoints use `response_model=` with Pydantic response models:

- `ExperimentListResponse`, `ExperimentDetail`
- `ModelListResponse`, `ModelDetail`, `PromoteRequest`, `PromoteResponse`
- `PredictionPayload`, `PredictionResult`
- `FeatureGetResponse`, `FeatureSavePayload`, `FeatureSaveResponse`
- `DriftReport` (reuse existing dataclass, convert to Pydantic)

**Error handling:** When a backend is unavailable (e.g., LLM not running), routers return HTTP 503 with `{"error": "service_unavailable", "component": "<name>", "message": "..."}`. This aligns with the health endpoint's per-component status reporting.

### 1.6 AI Routers

**New file:** `src/dataenginex/api/routers/ai.py`
**Prefix:** `/api/v1/ai`

| Endpoint | Method | Purpose | Backend |
|----------|--------|---------|---------|
| `/agents` | GET | List configured agents | `app.state.agents` |
| `/agents/{name}` | GET | Agent details | `app.state.agents` |
| `/agents/{name}/chat` | POST | Sync request/response chat | `agent.run()` |
| `/tools` | GET | List registered tools | `tool_registry.list()` |
| `/tools/{name}` | GET | Tool details (description, parameters) | `tool_registry.get()` |
| `/collections` | GET | List vector collections | config |
| `/collections/{name}/search` | POST | Search collection | retriever |
| `/collections/{name}/documents` | POST | Add documents | vectorstore |
| `/retrieve` | POST | Raw retrieval query | `app.state.retriever` |

**Chat endpoint contract:**

```
POST /api/v1/ai/agents/{name}/chat
Request:  {"message": "string"}
Response: {"agent": "name", "response": "string", "iterations": int, "tool_calls": int}
```

The `BuiltinAgentRuntime.run()` returns this dict directly (per interface change in 1.3). The router wraps it with the agent name.

Designed so SSE streaming (`Accept: text/event-stream`) can be added later without breaking the sync contract.

### 1.6a System Routers

**New file:** `src/dataenginex/api/routers/system.py`
**Prefix:** `/api/v1/system`

| Endpoint | Method | Purpose | Backend |
|----------|--------|---------|---------|
| `/components` | GET | Per-component health (tracker, feature_store, LLM, etc.) | app.state introspection |
| `/logs` | GET | Recent structured log entries (query params: level, limit, component) | Ring buffer or log file |
| `/traces` | GET | Recent traces (if tracing enabled) | OpenTelemetry collector |

**Note:** `/health`, `/metrics`, `/` already exist on root router. System router adds component-level detail and log/trace access. Logs endpoint reads from a bounded in-memory ring buffer (structlog processor appends entries). Traces endpoint proxies the OTLP collector or returns empty if tracing disabled.

### 1.6b Dashboard Data Strategy

Dashboard pages (`/data`, `/ml`, `/ai`) aggregate stats from multiple endpoints client-side. No dedicated "dashboard" API endpoint — Studio assembles the view by calling:

- `/data` dashboard: `GET /api/v1/pipelines` + `GET /api/v1/data/quality/summary`
- `/ml` dashboard: `GET /api/v1/ml/experiments` + `GET /api/v1/ml/models` + `GET /api/v1/ml/drift/*`
- `/ai` dashboard: `GET /api/v1/ai/agents` + `GET /api/v1/ai/collections`

This avoids bespoke aggregation endpoints and keeps the API granular.

### 1.7 Pipeline Run → Actual Execution

**File:** `src/dataenginex/api/routers/pipelines.py`

Update `POST /api/v1/pipelines/{name}/run`:
1. Get `PipelineRunner` from `app.state.pipeline_runner`
2. Execute synchronously (DuckDB pipelines complete in ms-seconds)
3. Return `PipelineResult` with status, rows_read, rows_written, duration, errors

**Note:** Pipeline run uses sync `def` (not `async def`). FastAPI runs sync endpoint handlers in a threadpool by default, which is correct for DuckDB operations.

### 1.8 Config Validation Enhancement

**File:** `src/dataenginex/config/loader.py`

Extend `validate_config()` with additional checks:
- Pipeline `source` references a defined source in `data.sources`
- Pipeline `depends_on` references other defined pipelines
- `ml.tracker` backend exists in `tracker_registry`
- `ml.features.backend` exists in `feature_store_registry`
- `ml.serving.engine` exists in `serving_registry`
- Agent `runtime` exists in `agent_registry`
- Agent `tools` reference registered tool names

Returns warnings (not hard failures) for registry checks — extras may register backends at import time.

---

## Part 2: DEX Studio Redesign

### 2.1 App Shell Architecture

**Pattern:** Two-level domain nav + command palette + breadcrumbs (Options B + C combined)

**Top bar (left → right):**
1. Logo
2. Project switcher dropdown (name, version, health indicator)
3. Separator
4. Domain tabs: **Data** | **ML** | **AI** | **System**
5. Flex spacer
6. Command palette trigger (Ctrl+K) — search/jump to any page, project, or action
7. Connection status indicator (green/red dot + label)

**Section sidebar:** Changes per active domain tab. Grouped with uppercase section headers. Includes quick actions at bottom.

**Content area:** Breadcrumbs at top (`Domain › Section › Page`), then page content.

### 2.2 Project Management

**Launch screen (Project Hub):**
- Centered layout with logo, search bar, action buttons
- Actions: **+ New Project**, **Import dex.yaml**, **From Template**
- Recent projects list with cards showing: icon, name, summary (pipelines/experiments/agents count), version, health status, last activity
- Clicking a project enters the domain shell

**In-app switcher:**
- Compact dropdown in top bar (left of domain tabs)
- Shows current project name + version + health dot
- Dropdown lists recent projects + "All Projects" link back to hub
- Switching projects reloads app state from the new project's DEX engine instance

**Project config:**
- Each project maps to a DEX engine URL + optional auth token
- Stored in `~/.dex-studio/projects.yaml`:
  ```yaml
  projects:
    movie-analytics:
      url: http://localhost:17000
      token: null
      icon: movie
    sales-forecasting:
      url: http://prod-dex:17000
      token: ${DEX_PROD_TOKEN}
      icon: chart
  ```

### 2.3 Domain: Data

**Sidebar sections:**

| Section | Pages |
|---------|-------|
| Overview | Dashboard |
| Operations | Pipelines, Sources, Warehouse |
| Observability | Quality Gates, Lineage |

**Pages:**

| Route | Page | Key Features |
|-------|------|-------------|
| `/data` | Dashboard | Metric cards (total runs, success rate, avg duration, rows today), recent pipeline activity |
| `/data/pipelines` | Pipelines | Pipeline table (name, source, status, last run, schedule, run button), DAG view toggle, run history |
| `/data/sources` | Sources | Configured sources table, connection test, source details |
| `/data/warehouse` | Warehouse | Medallion layer browser (Bronze/Silver/Gold), table inspector, row counts |
| `/data/quality` | Quality Gates | Aggregate quality metrics, per-pipeline check results, completeness/uniqueness/freshness scores |
| `/data/lineage` | Lineage | Event-based lineage graph, source-to-destination tracing |

### 2.4 Domain: ML

**Sidebar sections:**

| Section | Pages |
|---------|-------|
| Overview | Dashboard |
| Lifecycle | Experiments, Models, Predictions |
| Features | Feature Store, Drift Monitor |

**Pages:**

| Route | Page | Key Features |
|-------|------|-------------|
| `/ml` | Dashboard | Model count, active experiments, drift alerts, recent training runs |
| `/ml/experiments` | Experiments | Experiment list, run comparison table (params + metrics side by side), create/trigger training |
| `/ml/models` | Models | Model registry table (name, version, stage, metrics), promote action, version history |
| `/ml/predictions` | Predictions | Prediction playground (select model, input features as JSON, get prediction), request history |
| `/ml/features` | Feature Store | Feature group browser, schema inspector, entity key lookup, data preview, save new features |
| `/ml/drift` | Drift Monitor | PSI scores per feature, threshold indicators, drift history timeline, alert configuration |

### 2.5 Domain: AI

**Sidebar sections:**

| Section | Pages |
|---------|-------|
| Overview | Dashboard |
| Agents | Agent Chat, Tools |
| Knowledge | Collections, Retrieval |

**Pages:**

| Route | Page | Key Features |
|-------|------|-------------|
| `/ai` | Dashboard | Active agents, collection sizes, recent conversations, tool usage stats |
| `/ai/agents` | Agent Chat | Agent selector in header, chat interface (left ~65%), collapsible right inspector panel |
| `/ai/tools` | Tools | Registered tools table (name, description, parameters), test tool execution |
| `/ai/collections` | Collections | Collection list with doc count and embedding model, add documents, collection settings |
| `/ai/retrieval` | Retrieval | Search playground (query input, strategy selector, top_k slider), results with scores and metadata |

**Agent Chat Layout (Chat + Inspector):**
- **Left panel (~65%):** Chat messages with user/agent bubbles. Tool calls rendered as expandable inline blocks showing tool name, args, result, and duration. Input bar at bottom.
- **Right panel (~35%, collapsible):**
  - Agent config (runtime, model, max iterations, memory type)
  - Available tools list with descriptions
  - Session stats (messages, tool calls, total time, iterations)
  - Click a tool call in chat to inspect full args/response in panel

### 2.6 Domain: System

**Sidebar sections:**

| Section | Pages |
|---------|-------|
| Health | Status, Components |
| Observability | Metrics, Logs, Traces |
| Config | Settings, Connection |

**Pages:**

| Route | Page | Key Features |
|-------|------|-------------|
| `/system` | Status | Overall health, liveness/readiness/startup probes, uptime |
| `/system/components` | Components | Per-component health table (tracker, feature store, LLM, vectorstore, etc.) |
| `/system/metrics` | Metrics | Prometheus metrics display (request count, latency, error rate) |
| `/system/logs` | Logs | Structured log viewer — reads from DEX engine's JSON log output via `GET /api/v1/system/logs` |
| `/system/traces` | Traces | OpenTelemetry trace viewer — reads from OTLP collector via `GET /api/v1/system/traces`. Shows placeholder if tracing disabled. |
| `/system/settings` | Settings | Connection config (URL, token, timeout), UI preferences (theme, poll interval), test connection |
| `/system/connection` | Connection | Multi-project connection manager, environment switcher |

### 2.7 Component Library

Reusable components (redesigned from scratch):

| Component | Purpose |
|-----------|---------|
| `app_shell.py` | Top bar + domain tabs + project switcher + command palette |
| `domain_sidebar.py` | Section sidebar that changes per active domain |
| `breadcrumb.py` | Context breadcrumb bar |
| `metric_card.py` | Large KPI display (number, label, trend) |
| `status_badge.py` | Colored status pill (healthy, degraded, unhealthy, stale) |
| `data_table.py` | Sortable, filterable table with row actions |
| `chat_message.py` | Chat bubble (user or agent) with tool call rendering |
| `tool_call_block.py` | Expandable tool call display (name, args, result, duration) |
| `inspector_panel.py` | Collapsible right panel for detail views |
| `command_palette.py` | Ctrl+K search/jump overlay |
| `project_card.py` | Project card for hub and switcher |
| `empty_state.py` | Placeholder for pages with no data yet |

### 2.8 Theme

Carry forward existing dark-first palette with refinements:

| Token | Value | Usage |
|-------|-------|-------|
| `--bg-primary` | `#0f1117` | App background |
| `--bg-secondary` | `#1a1d27` | Cards, panels |
| `--bg-sidebar` | `#13151f` | Sidebar background |
| `--bg-hover` | `#1e2235` | Hover states |
| `--accent` | `#6366f1` | Active tab, buttons, links |
| `--accent-light` | `#a5b4fc` | Code highlights, tool names |
| `--text-primary` | `#f1f5f9` | Primary text |
| `--text-muted` | `#94a3b8` | Secondary text |
| `--text-dim` | `#64748b` | Tertiary text |
| `--text-faint` | `#475569` | Labels, section headers |
| `--border` | `#2d3348` | Borders, dividers |
| `--success` | `#22c55e` | Healthy, passing |
| `--warning` | `#f59e0b` | Degraded, stale |
| `--error` | `#ef4444` | Unhealthy, failed |

Light theme support via CSS custom properties toggle (future enhancement).

### 2.9 Data Flow

```
User clicks project → Studio loads project config (URL + token)
  → DexClient connects to DEX engine at that URL
  → Domain tabs become available
  → Each page calls DexClient methods → HTTP to DEX engine → response rendered

Project Hub:
  ~/.dex-studio/projects.yaml → list projects → show cards

In-app:
  DexClient.health() → System/Status
  DexClient.list_pipelines() → Data/Pipelines
  DexClient.list_experiments() → ML/Experiments
  DexClient.list_agents() → AI/Agents
  DexClient.agent_chat(name, message) → AI/Agent Chat
  etc.
```

### 2.10 DexClient API Expansion

New methods needed on `DexClient` to match new DEX engine endpoints:

```python
# Data (new)
async def list_sources(self) -> list[dict]
async def get_source(self, name: str) -> dict
async def run_pipeline(self, name: str) -> dict
async def warehouse_layers(self) -> list[dict]  # already exists, verify path
async def warehouse_tables(self, layer: str) -> list[dict]
async def data_quality_summary(self) -> dict  # already exists, verify path
async def data_quality_pipeline(self, pipeline: str) -> dict

# ML
async def list_experiments(self) -> list[dict]
async def create_experiment(self, name: str) -> dict
async def list_runs(self, experiment: str) -> list[dict]
async def list_models(self) -> list[dict]  # already exists
async def promote_model(self, name: str, stage: str) -> dict
async def predict(self, model_name: str, features: dict) -> dict  # already exists
async def get_features(self, group: str, entity_keys: list) -> dict
async def save_features(self, group: str, data: list[dict]) -> dict
async def check_drift(self, pipeline: str) -> dict

# AI
async def list_agents(self) -> list[dict]
async def get_agent(self, name: str) -> dict
async def agent_chat(self, name: str, message: str) -> dict
async def list_tools(self) -> list[dict]
async def get_tool(self, name: str) -> dict
async def list_collections(self) -> list[dict]
async def search_collection(self, name: str, query: str, top_k: int) -> dict
async def add_documents(self, collection: str, documents: list[dict]) -> dict
async def retrieve(self, query: str, strategy: str, top_k: int) -> dict

# System (new)
async def components(self) -> list[dict]
async def logs(self, level: str | None, limit: int) -> list[dict]
async def traces(self, limit: int) -> list[dict]
```

---

## Part 3: File Inventory

### DEX Engine (dex repo)

| Action | File | Purpose |
|--------|------|---------|
| Modified | `src/dataenginex/core/interfaces.py` | Add `list_experiments()` to `BaseTracker` |
| Modified | `src/dataenginex/ml/tracking/builtin.py` | Implement `list_experiments()` |
| Modified | `src/dataenginex/ai/agents/builtin.py` | `run()` returns dict with iterations/tool_calls |
| Modified | `src/dataenginex/api/factory.py` | Lifespan + middleware + new routers |
| Modified | `src/dataenginex/api/routers/pipelines.py` | Real pipeline execution |
| Modified | `src/dataenginex/config/loader.py` | Enhanced validation |
| Created | `src/dataenginex/api/routers/data.py` | Data API endpoints (sources, warehouse, lineage, quality) |
| Created | `src/dataenginex/api/routers/ml.py` | ML API endpoints |
| Created | `src/dataenginex/api/routers/ai.py` | AI API endpoints (incl. tools) |
| Created | `src/dataenginex/api/routers/system.py` | System API endpoints (components, logs, traces) |
| Created | `tests/unit/test_data_router.py` | Data router tests |
| Created | `tests/unit/test_ml_router.py` | ML router tests |
| Created | `tests/unit/test_ai_router.py` | AI router tests |
| Created | `tests/unit/test_system_router.py` | System router tests |
| Modified | `tests/unit/test_api_factory.py` | Lifespan + middleware tests |
| Modified | `tests/unit/test_config_loader.py` | Enhanced validation tests |

### DEX Studio (dex-studio repo) — Full Redesign

| Action | File | Purpose |
|--------|------|---------|
| Rewrite | `src/dex_studio/app.py` | New app bootstrap with domain routing |
| Rewrite | `src/dex_studio/client.py` | Expanded DexClient with all new endpoints |
| Rewrite | `src/dex_studio/config.py` | Multi-project config support |
| Rewrite | `src/dex_studio/theme.py` | Refined CSS custom properties |
| Rewrite | `src/dex_studio/cli.py` | Updated CLI options |
| Created | `src/dex_studio/components/app_shell.py` | Top bar + domain tabs + project switcher |
| Created | `src/dex_studio/components/domain_sidebar.py` | Per-domain section sidebar |
| Created | `src/dex_studio/components/breadcrumb.py` | Context breadcrumbs |
| Created | `src/dex_studio/components/data_table.py` | Reusable sortable table |
| Created | `src/dex_studio/components/chat_message.py` | Chat bubble + tool call rendering |
| Created | `src/dex_studio/components/tool_call_block.py` | Expandable tool call display |
| Created | `src/dex_studio/components/inspector_panel.py` | Collapsible right panel |
| Created | `src/dex_studio/components/command_palette.py` | Ctrl+K overlay |
| Created | `src/dex_studio/components/project_card.py` | Project card for hub/switcher |
| Created | `src/dex_studio/components/empty_state.py` | No-data placeholder |
| Rewrite | `src/dex_studio/components/metric_card.py` | Updated metric display |
| Rewrite | `src/dex_studio/components/status_card.py` | Renamed to status_badge.py |
| Delete | `src/dex_studio/components/sidebar.py` | Replaced by app_shell + domain_sidebar |
| Delete | `src/dex_studio/components/page_layout.py` | Replaced by app_shell |
| Created | `src/dex_studio/pages/project_hub.py` | Launch screen with project list |
| Rewrite | `src/dex_studio/pages/overview.py` | → `pages/data/dashboard.py` |
| Rewrite | `src/dex_studio/pages/health.py` | → `pages/system/status.py` |
| Rewrite | `src/dex_studio/pages/data_quality.py` | → `pages/data/quality.py` |
| Rewrite | `src/dex_studio/pages/lineage.py` | → `pages/data/lineage.py` |
| Rewrite | `src/dex_studio/pages/ml_models.py` | → `pages/ml/models.py` |
| Rewrite | `src/dex_studio/pages/settings.py` | → `pages/system/settings.py` |
| Created | `src/dex_studio/pages/data/pipelines.py` | Pipeline operations |
| Created | `src/dex_studio/pages/data/sources.py` | Source browser |
| Created | `src/dex_studio/pages/data/warehouse.py` | Medallion layer browser |
| Created | `src/dex_studio/pages/ml/dashboard.py` | ML overview |
| Created | `src/dex_studio/pages/ml/experiments.py` | Experiment tracking |
| Created | `src/dex_studio/pages/ml/predictions.py` | Prediction playground |
| Created | `src/dex_studio/pages/ml/features.py` | Feature store browser |
| Created | `src/dex_studio/pages/ml/drift.py` | Drift monitor |
| Created | `src/dex_studio/pages/ai/dashboard.py` | AI overview |
| Created | `src/dex_studio/pages/ai/agents.py` | Agent chat interface |
| Created | `src/dex_studio/pages/ai/tools.py` | Tool registry browser |
| Created | `src/dex_studio/pages/ai/collections.py` | Vector collection manager |
| Created | `src/dex_studio/pages/ai/retrieval.py` | Search playground |
| Created | `src/dex_studio/pages/system/components.py` | Component health |
| Created | `src/dex_studio/pages/system/metrics.py` | Prometheus viewer |
| Created | `src/dex_studio/pages/system/logs.py` | Log viewer |
| Created | `src/dex_studio/pages/system/traces.py` | Trace viewer |
| Created | `src/dex_studio/pages/system/connection.py` | Multi-project connections |

---

## Testing Strategy

### DEX Engine
- **Unit tests:** Each router tested with `FastAPI TestClient` + mock backends on `app.state`
- **Transform tests:** Each new transform against DuckDB in-memory
- **Integration tests:** Full `create_app(config)` → lifespan → router calls → verify backends initialized
- **Validation tests:** Config with invalid references → warnings returned
- **Coverage target:** 80%+ on new code paths

### DEX Studio
- **Unit tests:** Each DexClient method with httpx mock
- **Component tests:** Each reusable component renders correctly
- **Page tests:** Each page with mocked DexClient returns expected structure
- **Integration test:** Full app startup with mock DEX engine
- **Coverage target:** 80%+ on new code paths

---

## Out of Scope (Future Tasks)

- SSE/WebSocket streaming for agent chat responses
- Light theme implementation
- Helm chart / infradex updates for new API surface
- MLflow, Qdrant, LanceDB extra backend implementations
- Background task queue for long-running pipelines
- Collection document chunking and embedding pipeline
- Distributed orchestration (Airflow/Dagster integration)
- PyPI distribution for dex-studio
- Multi-user authentication for dex-studio
