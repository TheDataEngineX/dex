# DataEngineX 1.0 — Master Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build DataEngineX 1.0 — a unified, config-driven Data + ML + AI platform with one YAML config, one CLI, one UI.

**Architecture:** Opinionated Core + Swappable Extras. DuckDB as universal data substrate. BackendRegistry[T] pattern for all pluggable subsystems. Config-driven everything via `dex.yaml`. Python >=3.13 stable.

**Tech Stack:** Python 3.13+ · DuckDB 1.5 · FastAPI · Pydantic · structlog · Click · Rich · PyArrow · croniter · sentence-transformers (opt) · ONNX (opt)

**Spec:** `docs/superpowers/specs/2026-03-21-dataenginex-v2-system-redesign.md`

**Phase 0 (DONE):** Config system, BackendRegistry, 10 Base* ABCs, exceptions, CLI (`dex validate`, `dex version`), 66 tests — merged in PR #197.

---

## Phase Overview

| Phase | Focus | Exit Criteria | Key Gaps Resolved |
|-------|-------|---------------|-------------------|
| Pre-1 | Python 3.13 bump + dep cleanup | `requires-python = ">=3.13"`, CI green | AD7 override |
| 1 | Data Layer | `dex run ingest-movies` works | G9, G12, G25, G26 |
| 2 | ML Layer | `dex train` → tracker → serve | G5, G6, G8 (partial) |
| 3 | AI Layer | `dex agent movie-expert` chats | G7, G8, G27-G29 |
| 4 | CLI + API + Studio | Full `dex init → serve --studio` | G3, G4, G10, G36-G42, G44 |
| 5 | Infrastructure + Release | `pip install dataenginex` 1.0.0 | G52-G58, PyPI publish |

Each phase has its own detailed plan document. This master plan defines the file structure, dependency order, and shared conventions. Phase-specific plans are created when execution begins.

---

## Python 3.13 Bump (Pre-Phase 1)

### Rationale

The spec says AD7: `>=3.12`. But:
- We're already running Python 3.13.12
- Python 3.12 reaches end-of-life Oct 2028; 3.13 is Oct 2029
- 3.13 features we want: improved error messages, `type` statement (PEP 695), better `asyncio.TaskGroup`
- All our deps support 3.13 (already tested in CI)
- No enterprise users to worry about yet — this is pre-1.0

### Files to Change

| File | Change |
|------|--------|
| `pyproject.toml` | `requires-python = ">=3.13"` |
| `.python-version` | Create: `3.13` |
| `.github/workflows/ci.yml` (workspace) | Matrix: `["3.13"]` |
| `CLAUDE.md` | Python 3.13+ |
| `docs/ARCHITECTURE.md` | Python 3.13+ |
| `README.md` | Badge + install instructions |

---

## File Structure (Full Target for 1.0)

This is the target directory layout. Phases build toward this incrementally.

```
src/dataenginex/
├── __init__.py
├── config/                     # ✅ Phase 0 (DONE)
│   ├── __init__.py
│   ├── loader.py
│   ├── schema.py
│   └── defaults.py
├── core/                       # ✅ Phase 0 (DONE) + Phase 1 additions
│   ├── __init__.py
│   ├── exceptions.py           # ✅ DONE
│   ├── interfaces.py           # ✅ DONE (10 ABCs)
│   ├── registry.py             # ✅ DONE
│   ├── schemas.py              # existing
│   ├── validators.py           # existing
│   ├── quality.py              # existing → Phase 1 refactor
│   └── medallion.py            # existing → Phase 1 refactor
├── data/                       # Phase 1
│   ├── __init__.py
│   ├── connectors/
│   │   ├── __init__.py         # connector_registry instance
│   │   ├── duckdb.py           # DuckDB connector (DEFAULT)
│   │   ├── csv.py              # CSV file connector
│   │   └── rest.py             # REST API connector
│   ├── transforms/
│   │   ├── __init__.py         # transform_registry instance
│   │   ├── sql.py              # DuckDB SQL transform (DEFAULT)
│   │   ├── cast.py
│   │   ├── deduplicate.py
│   │   ├── filter.py
│   │   └── derive.py
│   ├── quality/
│   │   ├── __init__.py
│   │   └── gates.py            # QualityGate (completeness, uniqueness, custom)
│   ├── lineage/
│   │   ├── __init__.py
│   │   └── tracker.py          # Column-level lineage (DuckDB-backed)
│   └── pipeline/
│       ├── __init__.py
│       ├── runner.py           # PipelineRunner: extract → transform → quality → load
│       ├── dag.py              # DAG resolution (depends_on)
│       └── checkpoint.py       # Checkpoint/retry per step
├── orchestration/              # Phase 1
│   ├── __init__.py
│   ├── builtin.py              # Cron scheduler (croniter + asyncio)
│   └── registry.py             # orchestrator_registry instance
├── ml/                         # Phase 2
│   ├── __init__.py
│   ├── tracking/
│   │   ├── __init__.py
│   │   ├── builtin.py          # SQLite-backed tracker (DEFAULT)
│   │   └── registry.py         # tracker_registry instance
│   ├── features/
│   │   ├── __init__.py
│   │   ├── builtin.py          # DuckDB-backed feature store (DEFAULT)
│   │   └── registry.py         # feature_store_registry instance
│   ├── training/
│   │   ├── __init__.py
│   │   └── sklearn.py          # sklearn/xgboost training
│   ├── serving/
│   │   ├── __init__.py
│   │   ├── builtin.py          # FastAPI model serving (DEFAULT)
│   │   └── registry.py         # serving_registry instance
│   ├── drift/
│   │   ├── __init__.py
│   │   └── psi.py              # PSI-based drift detection
│   └── model_registry/
│       ├── __init__.py
│       └── versioning.py       # Model versioning + stages
├── agents/                     # Phase 3
│   ├── __init__.py
│   ├── runtime/
│   │   ├── __init__.py
│   │   ├── builtin.py          # Simple ReAct loop (DEFAULT)
│   │   └── registry.py         # agent_runtime_registry instance
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── ollama.py           # Ollama provider (DEFAULT)
│   │   └── registry.py         # llm_provider_registry instance
│   ├── retrieval/
│   │   ├── __init__.py
│   │   ├── sparse.py           # BM25 via DuckDB FTS
│   │   ├── dense.py            # DuckDB VSS HNSW
│   │   ├── hybrid.py           # BM25 + Dense + RRF fusion
│   │   ├── reranker.py         # Cross-encoder reranker
│   │   └── registry.py         # retriever_registry instance
│   ├── vectorstore/
│   │   ├── __init__.py
│   │   ├── builtin.py          # DuckDB-backed vector store (DEFAULT)
│   │   └── registry.py         # vectorstore_registry instance
│   ├── memory/
│   │   ├── __init__.py
│   │   └── store.py            # Short-term + episodic memory
│   └── tools/
│       ├── __init__.py
│       ├── registry.py         # Tool registry
│       ├── sql_query.py        # SQL query tool
│       ├── predict.py          # Model prediction tool
│       └── search.py           # Vector search tool
├── api/                        # Phase 4 (partially exists)
│   ├── __init__.py             # existing
│   ├── app.py                  # App factory (NEW)
│   ├── auth.py                 # existing
│   ├── errors.py               # existing
│   ├── health.py               # existing
│   ├── pagination.py           # existing
│   ├── rate_limit.py           # existing
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── projects.py         # Project CRUD
│   │   ├── pipelines.py        # Pipeline run/status
│   │   ├── data.py             # Data explorer
│   │   ├── ml.py               # ML experiments/models
│   │   ├── agents.py           # Agent chat/manage
│   │   └── ws.py               # WebSocket (live logs, agent streaming)
│   └── middleware/             # move from middleware/
│       ├── logging.py
│       ├── metrics.py
│       └── tracing.py
├── cli/                        # Phase 0 (DONE) + Phase 1-4 additions
│   ├── __init__.py             # ✅ DONE
│   ├── main.py                 # ✅ DONE (validate, version)
│   ├── run.py                  # Phase 1: `dex run`
│   ├── init.py                 # Phase 4: `dex init`
│   ├── train.py                # Phase 2: `dex train`
│   ├── serve.py                # Phase 4: `dex serve`
│   ├── agent.py                # Phase 3: `dex agent`
│   ├── query.py                # Phase 4: `dex query`
│   └── studio.py               # Phase 4: `dex studio`
├── secops/                     # Phase 4 (partially exists)
│   ├── __init__.py
│   ├── pii.py                  # existing
│   ├── masking.py              # existing
│   ├── audit.py                # existing
│   └── gate.py                 # existing
├── observability/              # Phase 4 (refactor from middleware/)
│   ├── __init__.py
│   ├── metrics.py
│   ├── tracing.py
│   └── logging.py
├── lakehouse/                  # existing → Phase 1 integration
│   ├── __init__.py
│   ├── catalog.py
│   ├── partitioning.py
│   └── storage.py
├── warehouse/                  # existing → Phase 1 integration
│   ├── __init__.py
│   ├── lineage.py
│   └── transforms.py
├── plugins/                    # existing
│   ├── __init__.py
│   └── registry.py
└── templates/                  # Phase 4
    ├── minimal/
    ├── data-pipeline/
    ├── ml-project/
    ├── ai-agent/
    ├── full-stack/
    └── career-intelligence/
```

---

## Shared Conventions

### Registry Pattern (all phases)

Every subsystem gets a registry instance in its `__init__.py`:

```python
# src/dataenginex/data/connectors/__init__.py
from dataenginex.core.interfaces import BaseConnector
from dataenginex.core.registry import BackendRegistry

connector_registry: BackendRegistry[BaseConnector] = BackendRegistry("connector")
```

Backend implementations register via decorator:

```python
# src/dataenginex/data/connectors/duckdb.py
from dataenginex.data.connectors import connector_registry

@connector_registry.decorator("duckdb", is_default=True)
class DuckDBConnector(BaseConnector):
    ...
```

### Test Pattern (all phases)

Conformance test suites verify interface contracts. Both built-in and extra backends must pass:

```python
# tests/conformance/test_connector.py
class ConnectorConformanceTests:
    """All BaseConnector implementations must pass these."""
    def test_connect_disconnect(self, connector): ...
    def test_read_write_cycle(self, connector): ...
    def test_health_check(self, connector): ...

# tests/unit/test_duckdb_connector.py
class TestDuckDBConnector(ConnectorConformanceTests):
    @pytest.fixture
    def connector(self, tmp_path):
        return DuckDBConnector(database=str(tmp_path / "test.duckdb"))
```

### Module Public API (all phases)

Every package `__init__.py` re-exports its public API:

```python
# src/dataenginex/data/__init__.py
from dataenginex.data.connectors import connector_registry
from dataenginex.data.connectors.duckdb import DuckDBConnector
from dataenginex.data.pipeline.runner import PipelineRunner

__all__ = ["connector_registry", "DuckDBConnector", "PipelineRunner"]
```

### Error Handling (all phases)

Use the exception hierarchy from Phase 0:

```python
from dataenginex.core.exceptions import PipelineError, PipelineStepError

raise PipelineStepError(
    pipeline="ingest-movies",
    step="quality-check",
    message="Quality gate failed: completeness 0.72 < threshold 0.90",
)
```

### Config Integration (all phases)

Every subsystem reads from `DexConfig`. The runner instantiates backends based on config:

```python
config = load_config("dex.yaml")
connector_cls = connector_registry.get(config.data.engine)
connector = connector_cls(**source_config.connection)
```

---

## Phase 1: Data Layer — Detailed Plan

> **Separate plan:** `docs/superpowers/plans/2026-03-22-phase-1-data-layer.md`

### Scope

- DuckDB connector (default) + CSV connector
- PipelineRunner: extract → transform chain → quality gate → load
- DuckDB SQL transforms (filter, derive, cast, deduplicate)
- Medallion architecture integration (bronze/silver/gold storage)
- Quality gates (completeness, uniqueness, custom SQL)
- Column-level lineage tracking
- DAG resolution for cross-pipeline dependencies
- Checkpoint/retry per step
- Built-in cron scheduler (croniter + asyncio)
- `dex run [pipeline] [--all] [--dry-run]` CLI command

### Dependencies

- Phase 0 (DONE): config, registry, interfaces, exceptions, CLI
- DuckDB >= 1.5.0 (already in deps)
- PyArrow (already in deps via DuckDB)
- croniter (already in deps)

### Exit Criteria

```bash
# 1. Config-driven pipeline
echo 'project: {name: demo}
data:
  sources:
    movies: {type: csv, path: examples/movies.csv}
  pipelines:
    ingest-movies:
      source: movies
      steps:
        - {type: filter, condition: "rating > 5.0"}
        - {type: deduplicate, key: id}
      quality: {completeness: 0.9, uniqueness: [id]}
      target: {layer: silver}' > dex.yaml

# 2. Run pipeline
dex run ingest-movies

# 3. Verify output
dex query "SELECT count(*) FROM silver.ingest_movies"
```

### Task Count: ~25 tasks (est. 4-6 hours)

---

## Phase 2: ML Layer — Summary

> **Separate plan:** Created when Phase 1 is complete.

### Scope

- SQLite-backed experiment tracker (AD4: SQLite for metadata, not DuckDB)
- DuckDB-backed feature store (offline features)
- Model training (sklearn/xgboost integration)
- Model registry (versioning: development → staging → production → archived)
- Built-in model serving (FastAPI endpoints via `dex serve`)
- PSI drift detection
- `dex train [experiment]` and `dex diff <run1> <run2>` CLI commands
- MLflow backend as `[mlflow]` extra

### Dependencies

- Phase 1 (data layer — pipelines feed features)

### Exit Criteria

```bash
dex train sentiment-classifier
# → logs to SQLite tracker, saves model artifact
dex serve
# → model available at /api/v1/models/sentiment-classifier/predict
```

---

## Phase 3: AI Layer — Summary

> **Separate plan:** Created when Phase 2 is complete.

### Scope

- Built-in ReAct agent runtime (~200 lines, simple think→act→observe loop)
- Ollama LLM provider (default local)
- Tool registry (sql_query, predict, search)
- BM25 sparse retrieval (DuckDB FTS extension)
- Dense vector retrieval (DuckDB VSS HNSW extension)
- Hybrid retrieval (BM25 + Dense + RRF fusion)
- Cross-encoder reranker
- Agent memory (short-term context, episodic store)
- `dex agent <name> [--message M]` CLI command
- `[embeddings]` extra (sentence-transformers + ONNX runtime)
- LangGraph backend as `[agents]` extra
- Qdrant/LanceDB backends as `[vectors]` extra

### Dependencies

- Phase 2 (ML layer — models for predict tool, feature store for context)

### Exit Criteria

```bash
dex agent movie-expert --message "What are the highest rated sci-fi movies?"
# → agent uses sql_query tool on DuckDB, returns structured answer
```

---

## Phase 4: CLI + API + Studio — Summary

> **Separate plan:** Created when Phase 3 is complete.

### Scope

- Complete CLI: `dex init`, `dex serve`, `dex query`, `dex status`, `dex studio`
- Project management API (CRUD, multi-project isolation per AD6)
- WebSocket endpoints (live logs, agent chat streaming)
- `dex init --template` with 6 templates
- App factory (`api/app.py`) that auto-registers all routers
- SecOps integration (PII scan in pipeline, masking, audit trail)
- DEX Studio pages via REST API (Studio is pure HTTP client)

### Dependencies

- Phase 3 (AI layer — agent playground, retrieval tester)

### Exit Criteria

```bash
dex init my-project --template data-pipeline
cd my-project
dex serve --studio
# → full platform running at localhost:17000 (API) + localhost:7860 (Studio)
```

---

## Phase 5: Infrastructure + Release — Summary

> **Separate plan:** Created when Phase 4 is complete.

### Scope

- Dockerfile (multi-stage, `ghcr.io/thedataenginex/dataenginex`)
- docker-compose.yml (full Tier 2 stack)
- InfraDEX unified Helm chart
- Dagster, Feast, BentoML extras
- Cloud connectors (S3, GCS, BigQuery)
- MkDocs Material → Cloudflare Pages
- PyPI publish as `dataenginex` 1.0.0

### Dependencies

- Phase 4 (full platform working)

### Exit Criteria

```bash
pip install dataenginex && dex init demo && dex serve --studio
docker compose up  # full platform
# docs live at docs.dataenginex.org
```

---

## Dependency Graph

```
Phase 0 (DONE) ──→ Pre-Phase 1 ──→ Phase 1 ──→ Phase 2 ──→ Phase 3 ──→ Phase 4 ──→ Phase 5
  config             py3.13          data          ML           AI        CLI/API      infra
  registry           deps            pipelines     tracking     agents    studio       deploy
  interfaces                         transforms    features     retrieval templates    1.0.0
  exceptions                         quality       serving      memory
  CLI base                           lineage       drift        tools
                                     scheduler     train cmd    agent cmd
                                     run cmd
```

Each phase produces a working, testable, committable increment. No phase depends on a later phase.
