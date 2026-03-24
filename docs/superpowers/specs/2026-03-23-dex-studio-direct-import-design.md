# DEX Studio Direct Import Architecture

**Date:** 2026-03-23
**Status:** Approved
**Scope:** dex (dataenginex), dex-studio, careerdex example

## Problem

dex-studio connects to dataenginex via HTTP (DexClient → REST API → FastAPI → library). This creates:

1. **Operational friction** — users must start two processes (dex server + dex-studio)
2. **Serialization bugs** — 4 confirmed field-name mismatches between API responses and page expectations (sources `connector_type`/`type`, lineage `id`/`event_id`, `target`/`destination`, missing `layer`)
3. **Data-shape drift** — 7 pages display columns the library doesn't provide (fake metadata)
4. **Unnecessary complexity** — DexClient methods, DexAPIError handling, HTTP connection lifecycle, response model duplication

## Solution

Replace DexClient HTTP calls with direct Python library imports. dex-studio adds `dataenginex` as a pip dependency and calls library objects directly. Pages work with typed Python objects (dataclasses, Pydantic models) — no serialization boundary.

### Decision Record

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Repo structure | Separate repos (dex-studio depends on dataenginex via pip) | Independent release cycles, less disruptive |
| Integration approach | DexEngine service layer (Approach A) | Eliminates serialization boundary entirely |
| Missing page data | Simplify pages to match real library data | Don't add fake metadata to fill UI columns |
| Remote mode | `--remote` flag, raises NotImplementedError for now | Deferred — build when needed |
| API availability | Use `ui.run_with(dex_api)` — NiceGUI runs on top of dex FastAPI app | Single ASGI app, no mounting issues, API available at `/api/v1/*` |

---

## Architecture

### Before

```text
User starts dex server (port 17000)
User starts dex-studio (port 7860)
dex-studio → DexClient → HTTP → FastAPI → app.state → library objects
```

### After

```text
User runs: dex-studio path/to/project.yaml

dex-studio (single process, port 7860)
├── NiceGUI UI pages
│   └── import dataenginex directly via DexEngine
├── dex FastAPI app as ASGI host (via ui.run_with)
│   └── /api/v1/* endpoints available for external access
└── Config: loaded once at startup from project YAML
```

---

## DexEngine (replaces DexClient)

**File:** `dex-studio/src/dex_studio/engine.py`

**Prerequisite:** Bug fixes C6 (project_dir param) and C7 (lineage param) must be applied to dex core first. DexEngine depends on these new parameters existing on PipelineRunner.

```python
from dataenginex.config import load_config, validate_config
from dataenginex.data.pipeline.runner import PipelineRunner
from dataenginex.data.pipeline.run_history import PipelineRunHistory
from dataenginex.warehouse.lineage import PersistentLineage
from dataenginex.ml.registry import ModelRegistry
from dataenginex.ml.llm import LLMProvider

class DexEngine:
    """Local dataenginex engine — direct library access, no HTTP."""

    def __init__(self, config_path: str | Path) -> None:
        self.config_path = Path(config_path).resolve()
        self.project_dir = self.config_path.parent
        self.config = load_config(self.config_path)
        validate_config(self.config)

        # Project directory structure
        dex_dir = self.project_dir / ".dex"
        dex_dir.mkdir(parents=True, exist_ok=True)

        # Data backends
        self.lineage = PersistentLineage(dex_dir / "lineage.json")
        self.pipeline_runner = PipelineRunner(
            self.config,
            data_dir=dex_dir / "lakehouse",
            project_dir=self.project_dir,  # C6: resolve relative source paths
            lineage=self.lineage,           # C7: wired lineage recording
        )
        self.run_history = PipelineRunHistory(dex_dir / "pipeline_runs.json")

        # ML backends (graceful degradation — each wrapped in try/except)
        self.tracker = self._init_backend("tracker", ...)
        self.feature_store = self._init_backend("feature_store", ...)
        self.model_registry = ModelRegistry(
            persist_path=str(dex_dir / "models" / "registry.json")
        )
        self.serving_engine = self._init_backend("serving_engine", ...)

        # AI backends (graceful degradation)
        self.llm: LLMProvider | None = None
        self.agents: dict[str, BaseAgentRuntime] = {}
        self._init_ai()

    def _init_backend(self, name: str, ...) -> Any:
        """Initialize backend with try/except — log warning on failure, return None."""
        ...

    def warehouse_layers(self) -> list[dict[str, Any]]:
        """List medallion layers and table counts from .dex/lakehouse/.

        New method — this logic currently lives only in the API router.
        Moved here so pages can access it without HTTP.
        """
        lakehouse = self.project_dir / ".dex" / "lakehouse"
        layers = []
        for layer_name in ("bronze", "silver", "gold"):
            layer_path = lakehouse / layer_name
            table_count = len(list(layer_path.glob("*.parquet"))) if layer_path.exists() else 0
            layers.append({"name": layer_name, "table_count": table_count})
        return layers

    def warehouse_tables(self, layer: str) -> list[dict[str, Any]]:
        """List tables in a specific medallion layer."""
        layer_path = self.project_dir / ".dex" / "lakehouse" / layer
        if not layer_path.exists():
            return []
        tables = []
        for f in layer_path.glob("*.parquet"):
            try:
                tables.append({"name": f.stem, "path": str(f), "size_bytes": f.stat().st_size})
            except OSError:
                continue  # file deleted between glob and stat
        return tables

    def health(self) -> dict[str, Any]:
        """New method — returns component health summary."""
        ...

    def close(self) -> None:
        """Cleanup resources."""
        if hasattr(self, "feature_store") and hasattr(self.feature_store, "close"):
            self.feature_store.close()
```

### What pages access

| Domain | Access pattern | Returns |
|--------|---------------|---------|
| Sources | `engine.config.data.sources` | `dict[str, SourceConfig]` |
| Pipelines | `engine.config.data.pipelines` | `dict[str, PipelineConfig]` |
| Run pipeline | `await asyncio.to_thread(engine.pipeline_runner.run, name)` | `PipelineResult` |
| Run history | `engine.run_history.get_runs(name)` | `list[PipelineRunRecord]` |
| Warehouse layers | `engine.warehouse_layers()` | `list[dict]` (new method) |
| Warehouse tables | `engine.warehouse_tables(layer)` | `list[dict]` (new method) |
| Lineage | `engine.lineage.all_events` | `list[LineageEvent]` |
| Experiments | `engine.tracker.list_experiments()` | `list[dict]` |
| Models | `engine.model_registry.list_models()` | `list[str]` (model names only) |
| Model versions | `engine.model_registry.list_versions(name)` | `list[str]` (version names) |
| Model detail | `engine.model_registry.get(name, version)` | `ModelArtifact` |
| Features | `engine.feature_store.list_feature_groups()` | `list[str]` |
| Agents | `engine.agents` | `dict[str, BaseAgentRuntime]` |
| Agent chat | `await asyncio.to_thread(engine.agents[name].run, msg)` | `dict` |
| Health | `engine.health()` | `dict` (new method) |

---

## App Initialization

**File:** `dex-studio/src/dex_studio/app.py`

### Avoiding double-init (BLOCKER-4 fix)

`create_app()` registers a lifespan handler that creates new backend instances at startup. If we mount the dex API naively, the lifespan fires and creates a second set of backends — two DuckDB connections, two lineage stores, state divergence.

**Solution:** Use NiceGUI's `ui.run_with(fastapi_app)` pattern. This runs NiceGUI on top of an existing FastAPI app rather than mounting a sub-app. We modify `create_app()` to accept an optional `skip_lifespan=True` kwarg (or pass pre-initialized backends) so the lifespan does not re-create what DexEngine already owns.

```python
from dataenginex.api.factory import create_app

def start(config_path: str | None = None, remote_url: str | None = None):
    if remote_url:
        raise NotImplementedError("Remote mode not yet implemented. Use config path.")

    # Resolve config — show helpful error if not found
    resolved_path = Path(config_path or "dex.yaml").resolve()
    if not resolved_path.exists():
        sys.stderr.write(f"Config not found: {resolved_path}\n")
        sys.stderr.write("Usage: dex-studio <path-to-config.yaml>\n")
        sys.exit(1)

    engine = DexEngine(resolved_path)
    app.storage.general["engine"] = engine

    # Create dex FastAPI app with skip_lifespan — DexEngine owns all backends
    dex_api = create_app(engine.config, skip_lifespan=True)
    dex_api.state.config = engine.config
    dex_api.state.pipeline_runner = engine.pipeline_runner
    dex_api.state.lineage = engine.lineage
    dex_api.state.tracker = engine.tracker
    dex_api.state.feature_store = engine.feature_store
    dex_api.state.model_registry = engine.model_registry
    dex_api.state.serving_engine = engine.serving_engine
    dex_api.state.llm = engine.llm
    dex_api.state.agents = engine.agents

    app.on_shutdown(engine.close)

    # NiceGUI runs on top of the dex FastAPI app
    # API endpoints available at /api/v1/*, UI at all other routes
    ui.run_with(
        dex_api,
        title=f"DEX Studio — {engine.config.project.name}",
        port=7860,
        storage_secret="dex-studio-secret",
    )
```

### CLI

**File:** `dex-studio/src/dex_studio/cli.py`

```bash
dex-studio path/to/project.yaml        # local mode (default)
dex-studio --remote http://dex:17000   # remote mode (future — NotImplementedError)
dex-studio                              # looks for dex.yaml in CWD
```

---

## Page Migration Pattern

Every page changes from:

```python
# BEFORE
client: DexClient = app.storage.general.get("client")
try:
    data = await client.list_sources()
    for src in data.get("sources", []):
        src.get("connector_type", "—")  # wrong field name
except DexAPIError:
    show_error(...)
```

To:

```python
# AFTER
engine: DexEngine = app.storage.general.get("engine")
for name, src in engine.config.data.sources.items():
    src.type  # typed attribute — no field name bugs
```

**Sync→async bridging:** Only long-running operations need `asyncio.to_thread()`:

- `engine.pipeline_runner.run(name)` — pipeline execution
- `engine.agents[name].run(msg)` — agent chat

Everything else (config reads, lineage queries, model registry lookups) is fast synchronous access.

---

## Concurrency

NiceGUI runs on a single uvicorn worker. Multiple browser clients share the same `DexEngine` instance. `asyncio.to_thread()` runs blocking calls in a thread pool.

**Thread-safe by design:**

- DuckDB connections are created per-run in PipelineRunner (safe)
- Config access is read-only (safe)

**Needs locking (JSON-backed stores):**

- `PersistentLineage._events` — appended and serialized concurrently
- `PipelineRunHistory._records` — same pattern
- `ModelRegistry._models` — mutated on promote/register
- `BuiltinTracker._experiments` / `._runs` — mutated on create

**Fix:** Add `threading.Lock` to each JSON-backed store. Acquire on write operations (record, save, promote), release after file write. Read operations return copies (already the case for lineage `all_events`).

This is a dex core change (not dex-studio), added as **C8: Add threading locks to JSON-backed stores**.

---

## Bug Fixes (dex core)

### C1: Lakehouse path mismatch

**File:** `src/dataenginex/data/pipeline/runner.py`
**Fix:** Change `_data_dir` default from `Path(".dex/data")` to `Path(".dex/lakehouse")`.
**Note:** DexEngine passes explicit `data_dir` so this is less critical for the studio path, but standalone API usage still needs the fix.

### C2: CSV connector SQL injection

**File:** `src/dataenginex/data/connectors/csv.py`
**Fix:** Use DuckDB parameterized query or proper escaping for filepath.

### C3: Feature store SQL injection

**File:** `src/dataenginex/ml/features/builtin.py`
**Fix:** Validate and quote table names using DuckDB identifier quoting.

### C4: Factory backend init failures crash app

**File:** `src/dataenginex/api/factory.py`
**Fix:** Wrap all backend inits (tracker, feature_store, serving_engine) in try/except with graceful degradation, same as LLM already does. Add `skip_lifespan: bool` parameter to `create_app()` — when True, skip the lifespan context manager entirely (DexEngine owns initialization).

### C5: Lineage JSON corruption crashes app

**File:** `src/dataenginex/warehouse/lineage.py`
**Fix:** try/except around `json.loads()` in `_load()`, log warning, start with empty events.

### C6: Relative paths resolved from CWD

**File:** `src/dataenginex/data/pipeline/runner.py`
**Fix:** Add `project_dir: Path | None = None` param to `__init__`. Resolve `source_config.path` relative to `project_dir` when provided.

### C7: Lineage not wired to PipelineRunner

**File:** `src/dataenginex/data/pipeline/runner.py`
**Fix:** Add `lineage: PersistentLineage | None = None` param to `__init__`. Call `lineage.record()` at end of `_extract` and `_load`.

### C8: Thread safety for JSON-backed stores

**Files:** `warehouse/lineage.py`, `ml/registry.py`, `ml/tracking/builtin.py`, `ml/features/builtin.py`, `data/pipeline/run_history.py`
**Fix:** Add `threading.Lock` to each store. Acquire on write, release after file write.

---

## Page Data-Shape Fixes (dex-studio)

### S1: Agent chat — tool_calls is int, not list

**File:** `pages/ai/agents.py`, `components/chat_message.py`
**Fix:** Display tool_calls as a count badge, not an iterable list.

### S2: Models page — list returns names only

**File:** `pages/ml/models.py`
**Fix:** `model_registry.list_models()` returns `list[str]` (names only). Show model names; call `list_versions(name)` for version count. For detail view, call `model_registry.get(name, version)` which returns `ModelArtifact` with stage, metrics, created_at.

### S3: Experiments page — no status/created_at/run_count

**File:** `pages/ml/experiments.py`
**Fix:** Show only experiment id + name. Drop fake metadata columns.

### S4: Agent inspector — no description field

**File:** `pages/ai/agents.py`
**Fix:** Show `system_prompt` snippet from `engine.config.ai.agents[name].system_prompt` instead.

### S5: AI dashboard — no agent status

**File:** `pages/ai/dashboard.py`
**Fix:** Derive availability from `engine.agents` dict (present = available, absent = LLM unavailable).

### S6: Features page — unknown structure

**File:** `pages/ml/features.py`
**Fix:** `list_feature_groups()` returns group names. Simplify to show names. Detail view calls `get_features(group)`.

### S7: Drift page — guessing field names

**File:** `pages/ml/drift.py`
**Fix:** Align to actual `DriftReport` dataclass. Severity values are `"none"`, `"moderate"`, `"severe"` only — fix the drift.py field comment to remove `"minor"` (the classifier never returns it).

---

## New Feature: Pipeline Run History

**File (new):** `dex/src/dataenginex/data/pipeline/run_history.py`

```python
@dataclass
class PipelineRunRecord:
    run_id: str          # auto-generated hex
    pipeline_name: str
    timestamp: str       # ISO format
    success: bool
    rows_input: int
    rows_output: int
    steps_completed: int
    duration_ms: float
    error: str | None

class PipelineRunHistory:
    def __init__(self, persist_path: str | Path) -> None: ...
    def record(self, result: PipelineResult, duration_ms: float) -> PipelineRunRecord: ...
    def get_runs(self, pipeline_name: str) -> list[PipelineRunRecord]: ...
    @property
    def all_runs(self) -> list[PipelineRunRecord]: ...
```

JSON-backed store at `.dex/pipeline_runs.json`. DexEngine records after every `pipeline_runner.run()` call. Includes `threading.Lock` for concurrent safety (C8).

---

## CareerDEX Example Project

**Location:** `careerdex/` (standalone project directory)

```text
careerdex/
├── careerdex.yaml          # Full config: data + ML + AI
└── data/
    ├── jobs.csv            # 20 rows (18 active, 2 expired)
    ├── candidates.csv      # 15 rows (13 active, 2 inactive)
    ├── skills.csv          # 12 rows
    └── companies.csv       # 8 rows
```

**Pipelines:** ingest_jobs, clean_jobs, job_analytics, ingest_candidates, clean_candidates
**ML:** salary_predictor experiment
**AI:** career_advisor + job_matcher agents (Ollama — guide message when unavailable)

**Run:** `dex-studio careerdex/careerdex.yaml`

---

## What Gets Deleted

- `DexAPIError` exception class usage in pages
- All `try/except DexAPIError` blocks (24 pages)
- All dict key guessing patterns (`src.get("connector_type", "—")`)
- HTTP connection lifecycle (connect/close/is_connected)
- `StudioConfig.api_url`, `api_token` fields
- httpx as a required dependency (moves to optional for future remote mode)

## What Gets Preserved

- `client.py` — kept for future `RemoteDexEngine` adapter
- All NiceGUI components — unchanged (they render data, don't fetch it)
- Theme system — unchanged
- App shell, sidebar, breadcrumbs — unchanged

---

## .dex/ Directory Layout

DexEngine creates and manages this structure in the project directory:

```text
project/
├── project.yaml
├── data/                    # User's source data (CSV, etc.)
└── .dex/                    # Created by DexEngine
    ├── lakehouse/
    │   ├── bronze/          # Raw ingested parquet
    │   ├── silver/          # Cleaned/transformed parquet
    │   └── gold/            # Analytics-ready parquet
    ├── models/
    │   └── registry.json    # Model registry state
    ├── lineage.json         # Lineage event store
    └── pipeline_runs.json   # Pipeline run history
```

DexEngine creates `.dex/` and its subdirectories at init time. Each backend creates its own files on first write.

---

## Execution Order

1. **dex** — bug fixes (C1-C8) + pipeline run history feature + `skip_lifespan` param on `create_app`
2. **dex-studio** — architecture refactor (DexEngine + app init + page migration + data-shape fixes S1-S7)
3. **careerdex** — example project (YAML + CSV data)
4. **Smoke test** — `dex-studio careerdex/careerdex.yaml` end-to-end
