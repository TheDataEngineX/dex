# Phase 0: Foundation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish the monorepo package structure, unified config system (`dex.yaml`), core interfaces (Base\* ABCs), backend registry pattern, exception hierarchy, and `dex validate` CLI command.

**Architecture:** The existing `dataenginex` 0.8.x library becomes the monorepo root. New modules (`config/`, `cli/`) are added alongside existing ones. Existing code is NOT deleted or refactored — Phase 0 adds the foundation layer that later phases build on. The `datadex` and `agentdex` code will be ported in Phases 1 and 3 respectively.

**Tech Stack:** Python 3.12+ · Pydantic 2.12+ · Click 8.3+ · Rich 14.3+ · DuckDB 1.5+ · structlog 25.5+ · PyYAML 6.0+ · pytest 9.1+

**Spec:** `docs/superpowers/specs/2026-03-21-dataenginex-v2-system-redesign.md`

---

## File Structure

### New Files to Create

| File | Responsibility |
|------|---------------|
| `src/dataenginex/config/__init__.py` | Public API for config module |
| `src/dataenginex/config/schema.py` | Pydantic models for every `dex.yaml` section |
| `src/dataenginex/config/loader.py` | Load YAML, resolve env vars, validate, layer configs |
| `src/dataenginex/config/defaults.py` | Built-in default values for all config sections |
| `src/dataenginex/core/interfaces.py` | All Base\* ABCs (BaseConnector, BaseTransform, BaseTracker, BaseRetriever, BaseFeatureStore, BaseOrchestrator, BaseServingEngine, BaseAgentRuntime, BaseLLMProvider, BaseVectorStore) |
| `src/dataenginex/core/registry.py` | Generic backend registry with decorator-based registration |
| `src/dataenginex/core/exceptions.py` | Unified exception hierarchy |
| `src/dataenginex/cli/__init__.py` | CLI package init |
| `src/dataenginex/cli/main.py` | Click group entry point (`dex` command) |
| `src/dataenginex/cli/validate.py` | `dex validate` subcommand |
| `tests/unit/test_config_schema.py` | Tests for Pydantic config models |
| `tests/unit/test_config_loader.py` | Tests for YAML loading, env var resolution, layering |
| `tests/unit/test_core_interfaces.py` | Tests proving ABCs enforce contracts |
| `tests/unit/test_core_registry.py` | Tests for backend registry pattern |
| `tests/unit/test_core_exceptions.py` | Tests for exception hierarchy |
| `tests/unit/test_cli_validate.py` | Tests for `dex validate` command |

### Files to Modify

| File | Change |
|------|--------|
| `pyproject.toml` | Add `click`, `rich`, `duckdb`, `croniter` to core deps. Add `[project.scripts] dex = ...`. Remove `loguru`. Update `requires-python` to `>=3.12`. Add mypy overrides for new modules. |
| `src/dataenginex/__init__.py` | No changes in Phase 0 (new modules accessed via subpackage imports) |

---

## Task 1: Update pyproject.toml — Core Dependencies + CLI Entry Point

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Update core dependencies and project metadata**

Add `click`, `rich`, `duckdb`, `croniter` to core deps. Change `requires-python` to `>=3.12`. Remove `loguru` (AD2: structlog only). Add CLI entry point.

```toml
# In [project] section:
requires-python = ">=3.12"

# In [project.dependencies] — ADD these:
#   "click>=8.3.1",
#   "rich>=14.3.3",
#   "duckdb>=1.5.0",
#   "croniter>=6.0.0",
# REMOVE:
#   "loguru>=0.7.3",

# Add new section:
[project.scripts]
dex = "dataenginex.cli.main:dex"
```

Changes to make in `pyproject.toml`:
1. Change `requires-python = ">=3.13"` → `requires-python = ">=3.12"`
2. Remove `"loguru>=0.7.3",` from `[project.dependencies]`
3. Add to `[project.dependencies]`: `"click>=8.3.1"`, `"rich>=14.3.3"`, `"duckdb>=1.5.0"`, `"croniter>=6.0.0"`
4. Add `[project.scripts]` section: `dex = "dataenginex.cli.main:dex"`
5. Change `[tool.ruff]` `target-version = "py313"` → `target-version = "py312"`
6. Change `[tool.mypy]` `python_version = "3.13"` → `python_version = "3.12"`
7. Add `"duckdb.*"` to the mypy ignore_missing_imports override
8. Remove `"loguru.*"` from mypy ignore list (no longer a dependency)

- [ ] **Step 2: Lock deps**

Run: `uv lock`
Expected: lockfile regenerated without errors

- [ ] **Step 3: Sync deps**

Run: `uv sync`
Expected: new deps installed, loguru removed

- [ ] **Step 4: Verify existing tests still pass**

Run: `uv run pytest tests/unit/ -x -q`
Expected: Tests may fail due to loguru removal — that's expected and will be fixed in Task 2.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml uv.lock
git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" -m "chore: update core deps — add click, rich, duckdb, croniter; remove loguru; target py3.12"
```

---

## Task 2: Migrate loguru → structlog (AD2)

**Files:**
- Modify: All source files that import `loguru`
- Modify: `tests/unit/test_logging.py`

**Context:** AD2 says structlog only. The codebase currently imports `loguru` in several files. These must all switch to `structlog`.

- [ ] **Step 1: Find all loguru imports**

Run: `grep -rn "from loguru" src/dataenginex/ --include="*.py"`

Replace every `from loguru import logger` with `import structlog` and `logger = structlog.get_logger()`.

Files known to use loguru (from exploration):
- `src/dataenginex/data/connectors.py`
- `src/dataenginex/plugins/registry.py`
- `src/dataenginex/ml/llm.py`
- `src/dataenginex/ml/registry.py`
- `src/dataenginex/ml/serving.py`
- `src/dataenginex/ml/drift.py`
- `src/dataenginex/ml/scheduler.py`
- `src/dataenginex/ml/training.py`
- `src/dataenginex/ml/vectorstore.py`
- `src/dataenginex/lakehouse/storage.py`
- `src/dataenginex/lakehouse/catalog.py`
- `src/dataenginex/warehouse/lineage.py`
- `src/dataenginex/warehouse/transforms.py`
- `src/dataenginex/secops/*.py`
- `src/dataenginex/data/profiler.py`
- `src/dataenginex/data/registry.py`

For each file, replace:
```python
# OLD
from loguru import logger

# NEW
import structlog

logger = structlog.get_logger()
```

Also update any `logger.debug(f"...")` string formatting to use structlog's key-value style:
```python
# OLD (loguru style)
logger.info(f"Loaded {count} items from {path}")

# NEW (structlog style)
logger.info("loaded items", count=count, path=str(path))
```

- [ ] **Step 2: Update test_logging.py if it tests loguru**

Check `tests/unit/test_logging.py` — if it references loguru, update to test structlog.

- [ ] **Step 3: Run lint + typecheck**

Run: `uv run ruff check src/dataenginex/ --fix && uv run mypy src/dataenginex/`
Expected: No loguru import errors. structlog types pass.

- [ ] **Step 4: Run full test suite**

Run: `uv run pytest tests/unit/ -x -q`
Expected: All existing tests pass with structlog.

- [ ] **Step 5: Commit**

```bash
# Stage all files that were modified in the loguru→structlog migration
# (list from Step 1 grep results — typically ~15 files in src/dataenginex/)
git add src/dataenginex/ tests/unit/test_logging.py
git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" -m "refactor: migrate loguru → structlog (AD2: single logging library)"
```

---

## Task 3: Exception Hierarchy

**Files:**
- Create: `src/dataenginex/core/exceptions.py`
- Create: `tests/unit/test_core_exceptions.py`

- [ ] **Step 1: Write tests for exception hierarchy**

```python
# tests/unit/test_core_exceptions.py
"""Tests for the unified exception hierarchy."""
from __future__ import annotations

import pytest

from dataenginex.core.exceptions import (
    BackendNotInstalledError,
    ConfigError,
    ConfigValidationError,
    DataEngineXError,
    PipelineError,
    RegistryError,
)


class TestExceptionHierarchy:
    """All custom exceptions inherit from DataEngineXError."""

    def test_base_is_exception(self) -> None:
        assert issubclass(DataEngineXError, Exception)

    def test_config_error_inherits_base(self) -> None:
        assert issubclass(ConfigError, DataEngineXError)

    def test_config_validation_inherits_config(self) -> None:
        assert issubclass(ConfigValidationError, ConfigError)

    def test_pipeline_error_inherits_base(self) -> None:
        assert issubclass(PipelineError, DataEngineXError)

    def test_registry_error_inherits_base(self) -> None:
        assert issubclass(RegistryError, DataEngineXError)

    def test_backend_not_installed_inherits_base(self) -> None:
        assert issubclass(BackendNotInstalledError, DataEngineXError)

    def test_backend_not_installed_message(self) -> None:
        err = BackendNotInstalledError(
            backend="qdrant",
            extra="vectors",
        )
        assert "qdrant" in str(err)
        assert "pip install dataenginex[vectors]" in str(err)

    def test_config_validation_error_fields(self) -> None:
        err = ConfigValidationError(
            field="ai.vectorstore.backend",
            message="unknown backend 'foo'",
        )
        assert "ai.vectorstore.backend" in str(err)
        assert "unknown backend 'foo'" in str(err)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_core_exceptions.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'dataenginex.core.exceptions'`

- [ ] **Step 3: Implement exceptions**

```python
# src/dataenginex/core/exceptions.py
"""Unified exception hierarchy for DataEngineX.

All framework exceptions inherit from ``DataEngineXError`` so callers
can catch broad or narrow as needed::

    try:
        dex.validate("dex.yaml")
    except ConfigValidationError:
        ...  # specific
    except DataEngineXError:
        ...  # catch-all
"""
from __future__ import annotations


class DataEngineXError(Exception):
    """Base exception for all DataEngineX errors."""


# --- Config ---


class ConfigError(DataEngineXError):
    """Error loading or processing configuration."""


class ConfigValidationError(ConfigError):
    """A specific config field failed validation."""

    def __init__(self, field: str, message: str) -> None:
        self.field = field
        self.message = message
        super().__init__(f"Config error at '{field}': {message}")


# --- Pipeline ---


class PipelineError(DataEngineXError):
    """Error during pipeline execution."""


class PipelineStepError(PipelineError):
    """A specific pipeline step failed."""

    def __init__(self, step: str, cause: str) -> None:
        self.step = step
        self.cause = cause
        super().__init__(f"Pipeline step '{step}' failed: {cause}")


# --- Registry ---


class RegistryError(DataEngineXError):
    """Error in backend registry operations."""


class BackendNotInstalledError(DataEngineXError):
    """An optional backend was requested but its extra is not installed."""

    def __init__(self, backend: str, extra: str) -> None:
        self.backend = backend
        self.extra = extra
        super().__init__(
            f"Backend '{backend}' requires: pip install dataenginex[{extra}]"
        )


# --- ML ---


class TrainingError(DataEngineXError):
    """Error during model training."""


class ServingError(DataEngineXError):
    """Error during model serving."""


# --- Agent ---


class AgentError(DataEngineXError):
    """Error in agent runtime."""


class LLMProviderError(AgentError):
    """Error communicating with LLM provider."""

    def __init__(self, provider: str, message: str) -> None:
        self.provider = provider
        super().__init__(f"LLM provider '{provider}': {message}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_core_exceptions.py -v`
Expected: All 8 tests PASS

- [ ] **Step 5: Run lint + typecheck on new file**

Run: `uv run ruff check src/dataenginex/core/exceptions.py && uv run mypy src/dataenginex/core/exceptions.py`
Expected: Clean

- [ ] **Step 6: Commit**

```bash
git add src/dataenginex/core/exceptions.py tests/unit/test_core_exceptions.py
git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" -m "feat: add unified exception hierarchy (DataEngineXError base)"
```

---

## Task 4: Backend Registry Pattern

**Files:**
- Create: `src/dataenginex/core/registry.py` (NEW — this is a different file from the existing `plugins/registry.py`)
- Create: `tests/unit/test_core_registry.py`

- [ ] **Step 1: Write tests for the registry pattern**

```python
# tests/unit/test_core_registry.py
"""Tests for the generic backend registry."""
from __future__ import annotations

from abc import ABC, abstractmethod

import pytest

from dataenginex.core.registry import BackendRegistry


class BaseWidget(ABC):
    """Dummy ABC for testing."""

    @abstractmethod
    def do_work(self) -> str: ...


class TestBackendRegistry:
    """BackendRegistry discovers, registers, and instantiates backends."""

    def setup_method(self) -> None:
        self.registry: BackendRegistry[BaseWidget] = BackendRegistry("widget")

    def test_register_and_get(self) -> None:
        class FooWidget(BaseWidget):
            def do_work(self) -> str:
                return "foo"

        self.registry.register("foo", FooWidget)
        cls = self.registry.get("foo")
        assert cls is FooWidget

    def test_get_unknown_raises(self) -> None:
        with pytest.raises(KeyError, match="widget.*unknown"):
            self.registry.get("unknown")

    def test_list_registered(self) -> None:
        class A(BaseWidget):
            def do_work(self) -> str:
                return "a"

        class B(BaseWidget):
            def do_work(self) -> str:
                return "b"

        self.registry.register("a", A)
        self.registry.register("b", B)
        assert sorted(self.registry.list()) == ["a", "b"]

    def test_register_duplicate_raises(self) -> None:
        class W(BaseWidget):
            def do_work(self) -> str:
                return "w"

        self.registry.register("w", W)
        with pytest.raises(ValueError, match="already registered"):
            self.registry.register("w", W)

    def test_register_decorator(self) -> None:
        @self.registry.decorator("bar")
        class BarWidget(BaseWidget):
            def do_work(self) -> str:
                return "bar"

        assert self.registry.get("bar") is BarWidget

    def test_default_backend(self) -> None:
        class DefaultWidget(BaseWidget):
            def do_work(self) -> str:
                return "default"

        self.registry.register("default", DefaultWidget, is_default=True)
        assert self.registry.get_default() is DefaultWidget

    def test_no_default_raises(self) -> None:
        with pytest.raises(ValueError, match="no default"):
            self.registry.get_default()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_core_registry.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement the registry**

```python
# src/dataenginex/core/registry.py
"""Generic backend registry pattern.

Every subsystem (connectors, trackers, retrievers, etc.) uses a
``BackendRegistry`` to discover and instantiate backend implementations.

Usage::

    from dataenginex.core.registry import BackendRegistry

    connector_registry: BackendRegistry[BaseConnector] = BackendRegistry("connector")

    @connector_registry.decorator("csv")
    class CsvConnector(BaseConnector):
        ...

    # Later:
    cls = connector_registry.get("csv")
    instance = cls(**kwargs)
"""
from __future__ import annotations

from typing import Generic, TypeVar

import structlog

logger = structlog.get_logger()

T = TypeVar("T")


class BackendRegistry(Generic[T]):
    """Type-safe registry for backend implementations.

    Parameters:
        domain: Human-readable name for error messages (e.g. "connector").
    """

    def __init__(self, domain: str) -> None:
        self._domain = domain
        self._backends: dict[str, type[T]] = {}
        self._default: str | None = None

    def register(
        self, name: str, cls: type[T], *, is_default: bool = False
    ) -> None:
        """Register a backend class under *name*.

        Raises:
            ValueError: If *name* is already registered.
        """
        if name in self._backends:
            msg = f"{self._domain} backend '{name}' already registered"
            raise ValueError(msg)
        self._backends[name] = cls
        if is_default:
            self._default = name
        logger.debug(
            "backend registered",
            domain=self._domain,
            name=name,
            default=is_default,
        )

    def decorator(self, name: str, *, is_default: bool = False):  # type: ignore[no-untyped-def]
        """Class decorator for registration.

        Usage::

            @registry.decorator("csv")
            class CsvConnector(BaseConnector):
                ...
        """

        def wrapper(cls: type[T]) -> type[T]:
            self.register(name, cls, is_default=is_default)
            return cls

        return wrapper

    def get(self, name: str) -> type[T]:
        """Return the backend class registered under *name*.

        Raises:
            KeyError: If *name* is not registered.
        """
        try:
            return self._backends[name]
        except KeyError:
            available = ", ".join(sorted(self._backends)) or "(none)"
            msg = f"{self._domain} backend '{name}' not found. Available: {available}"
            raise KeyError(msg) from None

    def get_default(self) -> type[T]:
        """Return the default backend class.

        Raises:
            ValueError: If no default has been set.
        """
        if self._default is None:
            msg = f"{self._domain} registry has no default backend"
            raise ValueError(msg)
        return self._backends[self._default]

    def list(self) -> list[str]:
        """Return all registered backend names."""
        return list(self._backends.keys())

    def __contains__(self, name: str) -> bool:
        return name in self._backends

    def __len__(self) -> int:
        return len(self._backends)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_core_registry.py -v`
Expected: All 7 tests PASS

- [ ] **Step 5: Lint + typecheck**

Run: `uv run ruff check src/dataenginex/core/registry.py && uv run mypy src/dataenginex/core/registry.py`
Expected: Clean

- [ ] **Step 6: Commit**

```bash
git add src/dataenginex/core/registry.py tests/unit/test_core_registry.py
git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" -m "feat: add generic BackendRegistry pattern for pluggable backends"
```

---

## Task 5: Core Interfaces (Base\* ABCs)

**Files:**
- Create: `src/dataenginex/core/interfaces.py`
- Create: `tests/unit/test_core_interfaces.py`

- [ ] **Step 1: Write tests for interface contracts**

```python
# tests/unit/test_core_interfaces.py
"""Tests proving Base* ABCs enforce their contracts.

Each ABC must be abstract — you cannot instantiate it directly.
"""
from __future__ import annotations

from typing import Any

import pytest

from dataenginex.core.interfaces import (
    BaseAgentRuntime,
    BaseConnector,
    BaseFeatureStore,
    BaseLLMProvider,
    BaseOrchestrator,
    BaseRetriever,
    BaseServingEngine,
    BaseTracker,
    BaseTransform,
    BaseVectorStore,
)


ALL_ABCS = [
    BaseConnector,
    BaseTransform,
    BaseTracker,
    BaseRetriever,
    BaseFeatureStore,
    BaseOrchestrator,
    BaseServingEngine,
    BaseAgentRuntime,
    BaseLLMProvider,
    BaseVectorStore,
]


class TestABCsCannotBeInstantiated:
    @pytest.mark.parametrize("abc_cls", ALL_ABCS, ids=lambda c: c.__name__)
    def test_cannot_instantiate(self, abc_cls: type) -> None:
        with pytest.raises(TypeError, match="abstract"):
            abc_cls()  # type: ignore[abstract]


class TestBaseConnectorContract:
    """A concrete connector must implement all abstract methods."""

    def test_minimal_implementation(self) -> None:
        class DummyConnector(BaseConnector):
            def connect(self) -> None:
                pass

            def disconnect(self) -> None:
                pass

            def read(self, **kwargs: Any) -> Any:
                return []

            def write(self, data: Any, **kwargs: Any) -> None:
                pass

            def health_check(self) -> bool:
                return True

        c = DummyConnector()
        assert c.health_check() is True


class TestBaseTransformContract:
    def test_minimal_implementation(self) -> None:
        class DummyTransform(BaseTransform):
            @property
            def name(self) -> str:
                return "dummy"

            def apply(self, data: Any) -> Any:
                return data

        t = DummyTransform()
        assert t.name == "dummy"
        assert t.apply(42) == 42


class TestBaseTrackerContract:
    def test_minimal_implementation(self) -> None:
        class DummyTracker(BaseTracker):
            def create_experiment(self, name: str) -> str:
                return "exp-1"

            def log_params(self, run_id: str, params: dict[str, Any]) -> None:
                pass

            def log_metrics(
                self, run_id: str, metrics: dict[str, float], step: int | None = None
            ) -> None:
                pass

            def start_run(self, experiment_id: str, run_name: str | None = None) -> str:
                return "run-1"

            def end_run(self, run_id: str, status: str = "FINISHED") -> None:
                pass

            def list_runs(self, experiment_id: str) -> list[dict[str, Any]]:
                return []

        t = DummyTracker()
        assert t.create_experiment("test") == "exp-1"


class TestBaseRetrieverContract:
    def test_minimal_implementation(self) -> None:
        class DummyRetriever(BaseRetriever):
            def retrieve(
                self, query: str, top_k: int = 10, **kwargs: Any
            ) -> list[dict[str, Any]]:
                return []

        r = DummyRetriever()
        assert r.retrieve("test") == []


class TestBaseLLMProviderContract:
    def test_minimal_implementation(self) -> None:
        class DummyLLM(BaseLLMProvider):
            async def generate(
                self, prompt: str, **kwargs: Any
            ) -> str:
                return "hello"

        llm = DummyLLM()
        # Just verify it instantiates (async method tested elsewhere)
        assert isinstance(llm, BaseLLMProvider)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_core_interfaces.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement all interfaces**

```python
# src/dataenginex/core/interfaces.py
"""Base interfaces (ABCs) for all pluggable subsystems.

Every backend (built-in or extra) implements the corresponding ABC.
This ensures interchangeability and enables conformance testing.

The interfaces defined here are:
- BaseConnector — data source/sink
- BaseTransform — data transformation step
- BaseTracker — experiment tracking
- BaseRetriever — document/vector retrieval
- BaseFeatureStore — feature storage and serving
- BaseOrchestrator — pipeline orchestration/scheduling
- BaseServingEngine — model serving
- BaseAgentRuntime — agent execution loop
- BaseLLMProvider — LLM API wrapper
- BaseVectorStore — vector CRUD operations
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


# --- Data Layer ---


class BaseConnector(ABC):
    """Interface for data source/sink connectors."""

    @abstractmethod
    def connect(self) -> None:
        """Establish connection to the data source."""

    @abstractmethod
    def disconnect(self) -> None:
        """Close connection."""

    @abstractmethod
    def read(self, **kwargs: Any) -> Any:
        """Read data from the source."""

    @abstractmethod
    def write(self, data: Any, **kwargs: Any) -> None:
        """Write data to the sink."""

    @abstractmethod
    def health_check(self) -> bool:
        """Return True if the connection is healthy."""


class BaseTransform(ABC):
    """Interface for data transformation steps."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable transform name."""

    @abstractmethod
    def apply(self, data: Any) -> Any:
        """Apply transformation and return result."""


# --- ML Layer ---


class BaseTracker(ABC):
    """Interface for experiment tracking backends."""

    @abstractmethod
    def create_experiment(self, name: str) -> str:
        """Create an experiment, return its ID."""

    @abstractmethod
    def start_run(
        self, experiment_id: str, run_name: str | None = None
    ) -> str:
        """Start a run within an experiment, return run ID."""

    @abstractmethod
    def end_run(self, run_id: str, status: str = "FINISHED") -> None:
        """End a run with given status."""

    @abstractmethod
    def log_params(self, run_id: str, params: dict[str, Any]) -> None:
        """Log parameters for a run."""

    @abstractmethod
    def log_metrics(
        self,
        run_id: str,
        metrics: dict[str, float],
        step: int | None = None,
    ) -> None:
        """Log metrics for a run at optional step."""

    @abstractmethod
    def list_runs(self, experiment_id: str) -> list[dict[str, Any]]:
        """List all runs for an experiment."""


class BaseFeatureStore(ABC):
    """Interface for feature storage and serving."""

    @abstractmethod
    def save_features(
        self, feature_group: str, data: Any, entity_key: str
    ) -> None:
        """Persist features for a feature group."""

    @abstractmethod
    def get_features(
        self, feature_group: str, entity_ids: list[str]
    ) -> Any:
        """Retrieve features by entity IDs."""

    @abstractmethod
    def list_feature_groups(self) -> list[str]:
        """List all registered feature groups."""


class BaseServingEngine(ABC):
    """Interface for model serving backends."""

    @abstractmethod
    def load_model(self, model_name: str, version: str | None = None) -> None:
        """Load a model for serving."""

    @abstractmethod
    def predict(self, model_name: str, data: Any) -> Any:
        """Run inference on loaded model."""

    @abstractmethod
    def list_models(self) -> list[str]:
        """List currently loaded models."""


# --- Retrieval Layer ---


class BaseRetriever(ABC):
    """Interface for document/vector retrieval."""

    @abstractmethod
    def retrieve(
        self, query: str, top_k: int = 10, **kwargs: Any
    ) -> list[dict[str, Any]]:
        """Retrieve top_k relevant documents for query."""


class BaseVectorStore(ABC):
    """Interface for vector CRUD operations."""

    @abstractmethod
    def add(
        self,
        ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadata: list[dict[str, Any]] | None = None,
    ) -> None:
        """Add vectors with documents and optional metadata."""

    @abstractmethod
    def search(
        self,
        query_embedding: list[float],
        top_k: int = 10,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """Search for nearest neighbors."""

    @abstractmethod
    def delete(self, ids: list[str]) -> None:
        """Delete vectors by ID."""

    @abstractmethod
    def count(self) -> int:
        """Return number of stored vectors."""


# --- Orchestration Layer ---


class BaseOrchestrator(ABC):
    """Interface for pipeline orchestration/scheduling."""

    @abstractmethod
    def schedule(self, pipeline_name: str, cron: str) -> None:
        """Schedule a pipeline with a cron expression."""

    @abstractmethod
    def trigger(self, pipeline_name: str) -> str:
        """Trigger an immediate run, return run ID."""

    @abstractmethod
    def status(self, run_id: str) -> dict[str, Any]:
        """Get status of a run."""

    @abstractmethod
    def cancel(self, run_id: str) -> None:
        """Cancel a running pipeline."""


# --- Agent Layer ---


class BaseAgentRuntime(ABC):
    """Interface for agent execution runtimes."""

    @abstractmethod
    async def run(
        self, message: str, **kwargs: Any
    ) -> str:
        """Execute agent with message and return response."""

    @abstractmethod
    async def step(
        self, message: str, **kwargs: Any
    ) -> dict[str, Any]:
        """Execute one reasoning step, return step details."""


class BaseLLMProvider(ABC):
    """Interface for LLM API wrappers."""

    @abstractmethod
    async def generate(self, prompt: str, **kwargs: Any) -> str:
        """Generate text from prompt."""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_core_interfaces.py -v`
Expected: All tests PASS

- [ ] **Step 5: Lint + typecheck**

Run: `uv run ruff check src/dataenginex/core/interfaces.py && uv run mypy src/dataenginex/core/interfaces.py`
Expected: Clean

- [ ] **Step 6: Commit**

```bash
git add src/dataenginex/core/interfaces.py tests/unit/test_core_interfaces.py
git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" -m "feat: add Base* ABCs for all pluggable subsystems (10 interfaces)"
```

---

## Task 6: Config Schema — Pydantic Models for dex.yaml

**Files:**
- Create: `src/dataenginex/config/__init__.py`
- Create: `src/dataenginex/config/schema.py`
- Create: `src/dataenginex/config/defaults.py`
- Create: `tests/unit/test_config_schema.py`

- [ ] **Step 1: Write tests for config schema**

```python
# tests/unit/test_config_schema.py
"""Tests for dex.yaml Pydantic schema models."""
from __future__ import annotations

import pytest

from dataenginex.config.schema import (
    AgentConfig,
    AiConfig,
    DataConfig,
    DexConfig,
    MlConfig,
    ObservabilityConfig,
    PipelineConfig,
    ProjectConfig,
    RetrievalConfig,
    SecopsConfig,
    ServerConfig,
    SourceConfig,
)


class TestProjectConfig:
    def test_minimal(self) -> None:
        cfg = ProjectConfig(name="test-project")
        assert cfg.name == "test-project"
        assert cfg.version == "0.1.0"

    def test_with_version(self) -> None:
        cfg = ProjectConfig(name="demo", version="1.0.0")
        assert cfg.version == "1.0.0"


class TestSourceConfig:
    def test_csv_source(self) -> None:
        cfg = SourceConfig(type="csv", path="data/input.csv")
        assert cfg.type == "csv"

    def test_duckdb_source(self) -> None:
        cfg = SourceConfig(type="duckdb", query="SELECT * FROM users")
        assert cfg.type == "duckdb"


class TestPipelineConfig:
    def test_minimal_pipeline(self) -> None:
        cfg = PipelineConfig(
            source="raw_data",
            transforms=[{"type": "filter", "condition": "age > 18"}],
            destination="silver_users",
        )
        assert cfg.source == "raw_data"
        assert len(cfg.transforms) == 1


class TestDataConfig:
    def test_with_sources_and_pipelines(self) -> None:
        cfg = DataConfig(
            sources={
                "users": SourceConfig(type="csv", path="data/users.csv"),
            },
            pipelines={
                "clean_users": PipelineConfig(
                    source="users",
                    transforms=[],
                    destination="silver_users",
                ),
            },
        )
        assert "users" in cfg.sources
        assert "clean_users" in cfg.pipelines

    def test_default_engine_is_duckdb(self) -> None:
        cfg = DataConfig()
        assert cfg.engine == "duckdb"


class TestMlConfig:
    def test_defaults(self) -> None:
        cfg = MlConfig()
        assert cfg.tracker == "builtin"


class TestAiConfig:
    def test_defaults(self) -> None:
        cfg = AiConfig()
        assert cfg.llm.provider == "ollama"


class TestDexConfig:
    def test_minimal_valid_config(self) -> None:
        cfg = DexConfig(project=ProjectConfig(name="minimal"))
        assert cfg.project.name == "minimal"
        assert cfg.data.engine == "duckdb"
        assert cfg.ml.tracker == "builtin"

    def test_all_sections_optional_except_project(self) -> None:
        with pytest.raises(Exception):
            DexConfig()  # type: ignore[call-arg]

    def test_server_defaults(self) -> None:
        cfg = DexConfig(project=ProjectConfig(name="srv"))
        assert cfg.server.host == "0.0.0.0"
        assert cfg.server.port == 17000
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_config_schema.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Create config package init**

```python
# src/dataenginex/config/__init__.py
"""Unified config system for dex.yaml.

Public API::

    from dataenginex.config import DexConfig, load_config, validate_config
"""
from __future__ import annotations
```

- [ ] **Step 4: Implement defaults**

```python
# src/dataenginex/config/defaults.py
"""Built-in default values for all config sections.

These are applied when a section is omitted from dex.yaml.
"""
from __future__ import annotations

# Data
DEFAULT_ENGINE = "duckdb"

# ML
DEFAULT_TRACKER = "builtin"
DEFAULT_FEATURE_STORE = "builtin"
DEFAULT_SERVING_ENGINE = "builtin"
DEFAULT_DRIFT_METHOD = "psi"
DEFAULT_DRIFT_THRESHOLD = 0.2

# AI
DEFAULT_LLM_PROVIDER = "ollama"
DEFAULT_LLM_MODEL = "qwen3:8b"
DEFAULT_RETRIEVAL_STRATEGY = "hybrid"
DEFAULT_VECTORSTORE_BACKEND = "builtin"
DEFAULT_AGENT_RUNTIME = "builtin"

# Server
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 17000

# Observability
DEFAULT_LOG_LEVEL = "INFO"
```

- [ ] **Step 5: Implement schema models**

```python
# src/dataenginex/config/schema.py
"""Pydantic models for dex.yaml — the unified config schema.

Every section is a Pydantic BaseModel with defaults so that
only ``project.name`` is required. Progressive disclosure:
add sections as you need them.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from dataenginex.config.defaults import (
    DEFAULT_AGENT_RUNTIME,
    DEFAULT_DRIFT_METHOD,
    DEFAULT_DRIFT_THRESHOLD,
    DEFAULT_ENGINE,
    DEFAULT_FEATURE_STORE,
    DEFAULT_HOST,
    DEFAULT_LLM_MODEL,
    DEFAULT_LLM_PROVIDER,
    DEFAULT_LOG_LEVEL,
    DEFAULT_PORT,
    DEFAULT_RETRIEVAL_STRATEGY,
    DEFAULT_SERVING_ENGINE,
    DEFAULT_TRACKER,
    DEFAULT_VECTORSTORE_BACKEND,
)


# --- Project ---


class ProjectConfig(BaseModel):
    """Top-level project metadata."""

    name: str
    version: str = "0.1.0"
    description: str = ""


# --- Data Layer ---


class SourceConfig(BaseModel):
    """A named data source."""

    type: str  # csv, duckdb, postgres, s3, rest, kafka, etc.
    path: str | None = None
    query: str | None = None
    url: str | None = None
    options: dict[str, Any] = Field(default_factory=dict)


class TransformStepConfig(BaseModel):
    """A single transform step in a pipeline."""

    type: str  # filter, derive, cast, deduplicate, sql, etc.
    condition: str | None = None
    expression: str | None = None
    columns: list[str] | None = None
    sql: str | None = None
    options: dict[str, Any] = Field(default_factory=dict)


class QualityCheckConfig(BaseModel):
    """Quality checks applied after transforms."""

    completeness: float | None = None  # min non-null ratio (0.0-1.0)
    uniqueness: list[str] | None = None  # columns that must be unique
    freshness_hours: float | None = None
    custom_sql: str | None = None


class PipelineConfig(BaseModel):
    """A named data pipeline."""

    source: str  # reference to a named source
    transforms: list[TransformStepConfig] = Field(default_factory=list)
    quality: QualityCheckConfig | None = None
    destination: str | None = None
    depends_on: list[str] = Field(default_factory=list)
    schedule: str | None = None  # cron expression


class DataConfig(BaseModel):
    """Data layer configuration."""

    engine: str = DEFAULT_ENGINE
    sources: dict[str, SourceConfig] = Field(default_factory=dict)
    pipelines: dict[str, PipelineConfig] = Field(default_factory=dict)


# --- ML Layer ---


class TrackerConfig(BaseModel):
    """Experiment tracker backend config."""

    backend: str = DEFAULT_TRACKER
    uri: str | None = None  # for mlflow


class FeatureStoreConfig(BaseModel):
    """Feature store backend config."""

    backend: str = DEFAULT_FEATURE_STORE
    options: dict[str, Any] = Field(default_factory=dict)


class DriftConfig(BaseModel):
    """Drift detection configuration."""

    monitor: list[str] = Field(default_factory=list)
    method: str = DEFAULT_DRIFT_METHOD
    threshold: float = DEFAULT_DRIFT_THRESHOLD


class ServingConfig(BaseModel):
    """Model serving config."""

    engine: str = DEFAULT_SERVING_ENGINE
    endpoints: list[dict[str, Any]] = Field(default_factory=list)


class ExperimentConfig(BaseModel):
    """An ML experiment definition."""

    model_type: str = "sklearn"
    target: str = ""
    features: list[str] = Field(default_factory=list)
    params: dict[str, Any] = Field(default_factory=dict)


class MlConfig(BaseModel):
    """ML layer configuration."""

    tracker: str = DEFAULT_TRACKER
    tracking: TrackerConfig = Field(default_factory=TrackerConfig)
    features: FeatureStoreConfig = Field(default_factory=FeatureStoreConfig)
    experiments: dict[str, ExperimentConfig] = Field(default_factory=dict)
    serving: ServingConfig = Field(default_factory=ServingConfig)
    drift: DriftConfig = Field(default_factory=DriftConfig)


# --- AI Layer ---


class LLMConfig(BaseModel):
    """LLM provider configuration."""

    provider: str = DEFAULT_LLM_PROVIDER
    model: str = DEFAULT_LLM_MODEL
    fallback: str | None = None
    options: dict[str, Any] = Field(default_factory=dict)


class RetrievalConfig(BaseModel):
    """Retrieval strategy configuration."""

    strategy: str = DEFAULT_RETRIEVAL_STRATEGY
    top_k: int = 10
    reranker: bool = True
    options: dict[str, Any] = Field(default_factory=dict)


class VectorStoreConfig(BaseModel):
    """Vector store backend configuration."""

    backend: str = DEFAULT_VECTORSTORE_BACKEND
    embedding_model: str = "all-MiniLM-L6-v2"
    options: dict[str, Any] = Field(default_factory=dict)


class CollectionConfig(BaseModel):
    """A named vector collection."""

    source: str | None = None  # pipeline that populates it
    embedding_model: str | None = None  # override default
    chunk_size: int = 512
    chunk_overlap: int = 50


class AgentConfig(BaseModel):
    """An AI agent definition."""

    runtime: str = DEFAULT_AGENT_RUNTIME
    system_prompt: str = ""
    tools: list[str] = Field(default_factory=list)
    model: str | None = None  # override default LLM
    max_iterations: int = 10
    memory: Literal["short_term", "episodic", "long_term"] = "short_term"


class AiConfig(BaseModel):
    """AI layer configuration."""

    llm: LLMConfig = Field(default_factory=LLMConfig)
    retrieval: RetrievalConfig = Field(default_factory=RetrievalConfig)
    vectorstore: VectorStoreConfig = Field(default_factory=VectorStoreConfig)
    collections: dict[str, CollectionConfig] = Field(default_factory=dict)
    agents: dict[str, AgentConfig] = Field(default_factory=dict)


# --- SecOps ---


class PiiConfig(BaseModel):
    """PII detection configuration."""

    scan: bool = False
    patterns: list[str] = Field(
        default_factory=lambda: ["email", "ssn", "phone", "credit_card"]
    )
    action: Literal["warn", "mask", "block"] = "warn"


class AuditConfig(BaseModel):
    """Audit logging configuration."""

    enabled: bool = False
    destination: str = "file"  # file, database


class SecopsConfig(BaseModel):
    """Security operations configuration."""

    pii: PiiConfig = Field(default_factory=PiiConfig)
    audit: AuditConfig = Field(default_factory=AuditConfig)


# --- Server ---


class AuthConfig(BaseModel):
    """Server authentication configuration."""

    enabled: bool = False
    secret_key: str | None = None
    algorithm: str = "HS256"


class ServerConfig(BaseModel):
    """API server configuration."""

    host: str = DEFAULT_HOST
    port: int = DEFAULT_PORT
    auth: AuthConfig = Field(default_factory=AuthConfig)
    cors_origins: list[str] = Field(default_factory=lambda: ["*"])


# --- Observability ---


class ObservabilityConfig(BaseModel):
    """Observability configuration."""

    metrics: bool = True
    tracing: bool = False
    log_level: str = DEFAULT_LOG_LEVEL


# --- Root Config ---


class DexConfig(BaseModel):
    """Root configuration model — one ``dex.yaml`` defines everything.

    Only ``project`` is required. All other sections have sensible defaults.
    """

    project: ProjectConfig
    data: DataConfig = Field(default_factory=DataConfig)
    ml: MlConfig = Field(default_factory=MlConfig)
    ai: AiConfig = Field(default_factory=AiConfig)
    secops: SecopsConfig = Field(default_factory=SecopsConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)
    observability: ObservabilityConfig = Field(default_factory=ObservabilityConfig)
```

- [ ] **Step 6: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_config_schema.py -v`
Expected: All tests PASS

- [ ] **Step 7: Lint + typecheck**

Run: `uv run ruff check src/dataenginex/config/ && uv run mypy src/dataenginex/config/`
Expected: Clean

- [ ] **Step 8: Commit**

```bash
git add src/dataenginex/config/ tests/unit/test_config_schema.py
git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" -m "feat: add dex.yaml Pydantic config schema (all sections with defaults)"
```

---

## Task 7: Config Loader — YAML + Env Var Resolution + Layering

**Files:**
- Create: `src/dataenginex/config/loader.py`
- Create: `tests/unit/test_config_loader.py`

- [ ] **Step 1: Write tests for config loading**

```python
# tests/unit/test_config_loader.py
"""Tests for YAML config loading, env var resolution, and layering."""
from __future__ import annotations

import os
from pathlib import Path
from textwrap import dedent

import pytest

from dataenginex.config.loader import load_config, resolve_env_vars, validate_config
from dataenginex.config.schema import DexConfig
from dataenginex.core.exceptions import ConfigError, ConfigValidationError


class TestResolveEnvVars:
    def test_simple_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DB_HOST", "localhost")
        result = resolve_env_vars("host: ${DB_HOST}")
        assert result == "host: localhost"

    def test_var_with_default(self) -> None:
        # VAR not set — should use default
        result = resolve_env_vars("port: ${UNSET_PORT:-5432}")
        assert result == "port: 5432"

    def test_var_with_default_when_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MY_PORT", "9999")
        result = resolve_env_vars("port: ${MY_PORT:-5432}")
        assert result == "port: 9999"

    def test_multiple_vars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HOST", "db.local")
        monkeypatch.setenv("PORT", "3306")
        result = resolve_env_vars("url: ${HOST}:${PORT}")
        assert result == "url: db.local:3306"

    def test_unset_var_no_default_raises(self) -> None:
        with pytest.raises(ConfigError, match="NONEXISTENT_VAR"):
            resolve_env_vars("val: ${NONEXISTENT_VAR}")


class TestLoadConfig:
    def test_load_minimal_yaml(self, tmp_path: Path) -> None:
        yaml_content = dedent("""\
            project:
              name: test-project
        """)
        config_file = tmp_path / "dex.yaml"
        config_file.write_text(yaml_content)

        cfg = load_config(config_file)
        assert isinstance(cfg, DexConfig)
        assert cfg.project.name == "test-project"

    def test_load_with_env_vars(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("PROJECT_NAME", "env-project")
        yaml_content = dedent("""\
            project:
              name: ${PROJECT_NAME}
        """)
        config_file = tmp_path / "dex.yaml"
        config_file.write_text(yaml_content)

        cfg = load_config(config_file)
        assert cfg.project.name == "env-project"

    def test_load_nonexistent_file_raises(self) -> None:
        with pytest.raises(ConfigError, match="not found"):
            load_config(Path("/nonexistent/dex.yaml"))

    def test_load_invalid_yaml_raises(self, tmp_path: Path) -> None:
        config_file = tmp_path / "dex.yaml"
        config_file.write_text(": : : invalid yaml {{{")

        with pytest.raises(ConfigError, match="parse"):
            load_config(config_file)

    def test_load_with_overlay(self, tmp_path: Path) -> None:
        base = dedent("""\
            project:
              name: my-app
            server:
              port: 17000
        """)
        overlay = dedent("""\
            server:
              port: 8080
        """)
        (tmp_path / "dex.yaml").write_text(base)
        (tmp_path / "dex.prod.yaml").write_text(overlay)

        cfg = load_config(
            tmp_path / "dex.yaml",
            overlay=tmp_path / "dex.prod.yaml",
        )
        assert cfg.project.name == "my-app"
        assert cfg.server.port == 8080


class TestValidateConfig:
    def test_valid_config_returns_none(self) -> None:
        cfg = DexConfig(
            project={"name": "valid"},  # type: ignore[arg-type]
        )
        errors = validate_config(cfg)
        assert errors == []

    def test_pipeline_references_missing_source(self) -> None:
        cfg = DexConfig(
            project={"name": "bad-ref"},  # type: ignore[arg-type]
            data={  # type: ignore[arg-type]
                "pipelines": {
                    "clean": {
                        "source": "nonexistent_source",
                        "transforms": [],
                    }
                }
            },
        )
        errors = validate_config(cfg)
        assert any("nonexistent_source" in e for e in errors)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_config_loader.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement the config loader**

```python
# src/dataenginex/config/loader.py
"""Load, resolve, validate, and layer dex.yaml configurations.

Usage::

    from dataenginex.config.loader import load_config

    cfg = load_config(Path("dex.yaml"))
    cfg = load_config(Path("dex.yaml"), overlay=Path("dex.prod.yaml"))
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import structlog
import yaml
from pydantic import ValidationError

from dataenginex.config.schema import DexConfig
from dataenginex.core.exceptions import ConfigError, ConfigValidationError

logger = structlog.get_logger()

# Matches ${VAR} and ${VAR:-default}
_ENV_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-(.*?))?\}")


def resolve_env_vars(text: str) -> str:
    """Replace ``${VAR}`` and ``${VAR:-default}`` in *text*.

    Raises:
        ConfigError: If a variable has no value and no default.
    """

    def _replace(match: re.Match[str]) -> str:
        var_name = match.group(1)
        default = match.group(2)
        value = os.environ.get(var_name)
        if value is not None:
            return value
        if default is not None:
            return default
        msg = (
            f"Environment variable '{var_name}' is not set and has no default. "
            f"Use ${{{{var_name}}:-default}} to provide a fallback."
        )
        raise ConfigError(msg)

    return _ENV_PATTERN.sub(_replace, text)


def _deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge *overlay* into *base*. Overlay values win."""
    merged = base.copy()
    for key, value in overlay.items():
        if (
            key in merged
            and isinstance(merged[key], dict)
            and isinstance(value, dict)
        ):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_config(
    path: Path,
    *,
    overlay: Path | None = None,
) -> DexConfig:
    """Load a ``dex.yaml`` and return a validated ``DexConfig``.

    Parameters:
        path: Path to the base config file.
        overlay: Optional overlay file (e.g. ``dex.prod.yaml``).

    Raises:
        ConfigError: If the file is missing or cannot be parsed.
    """
    if not path.exists():
        msg = f"Config file not found: {path}"
        raise ConfigError(msg)

    raw_text = path.read_text(encoding="utf-8")

    try:
        resolved_text = resolve_env_vars(raw_text)
    except ConfigError:
        raise
    except Exception as exc:
        msg = f"Failed to resolve env vars in {path}: {exc}"
        raise ConfigError(msg) from exc

    try:
        data = yaml.safe_load(resolved_text)
    except yaml.YAMLError as exc:
        msg = f"Failed to parse YAML in {path}: {exc}"
        raise ConfigError(msg) from exc

    if not isinstance(data, dict):
        msg = f"Config file {path} must be a YAML mapping, got {type(data).__name__}"
        raise ConfigError(msg)

    # Apply overlay
    if overlay is not None:
        if not overlay.exists():
            msg = f"Overlay config file not found: {overlay}"
            raise ConfigError(msg)
        overlay_text = overlay.read_text(encoding="utf-8")
        overlay_resolved = resolve_env_vars(overlay_text)
        overlay_data = yaml.safe_load(overlay_resolved)
        if isinstance(overlay_data, dict):
            data = _deep_merge(data, overlay_data)

    # Validate with Pydantic
    try:
        config = DexConfig.model_validate(data)
    except ValidationError as exc:
        msg = f"Config validation failed: {exc}"
        raise ConfigError(msg) from exc

    logger.info("config loaded", path=str(path), project=config.project.name)
    return config


def validate_config(config: DexConfig) -> list[str]:
    """Run cross-reference validation on a loaded config.

    Returns a list of error messages (empty = valid).
    Checks:
    - Pipeline sources reference defined sources
    - Pipeline depends_on references defined pipelines
    - Agent tools reference known tool names (deferred to Phase 3)
    """
    errors: list[str] = []

    source_names = set(config.data.sources.keys())
    pipeline_names = set(config.data.pipelines.keys())

    for pipe_name, pipe_cfg in config.data.pipelines.items():
        if pipe_cfg.source and pipe_cfg.source not in source_names:
            errors.append(
                f"Pipeline '{pipe_name}' references undefined source '{pipe_cfg.source}'"
            )
        for dep in pipe_cfg.depends_on:
            if dep not in pipeline_names:
                errors.append(
                    f"Pipeline '{pipe_name}' depends_on undefined pipeline '{dep}'"
                )

    if errors:
        logger.warning("config validation issues", count=len(errors))

    return errors
```

- [ ] **Step 4: Update config __init__.py exports**

```python
# src/dataenginex/config/__init__.py
"""Unified config system for dex.yaml.

Public API::

    from dataenginex.config import DexConfig, load_config, validate_config
"""
from __future__ import annotations

from dataenginex.config.loader import load_config, resolve_env_vars, validate_config
from dataenginex.config.schema import DexConfig

__all__ = ["DexConfig", "load_config", "resolve_env_vars", "validate_config"]
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_config_loader.py -v`
Expected: All tests PASS

- [ ] **Step 6: Lint + typecheck**

Run: `uv run ruff check src/dataenginex/config/ && uv run mypy src/dataenginex/config/`
Expected: Clean

- [ ] **Step 7: Commit**

```bash
git add src/dataenginex/config/ tests/unit/test_config_loader.py
git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" -m "feat: add config loader — YAML parsing, env var resolution, config layering"
```

---

## Task 8: CLI Foundation — `dex` Entry Point + `dex validate`

**Files:**
- Create: `src/dataenginex/cli/__init__.py`
- Create: `src/dataenginex/cli/main.py`
- Create: `src/dataenginex/cli/validate.py`
- Create: `tests/unit/test_cli_validate.py`

- [ ] **Step 1: Write tests for the CLI**

```python
# tests/unit/test_cli_validate.py
"""Tests for the `dex validate` CLI command."""
from __future__ import annotations

from pathlib import Path
from textwrap import dedent

from click.testing import CliRunner

from dataenginex.cli.main import dex


class TestDexCLI:
    """Test the top-level `dex` command group."""

    def test_version(self) -> None:
        runner = CliRunner()
        result = runner.invoke(dex, ["version"])
        assert result.exit_code == 0
        assert "dataenginex" in result.output.lower() or "." in result.output

    def test_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(dex, ["--help"])
        assert result.exit_code == 0
        assert "validate" in result.output


class TestDexValidate:
    """Test `dex validate` against various dex.yaml files."""

    def test_valid_config(self, tmp_path: Path) -> None:
        yaml_content = dedent("""\
            project:
              name: test-project
            data:
              sources:
                users:
                  type: csv
                  path: data/users.csv
              pipelines:
                clean:
                  source: users
                  transforms: []
        """)
        config_file = tmp_path / "dex.yaml"
        config_file.write_text(yaml_content)

        runner = CliRunner()
        result = runner.invoke(dex, ["validate", "--config", str(config_file)])
        assert result.exit_code == 0
        assert "valid" in result.output.lower() or "ok" in result.output.lower()

    def test_missing_config_file(self, tmp_path: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(
            dex, ["validate", "--config", str(tmp_path / "nonexistent.yaml")]
        )
        assert result.exit_code != 0

    def test_invalid_yaml(self, tmp_path: Path) -> None:
        config_file = tmp_path / "dex.yaml"
        config_file.write_text(": : broken {{{")

        runner = CliRunner()
        result = runner.invoke(dex, ["validate", "--config", str(config_file)])
        assert result.exit_code != 0

    def test_cross_ref_error(self, tmp_path: Path) -> None:
        yaml_content = dedent("""\
            project:
              name: bad-refs
            data:
              pipelines:
                clean:
                  source: ghost_source
                  transforms: []
        """)
        config_file = tmp_path / "dex.yaml"
        config_file.write_text(yaml_content)

        runner = CliRunner()
        result = runner.invoke(dex, ["validate", "--config", str(config_file)])
        assert result.exit_code != 0
        assert "ghost_source" in result.output
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_cli_validate.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Create CLI package**

```python
# src/dataenginex/cli/__init__.py
"""CLI package for the `dex` command."""
from __future__ import annotations
```

- [ ] **Step 4: Implement main CLI entry point**

```python
# src/dataenginex/cli/main.py
"""``dex`` CLI — unified command-line interface for DataEngineX.

Entry point: ``dex = "dataenginex.cli.main:dex"`` in pyproject.toml.
"""
from __future__ import annotations

import click
from importlib.metadata import version as pkg_version

from dataenginex.cli.validate import validate


@click.group()
def dex() -> None:
    """DataEngineX — unified Data + ML + AI platform."""


@dex.command()
def version() -> None:
    """Show the installed DataEngineX version."""
    ver = pkg_version("dataenginex")
    click.echo(f"dataenginex {ver}")


# Register subcommands
dex.add_command(validate)
```

- [ ] **Step 5: Implement validate subcommand**

```python
# src/dataenginex/cli/validate.py
"""``dex validate`` — validate a dex.yaml config file."""
from __future__ import annotations

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel

from dataenginex.config.loader import load_config, validate_config
from dataenginex.core.exceptions import ConfigError

console = Console()


@click.command()
@click.option(
    "--config",
    "config_path",
    default="dex.yaml",
    type=click.Path(exists=False),
    help="Path to dex.yaml config file.",
)
def validate(config_path: str) -> None:
    """Validate a dex.yaml configuration file."""
    path = Path(config_path)

    # Load and parse
    try:
        config = load_config(path)
    except ConfigError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        sys.exit(1)

    # Cross-reference validation
    errors = validate_config(config)

    if errors:
        console.print(
            Panel(
                "\n".join(f"  - {e}" for e in errors),
                title="[red]Validation Errors[/red]",
                border_style="red",
            )
        )
        sys.exit(1)

    console.print(
        f"[green]OK[/green] — {path} is valid "
        f"(project: {config.project.name})"
    )
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_cli_validate.py -v`
Expected: All tests PASS

- [ ] **Step 7: Test the actual CLI entry point**

Run: `uv run dex --help`
Expected: Shows help with `validate` and `version` subcommands.

Run: `uv run dex version`
Expected: Shows `dataenginex 0.8.9`

- [ ] **Step 8: Lint + typecheck**

Run: `uv run ruff check src/dataenginex/cli/ && uv run mypy src/dataenginex/cli/`
Expected: Clean

- [ ] **Step 9: Commit**

```bash
git add src/dataenginex/cli/ tests/unit/test_cli_validate.py
git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" -m "feat: add dex CLI — entry point, version, and validate commands"
```

---

## Task 9: Integration Test — Full dex validate Flow

**Files:**
- Create: `tests/unit/test_config_integration.py`
- Create: `examples/dex.yaml` (example config file)

- [ ] **Step 1: Create an example dex.yaml**

```yaml
# examples/dex.yaml
# Example DataEngineX project configuration.
# Only `project.name` is required — everything else has defaults.

project:
  name: movie-recommender
  version: "0.1.0"
  description: End-to-end movie recommendation pipeline

data:
  engine: duckdb
  sources:
    movies:
      type: csv
      path: data/movies.csv
    ratings:
      type: csv
      path: data/ratings.csv
  pipelines:
    ingest_movies:
      source: movies
      transforms:
        - type: filter
          condition: "year >= 2000"
        - type: deduplicate
          columns: [movie_id]
      quality:
        completeness: 0.95
        uniqueness: [movie_id]
      destination: silver_movies
    ingest_ratings:
      source: ratings
      transforms:
        - type: cast
          columns: [rating]
          expression: "CAST(rating AS FLOAT)"
      destination: silver_ratings
      depends_on: [ingest_movies]

ml:
  tracker: builtin
  experiments:
    collaborative_filter:
      model_type: sklearn
      target: rating
      features: [user_id, movie_id, genre_encoded]
  drift:
    monitor: [collaborative_filter]
    method: psi
    threshold: 0.15

ai:
  llm:
    provider: ollama
    model: qwen3:8b
  retrieval:
    strategy: hybrid
    top_k: 10
  agents:
    movie_expert:
      system_prompt: "You are a movie recommendation assistant."
      tools: [sql_query, predict]
      max_iterations: 5

server:
  port: 17000
```

- [ ] **Step 2: Write integration test**

```python
# tests/unit/test_config_integration.py
"""Integration test: load the example dex.yaml and validate it end-to-end."""
from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from dataenginex.cli.main import dex
from dataenginex.config.loader import load_config, validate_config


EXAMPLE_CONFIG = Path(__file__).parent.parent.parent / "examples" / "dex.yaml"


class TestExampleConfig:
    def test_example_config_loads(self) -> None:
        if not EXAMPLE_CONFIG.exists():
            pytest.skip("examples/dex.yaml not present")
        cfg = load_config(EXAMPLE_CONFIG)
        assert cfg.project.name == "movie-recommender"
        assert "movies" in cfg.data.sources
        assert "ingest_movies" in cfg.data.pipelines
        assert cfg.ai.llm.provider == "ollama"

    def test_example_config_validates(self) -> None:
        if not EXAMPLE_CONFIG.exists():
            return
        cfg = load_config(EXAMPLE_CONFIG)
        errors = validate_config(cfg)
        assert errors == []

    def test_cli_validate_example(self) -> None:
        if not EXAMPLE_CONFIG.exists():
            return
        runner = CliRunner()
        result = runner.invoke(dex, ["validate", "--config", str(EXAMPLE_CONFIG)])
        assert result.exit_code == 0
        assert "ok" in result.output.lower()
```

- [ ] **Step 3: Run integration test**

Run: `uv run pytest tests/unit/test_config_integration.py -v`
Expected: All 3 tests PASS

- [ ] **Step 4: Run full test suite**

Run: `uv run pytest tests/unit/ -x -q`
Expected: All tests pass (old + new)

- [ ] **Step 5: Run lint + typecheck on entire project**

Run: `uv run ruff check src/dataenginex/ && uv run mypy src/dataenginex/`
Expected: Clean (or pre-existing issues only)

- [ ] **Step 6: Commit**

```bash
git add examples/dex.yaml tests/unit/test_config_integration.py
git commit --author="jaymyaka <jayapal.myaka99@gmail.com>" -m "feat: add example dex.yaml and integration test for config system"
```

---

## Task 10: Final Validation — Exit Criteria Check

**Files:** None (verification only)

- [ ] **Step 1: Verify `dex validate` works on example config**

Run: `uv run dex validate --config examples/dex.yaml`
Expected: `OK — examples/dex.yaml is valid (project: movie-recommender)`

- [ ] **Step 2: Verify all tests pass**

Run: `uv run poe test-unit`
Expected: All tests pass

- [ ] **Step 3: Verify lint is clean**

Run: `uv run poe lint`
Expected: No errors

- [ ] **Step 4: Verify typecheck passes**

Run: `uv run poe typecheck`
Expected: Clean (or document pre-existing issues)

- [ ] **Step 5: Verify CLI entry point works**

Run: `uv run dex --help`
Expected: Shows `dex` help with `validate`, `version` subcommands

Run: `uv run dex version`
Expected: Shows current version

---

## Phase 0 Exit Criteria Summary

| Criteria | Verification |
|----------|-------------|
| Config schema validates all `dex.yaml` sections | `test_config_schema.py` passes |
| Env var interpolation (`${VAR:-default}`) works | `test_config_loader.py` passes |
| Config layering (base + overlay) works | `test_config_loader.py::test_load_with_overlay` passes |
| Cross-reference validation catches bad refs | `test_config_loader.py::test_pipeline_references_missing_source` passes |
| All 10 Base\* ABCs defined and enforce contracts | `test_core_interfaces.py` passes |
| BackendRegistry registers, discovers, has defaults | `test_core_registry.py` passes |
| Exception hierarchy established | `test_core_exceptions.py` passes |
| `dex validate` CLI command works | `test_cli_validate.py` passes + manual `uv run dex validate` |
| Example `dex.yaml` provided and validates | `test_config_integration.py` passes |
| loguru fully replaced with structlog | No `loguru` imports remain |
| Python 3.12+ target | `pyproject.toml` updated |
| All existing tests still pass | `uv run poe test-unit` |

**Next:** Phase 1 plan (Data Layer — DuckDB connector, pipeline runner, transforms, `dex run`).
