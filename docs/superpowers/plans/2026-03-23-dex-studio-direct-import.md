# DEX Studio Direct Import — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace dex-studio's HTTP client with direct dataenginex library imports, fix all core bugs, and ship a working careerdex example.

**Architecture:** DexEngine class replaces DexClient, wrapping all dataenginex backends. NiceGUI runs on top of the dex FastAPI app via `ui.run_with()`. Pages access typed Python objects directly — no serialization boundary.

**Tech Stack:** Python 3.13+ · dataenginex · NiceGUI · FastAPI · DuckDB · structlog · pytest

**Spec:** `docs/superpowers/specs/2026-03-23-dex-studio-direct-import-design.md`

---

## File Structure

### dex (dataenginex) — Modified Files

| File | Changes |
|------|---------|
| `src/dataenginex/data/pipeline/runner.py` | C1: default path, C6: project_dir param, C7: lineage param |
| `src/dataenginex/data/connectors/csv.py` | C2: SQL injection fix |
| `src/dataenginex/ml/features/builtin.py` | C3: SQL injection fix, C8: threading lock |
| `src/dataenginex/api/factory.py` | C4: skip_lifespan + graceful degradation |
| `src/dataenginex/warehouse/lineage.py` | C5: JSON corruption handling, C8: threading lock |
| `src/dataenginex/ml/registry.py` | C8: threading lock |
| `src/dataenginex/ml/tracking/builtin.py` | C8: threading lock |
| `src/dataenginex/ml/drift.py` | Fix severity docstring |

### dex (dataenginex) — New Files

| File | Purpose |
|------|---------|
| `src/dataenginex/data/pipeline/run_history.py` | JSON-backed pipeline run history store |
| `tests/unit/test_run_history.py` | Tests for PipelineRunHistory |

### dex-studio — Modified Files

| File | Changes |
|------|---------|
| `pyproject.toml` | Add dataenginex dependency |
| `src/dex_studio/app.py` | Replace DexClient with DexEngine, use ui.run_with |
| `src/dex_studio/cli.py` | Config path positional arg, --remote flag |
| `src/dex_studio/config.py` | Keep for StudioConfig (UI prefs only), remove API fields |
| All 24 page files under `src/dex_studio/pages/` | Replace client calls with engine access |
| `src/dex_studio/components/chat_message.py` | Fix tool_calls int vs list (S1) |

### dex-studio — New Files

| File | Purpose |
|------|---------|
| `src/dex_studio/engine.py` | DexEngine — direct library wrapper |

### careerdex — New Files

| File | Purpose |
|------|---------|
| `careerdex/careerdex.yaml` | Full project config (data + ML + AI) |
| `careerdex/data/jobs.csv` | 20 job postings |
| `careerdex/data/candidates.csv` | 15 candidates |
| `careerdex/data/skills.csv` | 12 skill categories |
| `careerdex/data/companies.csv` | 8 companies |

---

## Task 1: PipelineRunner Bug Fixes (C1 + C6 + C7)

**Files:**
- Modify: `dex/src/dataenginex/data/pipeline/runner.py`
- Modify: `dex/tests/unit/test_pipeline_runner.py`

### C1: Fix lakehouse path default

- [ ] **Step 1: Change default data_dir from `.dex/data` to `.dex/lakehouse`**

In `runner.py` line 73, change:

```python
# BEFORE
self._data_dir = data_dir or Path(".dex/data")

# AFTER
self._data_dir = data_dir or Path(".dex/lakehouse")
```

### C6: Add project_dir parameter for relative path resolution

- [ ] **Step 2: Add project_dir param to __init__**

Replace `runner.py` lines 71-74:

```python
# BEFORE
def __init__(self, config: DexConfig, data_dir: Path | None = None) -> None:
    self._config = config
    self._data_dir = data_dir or Path(".dex/data")
    self._data_dir.mkdir(parents=True, exist_ok=True)

# AFTER
def __init__(
    self,
    config: DexConfig,
    data_dir: Path | None = None,
    project_dir: Path | None = None,
    lineage: PersistentLineage | None = None,
) -> None:
    self._config = config
    self._data_dir = data_dir or Path(".dex/lakehouse")
    self._data_dir.mkdir(parents=True, exist_ok=True)
    self._project_dir = project_dir
    self._lineage = lineage
```

- [ ] **Step 3: Add import for PersistentLineage at top of file**

Add after existing imports (around line 28):

```python
from dataenginex.warehouse.lineage import PersistentLineage
```

- [ ] **Step 4: Resolve source paths relative to project_dir in _extract**

In `_extract` method, after line 143 (`connector_kwargs["path"] = source_config.path`), add path resolution:

```python
# BEFORE (line 142-144)
connector_kwargs: dict[str, Any] = dict(source_config.connection)
if source_config.path and "path" not in connector_kwargs:
    connector_kwargs["path"] = source_config.path

# AFTER
connector_kwargs: dict[str, Any] = dict(source_config.connection)
if source_config.path and "path" not in connector_kwargs:
    src_path = source_config.path
    if self._project_dir and not Path(src_path).is_absolute():
        src_path = str(self._project_dir / src_path)
    connector_kwargs["path"] = src_path
```

### C7: Wire lineage recording into extract and load

- [ ] **Step 5: Record lineage event after extract**

In `_extract`, after line 156 (`log.info("extract complete"...)`), before `return`:

```python
        log.info("extract complete", source=cfg.source, rows=len(raw_data))
        if self._lineage is not None:
            self._lineage.record(
                operation="ingest",
                layer="bronze",
                source=cfg.source,
                destination=f"bronze/{name}",
                input_count=len(raw_data),
                output_count=len(raw_data),
                pipeline_name=name,
                step_name="extract",
            )
        return len(raw_data)
```

- [ ] **Step 6: Record lineage event after load**

In `_load`, after line 232 (`log.info("load complete"...)`), before `return`:

```python
        log.info("load complete", layer=target_layer, path=str(output_path), rows=rows)
        if self._lineage is not None:
            self._lineage.record(
                operation="load",
                layer=target_layer,
                source=f"bronze/{name}",
                destination=str(output_path),
                input_count=rows,
                output_count=rows,
                pipeline_name=name,
                step_name="load",
            )
        return rows
```

- [ ] **Step 7: Update factory.py to pass lineage to PipelineRunner**

In `factory.py` lines 35-36, change order and pass lineage:

```python
# BEFORE
app.state.pipeline_runner = PipelineRunner(config)
app.state.lineage = PersistentLineage(".dex/lineage.json")

# AFTER
app.state.lineage = PersistentLineage(".dex/lineage.json")
app.state.pipeline_runner = PipelineRunner(config, lineage=app.state.lineage)
```

- [ ] **Step 8: Run existing pipeline runner tests**

```bash
cd /home/jay/workspace/DataEngineX/dex && uv run pytest tests/unit/test_pipeline_runner.py -v
```

Expected: All existing tests pass (the new params are optional with defaults).

- [ ] **Step 9: Add test for lineage wiring**

Add to `tests/unit/test_pipeline_runner.py`:

```python
def test_lineage_recorded_on_run(tmp_path: Path, simple_config: DexConfig) -> None:
    """Pipeline run records lineage events for extract and load."""
    lineage = PersistentLineage(tmp_path / "lineage.json")
    runner = PipelineRunner(simple_config, data_dir=tmp_path / "lakehouse", lineage=lineage)
    result = runner.run("test_pipeline")
    assert result.success
    events = lineage.all_events
    assert len(events) >= 2
    ops = [e.operation for e in events]
    assert "ingest" in ops
    assert "load" in ops
```

- [ ] **Step 10: Run tests**

```bash
cd /home/jay/workspace/DataEngineX/dex && uv run pytest tests/unit/test_pipeline_runner.py -v
```

- [ ] **Step 11: Run lint + typecheck**

```bash
cd /home/jay/workspace/DataEngineX/dex && uv run poe lint && uv run poe typecheck
```

- [ ] **Step 12: Commit**

```bash
cd /home/jay/workspace/DataEngineX/dex
git add src/dataenginex/data/pipeline/runner.py src/dataenginex/api/factory.py tests/unit/test_pipeline_runner.py
git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" -m "fix: PipelineRunner — lakehouse path, project_dir resolution, lineage wiring (C1+C6+C7)"
```

---

## Task 2: Security Fixes (C2 + C3)

**Files:**
- Modify: `dex/src/dataenginex/data/connectors/csv.py`
- Modify: `dex/src/dataenginex/ml/features/builtin.py`
- Test: `dex/tests/unit/test_csv_connector.py` (run existing, no changes)
- Test: `dex/tests/unit/test_builtin_feature_store.py` (run existing, no changes)

### C2: CSV connector SQL injection fix

- [ ] **Step 1: Fix SQL injection in csv.py read()**

In `csv.py` line 67, replace f-string with escaped path:

```python
# BEFORE
result = self._conn.execute(f"SELECT * FROM read_csv_auto('{filepath}')")

# AFTER
safe_path = str(filepath).replace("'", "''")
result = self._conn.execute(f"SELECT * FROM read_csv_auto('{safe_path}')")
```

- [ ] **Step 2: Run CSV connector tests**

```bash
cd /home/jay/workspace/DataEngineX/dex && uv run pytest tests/unit/test_csv_connector.py -v
```

### C3: Feature store SQL injection fix

- [ ] **Step 3: Fix SQL injection in builtin.py save_features()**

In `builtin.py` line 68, quote the table name:

```python
# BEFORE
self._conn.execute(
    f"CREATE OR REPLACE TABLE {feature_group} AS SELECT * FROM tbl"  # noqa: S608
)

# AFTER
safe_name = feature_group.replace('"', '""')
self._conn.execute(
    f'CREATE OR REPLACE TABLE "{safe_name}" AS SELECT * FROM tbl'  # noqa: S608
)
```

- [ ] **Step 4: Apply same fix to get_features() queries**

In `builtin.py` lines 96-97:

```python
# BEFORE
result = self._conn.execute(
    f"SELECT * FROM {feature_group} "  # noqa: S608
    f"WHERE CAST({entity_key} AS VARCHAR) IN ({placeholders})",

# AFTER
safe_name = feature_group.replace('"', '""')
safe_key = entity_key.replace('"', '""')
result = self._conn.execute(
    f'SELECT * FROM "{safe_name}" '  # noqa: S608
    f'WHERE CAST("{safe_key}" AS VARCHAR) IN ({placeholders})',
```

- [ ] **Step 5: Run feature store tests**

```bash
cd /home/jay/workspace/DataEngineX/dex && uv run pytest tests/unit/test_builtin_feature_store.py -v
```

- [ ] **Step 6: Lint + typecheck**

```bash
cd /home/jay/workspace/DataEngineX/dex && uv run poe lint && uv run poe typecheck
```

- [ ] **Step 7: Commit**

```bash
cd /home/jay/workspace/DataEngineX/dex
git add src/dataenginex/data/connectors/csv.py src/dataenginex/ml/features/builtin.py
git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" -m "fix: SQL injection in CSV connector and feature store (C2+C3)"
```

---

## Task 3: Infrastructure Fixes (C4 + C5 + C8)

**Files:**
- Modify: `dex/src/dataenginex/api/factory.py`
- Modify: `dex/src/dataenginex/warehouse/lineage.py`
- Modify: `dex/src/dataenginex/ml/registry.py`
- Modify: `dex/src/dataenginex/ml/tracking/builtin.py`
- Modify: `dex/src/dataenginex/ml/features/builtin.py`
- Modify: `dex/src/dataenginex/ml/drift.py`

### C4: Factory skip_lifespan + graceful degradation

- [ ] **Step 1: Add skip_lifespan param to create_app()**

In `factory.py`, modify `create_app` signature and the lifespan assignment:

```python
# BEFORE (line 119)
def create_app(config: DexConfig | None = None, **kwargs: Any) -> FastAPI:

# AFTER
def create_app(
    config: DexConfig | None = None,
    *,
    skip_lifespan: bool = False,
    **kwargs: Any,
) -> FastAPI:
```

And change the FastAPI constructor (line 144-149):

```python
# BEFORE
app = FastAPI(
    title=config.project.name,
    version=config.project.version,
    description=config.project.description or "DataEngineX API",
    lifespan=lifespan,
    **kwargs,
)

# AFTER
app = FastAPI(
    title=config.project.name,
    version=config.project.version,
    description=config.project.description or "DataEngineX API",
    lifespan=None if skip_lifespan else lifespan,
    **kwargs,
)
```

- [ ] **Step 2: Wrap ML backend inits in try/except in lifespan()**

In `factory.py`, wrap tracker, feature_store, serving_engine init (lines 47-62):

```python
    # 2. ML backends — import builtins first to trigger registry decoration
    import dataenginex.ml.features.builtin  # noqa: F401
    import dataenginex.ml.serving_engine.builtin  # noqa: F401
    import dataenginex.ml.tracking.builtin  # noqa: F401
    from dataenginex.ml.features import feature_store_registry
    from dataenginex.ml.registry import ModelRegistry
    from dataenginex.ml.serving_engine import serving_registry
    from dataenginex.ml.tracking import tracker_registry

    try:
        tracker_cls = tracker_registry.get(config.ml.tracking.backend)
        app.state.tracker = tracker_cls()
    except Exception:
        app.state.tracker = None
        logger.warning("tracker init failed, ML tracking degraded")

    try:
        fs_cls = feature_store_registry.get(config.ml.features.backend)
        app.state.feature_store = fs_cls(**config.ml.features.options)
    except Exception:
        app.state.feature_store = None
        logger.warning("feature store init failed, ML features degraded")

    model_registry = ModelRegistry(persist_path=".dex/models/registry.json")
    app.state.model_registry = model_registry

    try:
        serving_cls_any: Any = cast(Any, serving_registry.get(config.ml.serving.engine))
        app.state.serving_engine = serving_cls_any(
            model_registry=model_registry,
            model_dir=".dex/models",
        )
    except Exception:
        app.state.serving_engine = None
        logger.warning("serving engine init failed, predictions degraded")
```

### C5: Lineage JSON corruption handling

- [ ] **Step 3: Add try/except to lineage _load()**

In `lineage.py`, replace `_load()` (lines 182-189):

```python
    def _load(self) -> None:
        if not self._persist_path or not self._persist_path.exists():
            return
        try:
            raw = json.loads(self._persist_path.read_text())
            for item in raw:
                item.pop("timestamp", None)
                self._events.append(LineageEvent(**item))
            logger.info("lineage events loaded", count=len(self._events), path=str(self._persist_path))
        except (json.JSONDecodeError, TypeError, KeyError) as exc:
            logger.warning(
                "lineage file corrupted, starting fresh",
                path=str(self._persist_path),
                error=str(exc),
            )
            self._events = []
```

### C8: Threading locks for JSON-backed stores

- [ ] **Step 4: Add lock to PersistentLineage**

In `lineage.py`, add `import threading` at top. In `__init__`:

```python
def __init__(self, persist_path: str | Path | None = None) -> None:
    self._lock = threading.Lock()
    self._events: list[LineageEvent] = []
    ...
```

In `record()`:

```python
def record(self, **kwargs: Any) -> LineageEvent:
    event = LineageEvent(**kwargs)
    with self._lock:
        self._events.append(event)
        self._save()
    ...
    return event
```

- [ ] **Step 5: Add lock to ModelRegistry**

In `registry.py`, add `import threading` at top. In `__init__`:

```python
self._lock = threading.Lock()
```

Wrap `register()`, `promote()`, `_save()` calls with `with self._lock:`.

- [ ] **Step 6: Add lock to BuiltinTracker**

In `builtin.py` (tracking), add `import threading`. In `__init__`:

```python
self._lock = threading.Lock()
```

Wrap all `_save()` calls with `with self._lock:`.

- [ ] **Step 7: Add lock to BuiltinFeatureStore**

In `builtin.py` (features), add `import threading`. In `__init__`:

```python
self._lock = threading.Lock()
```

Wrap `save_features()` body with `with self._lock:`.

- [ ] **Step 8: Fix DriftReport severity docstring**

In `drift.py` line 42, fix the inline field comment:

```python
# BEFORE (line 42)
severity: str  # "none", "minor", "moderate", "severe"

# AFTER
severity: str  # "none", "moderate", "severe"
```

- [ ] **Step 9: Run all tests**

```bash
cd /home/jay/workspace/DataEngineX/dex && uv run poe test
```

- [ ] **Step 10: Lint + typecheck**

```bash
cd /home/jay/workspace/DataEngineX/dex && uv run poe lint && uv run poe typecheck
```

- [ ] **Step 11: Commit**

```bash
cd /home/jay/workspace/DataEngineX/dex
git add src/dataenginex/api/factory.py src/dataenginex/warehouse/lineage.py src/dataenginex/ml/registry.py src/dataenginex/ml/tracking/builtin.py src/dataenginex/ml/features/builtin.py src/dataenginex/ml/drift.py
git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" -m "fix: graceful backend degradation, lineage corruption handling, thread safety (C4+C5+C8)"
```

---

## Task 4: Pipeline Run History (New Feature)

**Files:**
- Create: `dex/src/dataenginex/data/pipeline/run_history.py`
- Modify: `dex/src/dataenginex/data/pipeline/__init__.py`
- Create: `dex/tests/unit/test_run_history.py`

- [ ] **Step 1: Write test file first (TDD)**

Create `tests/unit/test_run_history.py`:

```python
"""Tests for PipelineRunHistory."""
from __future__ import annotations

from pathlib import Path

from dataenginex.data.pipeline.run_history import PipelineRunHistory, PipelineRunRecord
from dataenginex.data.pipeline.runner import PipelineResult


def test_record_creates_entry(tmp_path: Path) -> None:
    history = PipelineRunHistory(tmp_path / "runs.json")
    result = PipelineResult(pipeline="test", success=True, rows_input=100, rows_output=95, steps_completed=3)
    rec = history.record(result, duration_ms=42.5)
    assert rec.pipeline_name == "test"
    assert rec.success is True
    assert rec.rows_input == 100
    assert rec.rows_output == 95
    assert rec.duration_ms == 42.5


def test_get_runs_filters_by_pipeline(tmp_path: Path) -> None:
    history = PipelineRunHistory(tmp_path / "runs.json")
    r1 = PipelineResult(pipeline="a", success=True)
    r2 = PipelineResult(pipeline="b", success=True)
    history.record(r1, duration_ms=10)
    history.record(r2, duration_ms=20)
    assert len(history.get_runs("a")) == 1
    assert len(history.get_runs("b")) == 1


def test_persistence_survives_reload(tmp_path: Path) -> None:
    path = tmp_path / "runs.json"
    h1 = PipelineRunHistory(path)
    h1.record(PipelineResult(pipeline="x", success=True), duration_ms=5)
    h2 = PipelineRunHistory(path)  # reload from disk
    assert len(h2.all_runs) == 1
    assert h2.all_runs[0].pipeline_name == "x"


def test_all_runs_returns_newest_first(tmp_path: Path) -> None:
    history = PipelineRunHistory(tmp_path / "runs.json")
    history.record(PipelineResult(pipeline="first", success=True), duration_ms=1)
    history.record(PipelineResult(pipeline="second", success=True), duration_ms=2)
    runs = history.all_runs
    assert runs[0].pipeline_name == "second"


def test_corrupted_json_starts_fresh(tmp_path: Path) -> None:
    path = tmp_path / "runs.json"
    path.write_text("NOT VALID JSON")
    history = PipelineRunHistory(path)
    assert len(history.all_runs) == 0
```

- [ ] **Step 2: Run tests — expect FAIL (module doesn't exist)**

```bash
cd /home/jay/workspace/DataEngineX/dex && uv run pytest tests/unit/test_run_history.py -v
```

- [ ] **Step 3: Implement PipelineRunHistory**

Create `src/dataenginex/data/pipeline/run_history.py`:

```python
"""JSON-backed pipeline run history store."""
from __future__ import annotations

import json
import secrets
import threading
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import structlog

from dataenginex.data.pipeline.runner import PipelineResult

logger = structlog.get_logger()

__all__ = ["PipelineRunHistory", "PipelineRunRecord"]


@dataclass
class PipelineRunRecord:
    """A single pipeline execution record."""

    run_id: str = field(default_factory=lambda: secrets.token_hex(6))
    pipeline_name: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(tz=UTC).isoformat())
    success: bool = False
    rows_input: int = 0
    rows_output: int = 0
    steps_completed: int = 0
    duration_ms: float = 0.0
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to plain dict."""
        return asdict(self)


class PipelineRunHistory:
    """Persistent pipeline run history backed by a JSON file."""

    def __init__(self, persist_path: str | Path) -> None:
        self._persist_path = Path(persist_path)
        self._records: list[PipelineRunRecord] = []
        self._lock = threading.Lock()
        if self._persist_path.exists():
            self._load()

    def record(self, result: PipelineResult, duration_ms: float) -> PipelineRunRecord:
        """Record a pipeline execution result."""
        rec = PipelineRunRecord(
            pipeline_name=result.pipeline,
            success=result.success,
            rows_input=result.rows_input,
            rows_output=result.rows_output,
            steps_completed=result.steps_completed,
            duration_ms=round(duration_ms, 2),
            error=result.error,
        )
        with self._lock:
            self._records.append(rec)
            self._save()
        return rec

    def get_runs(self, pipeline_name: str) -> list[PipelineRunRecord]:
        """Get runs for a specific pipeline, newest first."""
        return [r for r in reversed(self._records) if r.pipeline_name == pipeline_name]

    @property
    def all_runs(self) -> list[PipelineRunRecord]:
        """All runs, newest first."""
        return list(reversed(self._records))

    def _save(self) -> None:
        self._persist_path.parent.mkdir(parents=True, exist_ok=True)
        self._persist_path.write_text(
            json.dumps([r.to_dict() for r in self._records], indent=2, default=str)
        )

    def _load(self) -> None:
        try:
            raw = json.loads(self._persist_path.read_text())
            for item in raw:
                self._records.append(PipelineRunRecord(**item))
        except (json.JSONDecodeError, TypeError, KeyError) as exc:
            logger.warning("run history corrupted, starting fresh", error=str(exc))
            self._records = []
```

- [ ] **Step 4: Update `__init__.py` exports**

Replace `src/dataenginex/data/pipeline/__init__.py` with:

```python
from dataenginex.data.pipeline.dag import resolve_execution_order
from dataenginex.data.pipeline.run_history import PipelineRunHistory, PipelineRunRecord
from dataenginex.data.pipeline.runner import PipelineResult, PipelineRunner

__all__ = [
    "PipelineResult",
    "PipelineRunHistory",
    "PipelineRunRecord",
    "PipelineRunner",
    "resolve_execution_order",
]
```

- [ ] **Step 5: Run tests — expect PASS**

```bash
cd /home/jay/workspace/DataEngineX/dex && uv run pytest tests/unit/test_run_history.py -v
```

- [ ] **Step 6: Lint + typecheck**

```bash
cd /home/jay/workspace/DataEngineX/dex && uv run poe lint && uv run poe typecheck
```

- [ ] **Step 7: Commit**

```bash
cd /home/jay/workspace/DataEngineX/dex
git add src/dataenginex/data/pipeline/run_history.py src/dataenginex/data/pipeline/__init__.py tests/unit/test_run_history.py
git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" -m "feat: pipeline run history — JSON-backed execution tracker"
```

---

## Task 5: DexEngine Class (dex-studio)

**Files:**
- Create: `dex-studio/src/dex_studio/engine.py`
- Modify: `dex-studio/pyproject.toml`

- [ ] **Step 1: Add dataenginex dependency to pyproject.toml**

In `dex-studio/pyproject.toml`, add to `[project] dependencies`:

```toml
dependencies = [
    "dataenginex>=1.0",
    "nicegui>=2.0,<4.0",
    "pywebview>=5.0,<7.0",
    "httpx>=0.27",
    "pydantic>=2.0",
    "pyyaml>=6.0",
    "python-dotenv>=1.0",
    "rich>=14.0",
]
```

- [ ] **Step 2: Create engine.py**

Create `dex-studio/src/dex_studio/engine.py`:

```python
"""DexEngine — direct dataenginex library access, no HTTP.

Replaces DexClient for local mode. Wraps all dataenginex backends
and exposes them to NiceGUI pages as typed Python objects.
"""
from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

import structlog

from dataenginex.config import load_config, validate_config
from dataenginex.config.schema import DexConfig
from dataenginex.data.pipeline.run_history import PipelineRunHistory
from dataenginex.data.pipeline.runner import PipelineResult, PipelineRunner
from dataenginex.ml.registry import ModelRegistry
from dataenginex.warehouse.lineage import PersistentLineage

logger = structlog.get_logger()

__all__ = ["DexEngine"]


class DexEngine:
    """Local dataenginex engine — direct library access, no HTTP.

    Args:
        config_path: Path to a dex YAML config file.
    """

    def __init__(self, config_path: str | Path) -> None:
        self.config_path = Path(config_path).resolve()
        if not self.config_path.exists():
            msg = f"Config file not found: {self.config_path}"
            raise FileNotFoundError(msg)

        self.project_dir = self.config_path.parent
        self.config: DexConfig = load_config(self.config_path)
        validate_config(self.config)

        # Project directory structure
        self._dex_dir = self.project_dir / ".dex"
        self._dex_dir.mkdir(parents=True, exist_ok=True)

        # Data backends
        self.lineage = PersistentLineage(self._dex_dir / "lineage.json")
        self.pipeline_runner = PipelineRunner(
            self.config,
            data_dir=self._dex_dir / "lakehouse",
            project_dir=self.project_dir,
            lineage=self.lineage,
        )
        self.run_history = PipelineRunHistory(self._dex_dir / "pipeline_runs.json")

        # ML backends (graceful degradation)
        self.tracker: Any = self._init_ml_tracker()
        self.feature_store: Any = self._init_ml_feature_store()
        self.model_registry = ModelRegistry(
            persist_path=str(self._dex_dir / "models" / "registry.json"),
        )
        self.serving_engine: Any = self._init_ml_serving()

        # AI backends (graceful degradation)
        self.llm: Any = None
        self.agents: dict[str, Any] = {}
        self._init_ai()

        logger.info(
            "DexEngine ready",
            project=self.config.project.name,
            config=str(self.config_path),
        )

    # -- pipeline helpers ------------------------------------------------

    def run_pipeline(self, name: str) -> PipelineResult:
        """Run a pipeline and record the result in history."""
        import time

        start = time.monotonic()
        result = self.pipeline_runner.run(name)
        duration_ms = (time.monotonic() - start) * 1000
        self.run_history.record(result, duration_ms)
        return result

    # -- warehouse helpers -----------------------------------------------

    def warehouse_layers(self) -> list[dict[str, Any]]:
        """List medallion layers and table counts from .dex/lakehouse/."""
        lakehouse = self._dex_dir / "lakehouse"
        layers: list[dict[str, Any]] = []
        for layer_name in ("bronze", "silver", "gold"):
            layer_path = lakehouse / layer_name
            table_count = len(list(layer_path.glob("*.parquet"))) if layer_path.exists() else 0
            layers.append({"name": layer_name, "table_count": table_count})
        return layers

    def warehouse_tables(self, layer: str) -> list[dict[str, Any]]:
        """List parquet tables in a specific medallion layer."""
        layer_path = self._dex_dir / "lakehouse" / layer
        if not layer_path.exists():
            return []
        tables: list[dict[str, Any]] = []
        for f in layer_path.glob("*.parquet"):
            try:
                tables.append({"name": f.stem, "path": str(f), "size_bytes": f.stat().st_size})
            except OSError:
                continue
        return tables

    # -- health ----------------------------------------------------------

    def health(self) -> dict[str, Any]:
        """Return component health summary."""
        return {
            "status": "healthy",
            "project": self.config.project.name,
            "components": {
                "pipeline_runner": self.pipeline_runner is not None,
                "lineage": self.lineage is not None,
                "tracker": self.tracker is not None,
                "feature_store": self.feature_store is not None,
                "model_registry": self.model_registry is not None,
                "serving_engine": self.serving_engine is not None,
                "llm": self.llm is not None,
                "agents": len(self.agents),
            },
        }

    # -- cleanup ---------------------------------------------------------

    def close(self) -> None:
        """Cleanup resources."""
        if hasattr(self, "feature_store") and self.feature_store and hasattr(self.feature_store, "close"):
            self.feature_store.close()
        logger.info("DexEngine shutdown")

    # -- private init helpers --------------------------------------------

    def _init_ml_tracker(self) -> Any:
        try:
            import dataenginex.ml.tracking.builtin  # noqa: F401
            from dataenginex.ml.tracking import tracker_registry

            tracker_cls = tracker_registry.get(self.config.ml.tracking.backend)
            return tracker_cls()
        except Exception:
            logger.warning("tracker init failed, ML tracking unavailable")
            return None

    def _init_ml_feature_store(self) -> Any:
        try:
            import dataenginex.ml.features.builtin  # noqa: F401
            from dataenginex.ml.features import feature_store_registry

            fs_cls = feature_store_registry.get(self.config.ml.features.backend)
            return fs_cls(**self.config.ml.features.options)
        except Exception:
            logger.warning("feature store init failed, ML features unavailable")
            return None

    def _init_ml_serving(self) -> Any:
        try:
            from typing import cast

            import dataenginex.ml.serving_engine.builtin  # noqa: F401
            from dataenginex.ml.serving_engine import serving_registry

            serving_cls: Any = cast(Any, serving_registry.get(self.config.ml.serving.engine))
            return serving_cls(
                model_registry=self.model_registry,
                model_dir=str(self._dex_dir / "models"),
            )
        except Exception:
            logger.warning("serving engine init failed, predictions unavailable")
            return None

    def _init_ai(self) -> None:
        """Initialize LLM provider and agents with graceful degradation."""
        try:
            from dataenginex.ml.llm import get_llm_provider

            self.llm = get_llm_provider(
                self.config.ai.llm.provider,
                model=self.config.ai.llm.model,
            )
        except Exception:
            self.llm = None
            logger.warning("LLM provider unavailable, agents disabled")

        if self.llm is None:
            return

        try:
            from typing import cast

            import dataenginex.ai.agents.builtin  # noqa: F401
            from dataenginex.ai.agents import agent_registry
            from dataenginex.ai.tools import tool_registry
            from dataenginex.ai.tools.builtin import register_builtin_tools

            register_builtin_tools()

            for name, agent_cfg in self.config.ai.agents.items():
                agent_llm = self.llm
                if agent_cfg.model:
                    try:
                        from dataenginex.ml.llm import get_llm_provider as _get

                        agent_llm = _get(self.config.ai.llm.provider, model=agent_cfg.model)
                    except Exception:
                        pass
                agent_cls: Any = cast(Any, agent_registry.get(agent_cfg.runtime))
                self.agents[name] = agent_cls(
                    llm=agent_llm,
                    system_prompt=agent_cfg.system_prompt,
                    tools=tool_registry,
                    max_iterations=agent_cfg.max_iterations,
                )
                logger.info("agent initialized", agent=name)
        except Exception:
            logger.warning("agent initialization failed")
```

- [ ] **Step 3: Sync dex-studio dependencies**

```bash
cd /home/jay/workspace/DataEngineX/dex-studio && uv sync
```

- [ ] **Step 4: Lint + typecheck**

```bash
cd /home/jay/workspace/DataEngineX/dex-studio && uv run poe lint && uv run poe typecheck
```

- [ ] **Step 5: Commit**

```bash
cd /home/jay/workspace/DataEngineX/dex-studio
git add src/dex_studio/engine.py pyproject.toml
git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" -m "feat: DexEngine — direct dataenginex library access replaces HTTP client"
```

---

## Task 6: App Initialization + CLI Refactor (dex-studio)

**Files:**
- Modify: `dex-studio/src/dex_studio/app.py`
- Modify: `dex-studio/src/dex_studio/cli.py`

- [ ] **Step 1: Rewrite app.py**

Replace `dex-studio/src/dex_studio/app.py` with:

```python
"""DEX Studio — NiceGUI application entry point.

Creates the NiceGUI app on top of the DEX FastAPI app (via ui.run_with),
registers all pages, and launches.
"""
from __future__ import annotations

import contextlib
import logging
import sys
from pathlib import Path

from nicegui import app, ui

from dex_studio.config import StudioConfig, load_config
from dex_studio.engine import DexEngine

_log = logging.getLogger(__name__)

__all__ = ["start"]


def _register_pages() -> None:
    """Import all page modules to register their routes."""
    import importlib

    from dex_studio.pages import project_hub  # noqa: F401

    _optional_imports = [
        "dex_studio.pages.data.dashboard",
        "dex_studio.pages.data.pipelines",
        "dex_studio.pages.data.sources",
        "dex_studio.pages.data.warehouse",
        "dex_studio.pages.data.quality",
        "dex_studio.pages.data.lineage",
        "dex_studio.pages.ml.dashboard",
        "dex_studio.pages.ml.experiments",
        "dex_studio.pages.ml.models",
        "dex_studio.pages.ml.predictions",
        "dex_studio.pages.ml.features",
        "dex_studio.pages.ml.drift",
        "dex_studio.pages.ai.dashboard",
        "dex_studio.pages.ai.agents",
        "dex_studio.pages.ai.tools",
        "dex_studio.pages.ai.collections",
        "dex_studio.pages.ai.retrieval",
        "dex_studio.pages.system.status",
        "dex_studio.pages.system.components",
        "dex_studio.pages.system.metrics",
        "dex_studio.pages.system.logs",
        "dex_studio.pages.system.traces",
        "dex_studio.pages.system.settings",
        "dex_studio.pages.system.connection",
    ]
    for mod in _optional_imports:
        with contextlib.suppress(ImportError):
            importlib.import_module(mod)


def start(
    config_path: Path | None = None,
    studio_config: StudioConfig | None = None,
) -> None:
    """Launch DEX Studio.

    Parameters
    ----------
    config_path:
        Path to a dex YAML config file. DexEngine loads and validates it.
    studio_config:
        UI-level preferences (theme, window size, etc.).
    """
    resolved = (config_path or Path("dex.yaml")).resolve()
    if not resolved.exists():
        sys.stderr.write(f"Config not found: {resolved}\n")
        sys.stderr.write("Usage: dex-studio <path-to-config.yaml>\n")
        sys.exit(1)

    engine = DexEngine(resolved)
    ui_cfg = studio_config or load_config()

    app.storage.general["engine"] = engine
    app.storage.general["config"] = ui_cfg

    # Create dex FastAPI app without lifespan — DexEngine owns backends
    from dataenginex.api.factory import create_app

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
    _register_pages()

    use_native = ui_cfg.native_mode
    if use_native:
        use_native = _check_native_support()

    ui.run_with(
        dex_api,
        title=f"DEX Studio — {engine.config.project.name}",
        storage_secret="dex-studio-secret",
    )


def _check_native_support() -> bool:
    """Return True if pywebview can find a usable GUI backend."""
    try:
        from webview.guilib import initialize

        initialize()
        return True  # noqa: TRY300
    except Exception:  # noqa: BLE001
        _log.warning(
            "pywebview cannot find GTK or QT — falling back to browser mode."
        )
        return False
```

- [ ] **Step 2: Rewrite cli.py**

Replace `dex-studio/src/dex_studio/cli.py` with:

```python
"""CLI entry point for DEX Studio.

Usage::

    dex-studio careerdex/careerdex.yaml     # local mode (default)
    dex-studio --remote http://dex:17000    # remote mode (future)
    dex-studio                               # looks for dex.yaml in CWD
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dex-studio",
        description="DEX Studio — local control plane for DataEngineX",
    )
    parser.add_argument(
        "config",
        nargs="?",
        type=Path,
        default=None,
        help="Path to a dex YAML config file (default: dex.yaml in CWD)",
    )
    parser.add_argument(
        "--remote",
        default=None,
        help="Connect to remote DEX engine (not yet implemented)",
    )
    parser.add_argument(
        "--theme",
        choices=["dark", "light"],
        default=None,
        help="UI theme (default: dark)",
    )
    parser.add_argument(
        "--no-native",
        action="store_true",
        help="Open in browser instead of a native window",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Print version and exit",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    """CLI entry point."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.version:
        from dex_studio import __version__

        print(f"dex-studio {__version__}")  # noqa: T201
        sys.exit(0)

    if args.remote:
        sys.stderr.write("Remote mode not yet implemented. Use a config path.\n")
        sys.exit(1)

    # Load UI preferences
    from dex_studio.config import StudioConfig, load_config

    ui_cfg = load_config()
    overrides: dict[str, object] = {}
    if args.theme:
        overrides["theme"] = args.theme
    if args.no_native:
        overrides["native_mode"] = False
    if overrides:
        from dataclasses import asdict

        merged = {**asdict(ui_cfg), **overrides}
        ui_cfg = StudioConfig(**merged)

    from dex_studio.app import start

    start(config_path=args.config, studio_config=ui_cfg)


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Lint + typecheck**

```bash
cd /home/jay/workspace/DataEngineX/dex-studio && uv run poe lint && uv run poe typecheck
```

- [ ] **Step 4: Commit**

```bash
cd /home/jay/workspace/DataEngineX/dex-studio
git add src/dex_studio/app.py src/dex_studio/cli.py
git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" -m "feat: app init via DexEngine + ui.run_with, CLI accepts config path"
```

---

## Task 7: Page Migration — All Pages

**Files:** All 24 page files under `dex-studio/src/dex_studio/pages/` plus `components/chat_message.py`

**Pattern for every page:**

Every page currently does:
```python
client: DexClient | None = app.storage.general.get("client")
```

Change to:
```python
from dex_studio.engine import DexEngine
engine: DexEngine | None = app.storage.general.get("engine")
```

Then replace `await client.method()` calls with direct engine access. Remove all `try/except DexAPIError` blocks.

### Data Pages

- [ ] **Step 1: Migrate data/sources.py**

Replace `client.list_sources()` dict access with `engine.config.data.sources`. Each source is a `SourceConfig` with `.type`, `.path`, `.connection` attributes.

- [ ] **Step 2: Migrate data/pipelines.py**

Replace `client.list_pipelines()` with `engine.config.data.pipelines`. Replace `client.run_pipeline(name)` with `await asyncio.to_thread(engine.run_pipeline, name)`. Add run history display using `engine.run_history.get_runs(name)`.

- [ ] **Step 3: Migrate data/warehouse.py**

Replace `client.warehouse_layers()` with `engine.warehouse_layers()`. Replace `client.warehouse_tables(layer)` with `engine.warehouse_tables(layer)`.

- [ ] **Step 4: Migrate data/lineage.py**

Replace `client.list_lineage()` with `engine.lineage.all_events`. Each event is a `LineageEvent` dataclass — use `.event_id`, `.source`, `.destination`, `.operation`, `.layer`, `.timestamp` directly. No field name guessing.

- [ ] **Step 5: Migrate data/quality.py**

Replace `client.data_quality_summary()` with direct quality data from engine config.

- [ ] **Step 6: Migrate data/dashboard.py**

Replace `client.list_pipelines()` / `client.list_sources()` / `client.data_quality_summary()` with direct engine config access.

### ML Pages

- [ ] **Step 7: Migrate ml/experiments.py (S3 fix)**

Replace `client.list_experiments()` with `engine.tracker.list_experiments()`. Show only `id` + `name` columns (drop status, created_at, run_count).

- [ ] **Step 8: Migrate ml/models.py (S2 fix)**

Replace `client.list_models()` with `engine.model_registry.list_models()` (returns `list[str]`). For each model name, call `engine.model_registry.list_versions(name)` for version count. For detail, call `engine.model_registry.get(name, version)` which returns `ModelArtifact`.

- [ ] **Step 9: Migrate ml/predictions.py**

Replace `client.predict()` with `await asyncio.to_thread(engine.serving_engine.predict, ...)`. Handle `engine.serving_engine is None` gracefully.

- [ ] **Step 10: Migrate ml/features.py (S6 fix)**

Replace `client.list_feature_groups()` with `engine.feature_store.list_feature_groups()` (returns `list[str]`). Simplify table to show group names only.

- [ ] **Step 11: Migrate ml/drift.py (S7 fix)**

Replace `client.check_drift()` with direct call to `DriftDetector`. Align to actual `DriftReport` fields. Severity values: `"none"`, `"moderate"`, `"severe"`.

- [ ] **Step 12: Migrate ml/dashboard.py**

Replace `client.list_experiments()` / `client.list_models()` with direct engine access.

### AI Pages

- [ ] **Step 13: Migrate ai/agents.py (S1 + S4 fix)**

Replace `client.agent_chat()` with `await asyncio.to_thread(engine.agents[name].run, msg)`. Fix S1: display `tool_calls` as integer count, not list. Fix S4: show `engine.config.ai.agents[name].system_prompt` snippet instead of description. Add guide message when LLM unavailable (503-equivalent):

```python
if name not in engine.agents:
    response_text = (
        "LLM provider unavailable.\n\nTo enable AI agents, start Ollama:\n"
        "  ollama serve\n  ollama pull qwen3:8b\n\nThen restart DEX Studio."
    )
```

- [ ] **Step 14: Fix components/chat_message.py (S1)**

Change `tool_calls` rendering from iterating a list to displaying an integer badge.

- [ ] **Step 15: Migrate ai/dashboard.py (S5 fix)**

Replace `client.list_agents()` with `engine.config.ai.agents` for config, `engine.agents` for availability. Derive status: key in `engine.agents` = available, else = unavailable.

- [ ] **Step 16: Migrate ai/tools.py**

Replace `client.list_tools()` with direct tool registry access.

### System Pages

- [ ] **Step 17: Migrate system pages (status, components, logs, traces, connection)**

Replace `client.health()` with `engine.health()`. Replace `client.components()` with `engine.health()["components"]`. System logs/traces are stubs — keep minimal. Connection page becomes a simple engine status display.

- [ ] **Step 18: Lint + typecheck**

```bash
cd /home/jay/workspace/DataEngineX/dex-studio && uv run poe lint && uv run poe typecheck
```

- [ ] **Step 19: Commit**

```bash
cd /home/jay/workspace/DataEngineX/dex-studio
git add src/dex_studio/pages/ src/dex_studio/components/chat_message.py
git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" -m "feat: migrate all 24 pages to DexEngine direct access, fix data-shape bugs S1-S7"
```

---

## Task 8: CareerDEX Example Project

**Note:** The `careerdex` repo already exists at `/home/jay/workspace/DataEngineX/careerdex/` with its own `pyproject.toml`, `src/`, `tests/`, etc. We add the config YAML and CSV data files to the existing repo.

**Files:**
- Create: `careerdex/careerdex.yaml` (project root)
- Create: `careerdex/data/jobs.csv`
- Create: `careerdex/data/candidates.csv`
- Create: `careerdex/data/skills.csv`
- Create: `careerdex/data/companies.csv`

- [ ] **Step 1: Create data directory in existing repo**

```bash
mkdir -p /home/jay/workspace/DataEngineX/careerdex/data
```

- [ ] **Step 2: Create jobs.csv (20 rows)**

Headers: `id,title,company_id,location,salary_min,salary_max,experience_years,required_skills,posted_date,status`

18 active + 2 expired. Salary ranges from 70k-200k. Experience 0-10 years.

- [ ] **Step 3: Create candidates.csv (15 rows)**

Headers: `id,name,email,location,experience_years,skills,desired_salary,status,applied_date`

13 active + 2 inactive.

- [ ] **Step 4: Create skills.csv (12 rows)**

Headers: `id,name,category,demand_score`

Categories: programming, data, cloud, soft_skills.

- [ ] **Step 5: Create companies.csv (8 rows)**

Headers: `id,name,industry,size_tier,location,founded_year`

Mix of startup, mid-market, enterprise.

- [ ] **Step 6: Create careerdex.yaml**

```yaml
project:
  name: careerdex
  version: "1.0.0"
  description: "AI-powered career intelligence platform"

data:
  engine: duckdb
  sources:
    raw_jobs:
      type: csv
      path: data/jobs.csv
    raw_candidates:
      type: csv
      path: data/candidates.csv
    raw_skills:
      type: csv
      path: data/skills.csv
    raw_companies:
      type: csv
      path: data/companies.csv

  pipelines:
    ingest_jobs:
      source: raw_jobs
      transforms:
        - type: filter
          condition: "status = 'active'"
        - type: deduplicate
          key: [id]
      quality:
        completeness: 0.90
        uniqueness: [id]
      target:
        layer: bronze

    clean_jobs:
      source: raw_jobs
      depends_on: [ingest_jobs]
      transforms:
        - type: filter
          condition: "salary_min > 0 AND experience_years >= 0"
        - type: deduplicate
          key: [id]
      quality:
        completeness: 0.95
        uniqueness: [id]
      target:
        layer: silver

    job_analytics:
      source: raw_jobs
      depends_on: [clean_jobs]
      transforms:
        - type: filter
          condition: "salary_min > 0"
      target:
        layer: gold

    ingest_candidates:
      source: raw_candidates
      transforms:
        - type: filter
          condition: "status = 'active'"
        - type: deduplicate
          key: [email]
      quality:
        completeness: 0.90
        uniqueness: [email]
      target:
        layer: bronze

    clean_candidates:
      source: raw_candidates
      depends_on: [ingest_candidates]
      transforms:
        - type: filter
          condition: "desired_salary > 0 AND experience_years >= 0"
        - type: deduplicate
          key: [email]
      quality:
        completeness: 0.95
        uniqueness: [email]
      target:
        layer: silver

ml:
  tracking:
    backend: builtin
  experiments:
    salary_predictor:
      model_type: sklearn
      target: salary_max
      features: [experience_years, desired_salary]
      params:
        n_estimators: 100
        max_depth: 5
  drift:
    monitor: [experience_years, desired_salary]
    method: psi
    threshold: 0.2

ai:
  llm:
    provider: ollama
    model: "${LLM_MODEL:-qwen3:8b}"
  retrieval:
    strategy: hybrid
    top_k: 10
    reranker: true
  vectorstore:
    backend: builtin
    embedding_model: all-MiniLM-L6-v2
  collections:
    career_docs:
      chunk_size: 512
      chunk_overlap: 50
  agents:
    career_advisor:
      system_prompt: "You are an expert career advisor. Help users with career planning, skill development, and job search strategies."
      tools: [query, pipeline_status]
      max_iterations: 10
    job_matcher:
      system_prompt: "You are a job matching specialist. Match candidates to jobs based on skills, experience, and preferences."
      tools: [query, pipeline_status]
      max_iterations: 8

server:
  host: "0.0.0.0"
  port: 17003
  auth:
    enabled: false

observability:
  metrics: true
  tracing: false
  log_level: INFO
```

- [ ] **Step 7: Validate config**

```bash
cd /home/jay/workspace/DataEngineX/dex && uv run dex validate /home/jay/workspace/DataEngineX/careerdex/careerdex.yaml
```

- [ ] **Step 8: Commit**

```bash
cd /home/jay/workspace/DataEngineX/careerdex
git add careerdex.yaml data/
git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" -m "feat: careerdex config + CSV data — full-stack DataEngineX demo"
```

---

## Task 9: End-to-End Smoke Test

- [ ] **Step 1: Run dex full test suite**

```bash
cd /home/jay/workspace/DataEngineX/dex && uv run poe check-all
```

- [ ] **Step 2: Run dex-studio lint + typecheck**

```bash
cd /home/jay/workspace/DataEngineX/dex-studio && uv run poe lint && uv run poe typecheck
```

- [ ] **Step 3: Test careerdex config validation**

```bash
cd /home/jay/workspace/DataEngineX/dex && uv run dex validate /home/jay/workspace/DataEngineX/careerdex/careerdex.yaml
```

- [ ] **Step 4: Launch dex-studio with careerdex**

```bash
cd /home/jay/workspace/DataEngineX/dex-studio && uv run dex-studio /home/jay/workspace/DataEngineX/careerdex/careerdex.yaml
```

Expected: Studio launches on port 7860 with "DEX Studio — careerdex" title.

- [ ] **Step 5: Verify data pages**

In browser at http://localhost:7860:
- `/data` — dashboard shows 5 pipelines, 4 sources
- `/data/sources` — shows raw_jobs, raw_candidates, raw_skills, raw_companies with correct types
- `/data/pipelines` — shows all 5 pipelines, click "Run" on ingest_jobs
- `/data/warehouse` — after running pipelines, shows tables in bronze/silver/gold layers
- `/data/lineage` — shows lineage events from pipeline runs

- [ ] **Step 6: Verify ML pages**

- `/ml/experiments` — shows experiment list (may be empty initially)
- `/ml/models` — shows model registry
- `/ml/features` — shows feature groups

- [ ] **Step 7: Verify AI pages**

- `/ai/agents` — shows career_advisor and job_matcher
- If Ollama not running: shows guide message about starting Ollama
- If Ollama running: chat works

- [ ] **Step 8: Verify API endpoints still work**

```bash
curl http://localhost:7860/api/v1/health
curl http://localhost:7860/api/v1/data/sources
curl http://localhost:7860/api/v1/pipelines/
```

Expected: JSON responses (same format as standalone dex server).
