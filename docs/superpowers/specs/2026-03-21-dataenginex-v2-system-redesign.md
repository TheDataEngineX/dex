# DataEngineX 1.0 — System Redesign Spec

**Date:** 2026-03-21
**Status:** Approved
**Author:** Jay + Claude
**Version Note:** Current package is 0.8.x (pre-1.0). This spec defines the 1.0 architecture. Not a "v2" — it's the first stable release with unified architecture.

---

## Vision

DataEngineX is a **unified, config-driven platform** that orchestrates best-in-class Data + ML + AI tools through one YAML config, one CLI, and one UI — self-hosted, open-source, and production-ready.

**What it is:** An integration and orchestration layer over industry-standard tools.
**What it is NOT:** A replacement for DuckDB, MLflow, Dagster, or LangGraph.

**Differentiators:**
1. **Unified config** — one `dex.yaml` defines the entire data-to-AI pipeline
2. **Single pip install** — `pip install dataenginex` with progressive extras
3. **Self-hosted simplicity** — zero to production in `docker compose up`

---

## Architecture: Approach 3 — Opinionated Core + Swappable Extras

- **Zero-config mode:** `pip install dataenginex` gives DuckDB + FastAPI + built-in scheduler + SQLite tracker + ReAct agent runtime. Works immediately, no external services.
- **Scale-up mode:** Swap to industry tools via extras — same YAML config, just change the backend.
- **Embedding mode:** Retrieval features (hybrid search, reranking) require `pip install dataenginex[embeddings]` which pulls sentence-transformers + ONNX runtime (~200MB). NOT in base install to keep it lightweight. Base install stays <50MB.

---

## Repo Structure

### Current (6 repos) → Proposed (3 repos)

| Current | Proposed | GitHub Repo | Action |
|---------|----------|-------------|--------|
| `dex` | `dataenginex` | `github.com/TheDataEngineX/dataenginex` | Becomes THE monorepo |
| `datadex` | absorbed into `dataenginex.data` | — | Git subtree merge |
| `agentdex` | absorbed into `dataenginex.agents` | — | Git subtree merge |
| `careerdex` | `templates/career-intelligence/` | — | Becomes example template |
| `dex-studio` | `dex-studio` | `github.com/TheDataEngineX/dex-studio` | Different release cadence, pure HTTP client |
| `infradex` | `infradex` | `github.com/TheDataEngineX/infradex` | IaC concern, not library |
| `.github` | `.github` | `github.com/TheDataEngineX/.github` | Shared org config |

### Package Structure

```
dataenginex/
├── src/dataenginex/
│   ├── __init__.py
│   ├── config/                  # Unified YAML config system
│   │   ├── loader.py            # Load + resolve env vars + validate
│   │   ├── schema.py            # Pydantic models for all dex.yaml sections
│   │   └── defaults.py          # Built-in defaults
│   ├── core/                    # Shared primitives
│   │   ├── schemas.py           # Base Pydantic models
│   │   ├── registry.py          # Plugin/backend registry pattern
│   │   ├── interfaces.py        # Abstract interfaces (Base* ABCs)
│   │   └── exceptions.py        # Unified exception hierarchy
│   ├── api/                     # FastAPI server + middleware
│   │   ├── app.py               # App factory
│   │   ├── auth.py              # JWT auth
│   │   ├── middleware/          # Logging, metrics, rate limit, tracing
│   │   └── routers/             # Auto-registered route modules
│   ├── data/                    # Data layer (was datadex)
│   │   ├── connectors/          # Source/sink connectors
│   │   │   ├── base.py          # BaseConnector ABC
│   │   │   ├── csv.py           # Built-in
│   │   │   ├── duckdb.py        # Built-in (DEFAULT)
│   │   │   ├── postgres.py      # [postgres] extra
│   │   │   ├── mysql.py         # [mysql] extra
│   │   │   ├── s3.py            # [cloud] extra
│   │   │   ├── gcs.py           # [cloud] extra
│   │   │   ├── kafka.py         # [streaming] extra
│   │   │   ├── iceberg.py       # [lakehouse] extra
│   │   │   └── rest.py          # Built-in
│   │   ├── transforms/          # DuckDB SQL-based transforms
│   │   │   ├── base.py          # BaseTransform ABC
│   │   │   ├── sql.py           # Raw DuckDB SQL (DEFAULT)
│   │   │   ├── cast.py
│   │   │   ├── deduplicate.py
│   │   │   ├── filter.py        # DuckDB WHERE clause
│   │   │   └── derive.py        # DuckDB SQL expressions
│   │   ├── quality/             # Data quality gates
│   │   ├── lineage/             # Column-level lineage
│   │   └── lakehouse/           # Medallion architecture + storage
│   ├── orchestration/           # Pipeline orchestration
│   │   ├── base.py              # BaseOrchestrator ABC
│   │   ├── builtin.py           # Cron + DAG scheduler (DEFAULT)
│   │   ├── dagster_backend.py   # [dagster] extra
│   │   └── airflow_backend.py   # [airflow] extra
│   ├── ml/                      # ML lifecycle
│   │   ├── tracking/            # Experiment tracking
│   │   │   ├── base.py          # BaseTracker ABC
│   │   │   ├── builtin.py       # SQLite tracker (DEFAULT)
│   │   │   └── mlflow_backend.py # [mlflow] extra
│   │   ├── training/            # Model training
│   │   ├── features/            # Feature store
│   │   │   ├── base.py          # BaseFeatureStore ABC
│   │   │   ├── builtin.py       # DuckDB-backed (DEFAULT)
│   │   │   └── feast_backend.py # [feast] extra
│   │   ├── serving/             # Model serving
│   │   │   ├── base.py          # BaseServingEngine ABC
│   │   │   ├── builtin.py       # FastAPI server (DEFAULT)
│   │   │   └── bentoml_backend.py # [bentoml] extra
│   │   ├── registry/            # Model registry + versioning
│   │   ├── drift/               # PSI-based drift detection
│   │   ├── retrieval/           # Unified retrieval layer (NEW)
│   │   │   ├── base.py          # BaseRetriever ABC
│   │   │   ├── sparse.py        # BM25 via DuckDB FTS (BUILT-IN)
│   │   │   ├── dense.py         # DuckDB VSS HNSW (BUILT-IN)
│   │   │   ├── hybrid.py        # BM25 + Dense + RRF fusion (BUILT-IN)
│   │   │   ├── reranker.py      # Cross-encoder reranker (BUILT-IN)
│   │   │   ├── colbert_backend.py # [colbert] extra
│   │   │   ├── pageindex_backend.py # [pageindex] extra
│   │   │   ├── qdrant_backend.py  # [vectors] extra
│   │   │   └── lancedb_backend.py # [vectors] extra
│   │   └── vectorstore/         # Vector storage (CRUD)
│   │       ├── base.py          # BaseVectorStore ABC
│   │       ├── builtin.py       # DuckDB-backed
│   │       ├── qdrant_backend.py
│   │       └── lancedb_backend.py
│   ├── agents/                  # AI agent layer (was agentdex)
│   │   ├── runtime/             # Agent execution
│   │   │   ├── base.py          # BaseAgentRuntime ABC
│   │   │   ├── builtin.py       # Simple ReAct loop (DEFAULT)
│   │   │   └── langgraph_backend.py # [agents] extra
│   │   ├── llm/                 # LLM provider routing
│   │   │   ├── base.py          # BaseLLMProvider ABC
│   │   │   ├── ollama.py        # Ollama (DEFAULT local)
│   │   │   └── litellm_backend.py # [litellm] extra
│   │   ├── memory/              # Short-term, long-term, episodic
│   │   ├── tools/               # Tool registry + built-ins
│   │   └── workflows/           # Multi-agent DAG workflows
│   ├── secops/                  # Data security operations
│   │   ├── pii.py               # PII detection
│   │   ├── masking.py           # Data masking/redaction
│   │   └── audit.py             # Audit logging
│   ├── observability/           # Unified observability
│   │   ├── metrics.py           # Prometheus
│   │   ├── tracing.py           # OpenTelemetry
│   │   └── logging.py           # structlog
│   └── cli/                     # Unified CLI
│       ├── main.py              # `dex` entry point
│       ├── init.py              # `dex init`
│       ├── run.py               # `dex run`
│       ├── serve.py             # `dex serve`
│       ├── train.py             # `dex train`
│       ├── agent.py             # `dex agent`
│       ├── query.py             # `dex query`
│       └── studio.py            # `dex studio`
├── templates/                   # Project templates
│   ├── minimal/
│   ├── data-pipeline/
│   ├── ml-project/
│   ├── ai-agent/
│   ├── full-stack/
│   └── career-intelligence/     # CareerDEX as template
├── examples/
├── tests/
├── docs/
└── pyproject.toml
```

### Dependency Extras

```toml
[project.dependencies]
# Core (always installed):
# duckdb>=1.5.0, fastapi>=0.135.1, uvicorn>=0.42.0, structlog>=25.5.0,
# pydantic>=2.12.5, httpx>=0.28.1, click>=8.3.1, rich>=14.3.3,
# croniter>=6.0.0, pyarrow>=23.0.1
# FastAPI is core because: dex serve, model serving, WebSocket,
# and Studio integration all require it.

[project.optional-dependencies]
# Embeddings (required for retrieval/RAG — pulls ONNX, not PyTorch)
embeddings = ["sentence-transformers>=5.3", "onnxruntime>=1.22"]

# Tier 2: Self-hosted scale-up
dagster   = ["dagster>=1.12.20", "dagster-webserver>=1.12.20"]
mlflow    = ["mlflow>=3.10.1"]
agents    = ["langgraph>=1.10.1", "litellm>=1.65"]
vectors   = ["qdrant-client>=1.14", "lancedb>=0.20"]
feast     = ["feast>=0.41"]
colbert   = ["ragatouille>=0.0.9post2"]
pageindex = ["pageindex>=0.1"]

# Tier 3: Cloud/enterprise
cloud     = ["boto3>=1.36", "google-cloud-storage>=2.19", "google-cloud-bigquery>=3.30"]
spark     = ["pyspark>=4.1.1"]
kafka     = ["confluent-kafka>=2.8"]
lakehouse = ["pyiceberg>=0.9"]
bentoml   = ["bentoml>=1.4.36"]

# Bundles
all       = ["dataenginex[embeddings,dagster,mlflow,agents,vectors,feast,cloud,spark,kafka,lakehouse,bentoml,colbert]"]
```

---

## Unified Config System (dex.yaml)

One YAML file defines the entire Data + ML + AI pipeline. Every section is optional — progressive disclosure.

### Schema Overview

```yaml
project:
  name: string                    # project name
  version: string                 # semver

data:
  engine: duckdb | spark | polars
  sources: {name: SourceConfig}   # named data sources
  pipelines: {name: PipelineConfig}  # named pipelines
  schedule: {pipeline: cron}      # cron expressions

ml:
  tracker: builtin | mlflow
  features:
    store: builtin | feast
    definitions: {name: FeatureConfig}
  experiments: {name: ExperimentConfig}
  serving:
    engine: builtin | bentoml
    endpoints: [EndpointConfig]
  drift:
    monitor: [model_names]
    method: psi | ks | chi2
    threshold: float

ai:
  llm:
    provider: ollama | litellm
    model: string
    fallback: string (optional)
  retrieval:
    strategy: dense | hybrid | colbert | pageindex
    # backend-specific config
  vectorstore:
    backend: builtin | qdrant | lancedb
    embedding_model: string
  collections: {name: CollectionConfig}
  agents:
    runtime: builtin | langgraph
    definitions: {name: AgentConfig}

secops:
  pii: {scan, patterns, action}
  audit: {enabled, destination}

server:
  host, port, auth, cors

observability:
  metrics, tracing, log_level
```

### Key Design Decisions

- **Env var interpolation:** `${VAR}` and `${VAR:-default}` resolved before Pydantic validation
- **Cross-referencing:** Pipelines reference sources. Features reference pipelines. Agents reference endpoints. Validated at load time.
- **DuckDB SQL as expression language:** filter/derive transforms use SQL directly — no custom DSL
- **Config layering:** `dex.yaml` (base) + `dex.{env}.yaml` (override) + env vars (highest priority)
- **Multi-file support:** `!include sources.yaml` for large projects
- **Config snapshots:** Every run persists resolved config for reproducibility

---

## Data Flow Architecture

### DuckDB-Centric Design

DuckDB is the universal data substrate:
- Pipeline transforms (SQL expressions)
- Feature store backend (offline features)
- Vector search (HNSW index via VSS extension)
- Experiment tracking storage (SQLite mode)
- Agent SQL tool execution
- Data quality checks (SQL aggregations)
- Lineage metadata storage

DuckDB 1.5 reads Parquet, CSV, JSON, Postgres, MySQL, S3 natively — most connectors become thin wrappers.

**When to upgrade beyond DuckDB:** Streaming (Kafka), high-concurrency writes (>100 req/s), datasets >100GB → add `[spark]`, `[kafka]`, `[lakehouse]` extras.

### Pipeline Execution Flow

```
Config → Extract → Transform Chain → Quality Gate → SecOps Scan → Load → Lineage
```

- Checkpoint after each step (bronze write before transforms)
- Retry from last checkpoint on failure
- Cross-pipeline dependencies via `depends_on`
- Lineage tracked at every step

### Medallion Architecture

```
Bronze (raw) → Silver (clean) → Gold (enriched) → Feature Store → ML/AI
```

Storage backends: local parquet (default) | S3 | GCS | Iceberg

---

## Retrieval & Vector Search Architecture

### Supported Strategies

| Strategy | Backend | Install | Use Case |
|----------|---------|---------|----------|
| BM25 keyword search | DuckDB FTS | Built-in | Exact matches, identifiers |
| Dense vector search | DuckDB VSS (HNSW) | Built-in | Semantic similarity, small-medium |
| Dense vector search | Qdrant | `[vectors]` | Production scale, filtering, multi-tenancy |
| Dense vector search | LanceDB | `[vectors]` | Embedded, multimodal, disk-first |
| Hybrid search | BM25 + DuckDB VSS + RRF | Built-in | Best default RAG retrieval |
| Late interaction | ColBERT via RAGatouille | `[colbert]` | Highest accuracy retrieval |
| Vectorless | PageIndex tree indexing | `[pageindex]` | Document-heavy, no embedding cost |

### Default RAG Pipeline (Zero Config)

```
Query → BM25 (50 results) + Dense (50 results) → RRF Fusion → Cross-Encoder Rerank → Top 10 → LLM
```

All in-process via DuckDB + sentence-transformers. Zero external services.

---

## DEX Studio Redesign

**Goal:** Single pane of glass — create projects, build pipelines, train models, deploy agents, monitor everything.

### Pages (12)

1. Dashboard — project overview + health
2. Projects — create/manage dex.yaml projects (templates, config editor)
3. Pipelines — visual DAG, run history, logs, data preview, quality
4. Data Explorer — bronze/silver/gold browser, schema viewer, SQL editor, lineage graph
5. ML Workspace — experiments, run comparison, feature store, model registry, drift, serving
6. Agent Playground — chat interface, tool execution log, memory inspector, cost tracker
7. Retrieval — collections browser, search tester, embedding status
8. Observability — health, Prometheus charts, log viewer, trace explorer, audit
9. SecOps — PII scan results, masking rules, audit trail
10. Settings — connection, theme, API keys

### Key Design Rules

- Studio has NO Python dependency on `dataenginex` — pure HTTP client
- All interaction via REST API + WebSocket (live logs, agent chat streaming)
- NiceGUI 3.x with `ui.echart()` for charts, `ui.codemirror()` for YAML editor
- Read-only DuckDB access from Studio (SELECT only)

---

## CLI Design

### Commands

```
dex init <name> [--template T]     # scaffold project
dex validate                       # validate dex.yaml
dex run [pipeline] [--all] [--schedule] [--dry-run]
dex train [experiment] [--promote run-id]
dex serve [--studio] [--workers N]
dex agent <name> [--message M] [--format json]
dex query <sql> [--interactive]
dex studio                         # launch DEX Studio
dex status                         # project health
dex diff <run1> <run2>             # compare runs
dex version
```

### Entry Point

```toml
[project.scripts]
dex = "dataenginex.cli.main:dex"
```

---

## Deployment Tiers

### Tier 1: Laptop (Zero Infrastructure)

```bash
pip install dataenginex
dex init my-project && cd my-project
dex serve --studio
```

Everything in-process: DuckDB, SQLite tracker, built-in scheduler, Ollama (local).

### Tier 2: Single VPS (Docker Compose)

```bash
# Hetzner CX41 (~15 EUR/mo)
# Images from ghcr.io/thedataenginex/*
docker compose up -d
```

Adds: Postgres, Redis, Qdrant, Ollama (GPU), Prometheus, Grafana, Jaeger.

### Tier 3: Kubernetes (K3s / EKS / GKE)

Helm chart + ArgoCD. Same `dex.yaml`, different `values.yaml` per environment.
Container images pulled from `ghcr.io/thedataenginex/dataenginex`.

### Config Adapts to Tier

```bash
dex serve                                  # laptop (defaults)
dex serve --override dex.prod.yaml         # VPS/K8s (swap backends)
```

---

## InfraDEX Restructure

- 6 Helm charts → 1 unified chart
- CLI removed (InfraDEX is pure IaC)
- One `docker compose up` = full platform
- Terraform: Hetzner VPS priority, AWS/GCP secondary
- One-click deploy script for Tier 2
- Container images pushed to `ghcr.io/thedataenginex/*` (GitHub Container Registry, free for public repos)
- CI/CD: GitHub Actions builds → GHCR push → ArgoCD sync
- Docs hosted at `docs.dataenginex.org` (MkDocs Material → Cloudflare Pages)

---

## Tech Stack (Verified March 2026)

### Core Dependencies (always installed)

| Component | Tool | Version | Role |
|-----------|------|---------|------|
| Runtime | Python | >=3.12 | Language runtime |
| Data engine | DuckDB | 1.5.0 | Universal data substrate |
| API framework | FastAPI | 0.135.1 | Server, model serving, WebSocket |
| ASGI server | uvicorn | 0.42.0 | Production server |
| Validation | Pydantic | 2.12.5 | Config schema, data models |
| HTTP client | httpx | 0.28.1 | External API calls |
| Logging | structlog | 25.5.0 | Structured logging (JSON) |
| Data format | PyArrow | 23.0.1 | Parquet read/write |
| CLI | Click | 8.3.1 | CLI framework |
| CLI display | Rich | 14.3.3 | Terminal output |
| Scheduling | croniter | 6.0.0 | Cron expression parsing |

### Optional Extras

| Component | Tool | Version | Extra | Role |
|-----------|------|---------|-------|------|
| Orchestration | Dagster | 1.12.20 | `[dagster]` | Production orchestration |
| Experiment tracking | MLflow | 3.10.1 | `[mlflow]` | Industry-standard tracking |
| Feature store | Feast | 0.41+ | `[feast]` | Online+offline features |
| Model serving | BentoML | 1.4.36 | `[bentoml]` | Production model serving |
| Vector DB | Qdrant | 1.17.0 | `[vectors]` | Production vector search |
| Vector DB | LanceDB | 0.20+ | `[vectors]` | Embedded/multimodal vectors |
| Retrieval | ColBERT/RAGatouille | 0.0.9post2 | `[colbert]` | Highest accuracy retrieval |
| Retrieval | PageIndex | 0.1+ | `[pageindex]` | Vectorless document retrieval |
| Embeddings | sentence-transformers | 5.3.0 | `[embeddings]` | Embedding models (ONNX) |
| Agent runtime | LangGraph | 1.10.1 | `[agents]` | Multi-agent workflows |
| LLM routing | LiteLLM | 1.65+ | `[agents]` | 100+ LLM providers |
| LLM local | Ollama | 0.18.2 | — (external) | Default local LLM |
| Data format | Apache Iceberg | v3 spec | `[lakehouse]` | Open table format |
| Spark | PySpark | 4.1.1 | `[spark]` | Distributed processing |

### Dev Tooling

| Tool | Version | Purpose |
|------|---------|---------|
| uv | 0.10.12 | Package manager + virtualenvs |
| Ruff | 0.15.7 | Linting + formatting |
| mypy | 1.19.1 | Static type checking (strict) |
| pytest | 9.1 | Testing framework |

### Infrastructure (InfraDEX)

| Component | Tool | Role |
|-----------|------|------|
| UI | NiceGUI 3.8.0 | DEX Studio |
| Observability | Prometheus + Grafana + OTel | Metrics, tracing, logging |
| IaC | Terraform + Helm + K3s | Deployment automation |
| Container registry | ghcr.io/thedataenginex/* | Docker images (GHCR) |
| CI/CD | GitHub Actions + ArgoCD | Automation + GitOps |

---

## Gap Registry (58 gaps identified and resolved)

### Critical Path (must resolve before v1)

| ID | Gap | Resolution |
|----|-----|------------|
| G1 | No unified config schema | ONE `dex.yaml` with Pydantic validation |
| G2 | No backend interface pattern | Base* ABCs + registry pattern for every layer |
| G3 | No unified CLI | ONE `dex` command with subcommands |
| G4 | No project scaffolding | `dex init --template` with 6 templates |
| G5 | No built-in experiment tracker | SQLite-backed tracker |
| G6 | No built-in scheduler | Cron scheduler via croniter + asyncio |
| G7 | No built-in vector search | DuckDB VSS HNSW + NumPy fallback |
| G8 | Agent runtime hollow | Simple ReAct loop (~200 lines) |
| G9 | PipelineRunner not implemented | DuckDB-centric extract→transform→quality→load |
| G10 | Studio has no project management | Project CRUD API + template UI |
| G12 | Filter/derive transforms stubbed | DuckDB SQL expressions (zero custom parsing) |
| G15 | No env var interpolation | `${VAR:-default}` resolver before validation |
| G16 | No cross-reference validation | Pydantic model_validator checks all refs |
| G20 | DuckDB can't do everything | Clear upgrade paths documented per limitation |
| G27 | No retrieval abstraction | BaseRetriever ABC with 7 strategy implementations |
| G28 | No BM25/full-text search | DuckDB built-in FTS |
| G29 | No fusion/reranking | RRF (20 lines) + cross-encoder |
| G36 | No project management API | Projects module + SQLite metadata DB |
| G37 | No WebSocket for live logs | FastAPI WebSocket endpoints |
| G44 | CLI fragmented across repos | ONE `dex` CLI replaces all |
| G51 | No config override mechanism | Deep merge: base + env override + env vars |

### Important (v1 should address)

| ID | Gap | Resolution |
|----|-----|------------|
| G11 | No migration strategy | Git subtree merge preserves history |
| G17 | Config multi-file support | `!include` directive |
| G18 | No config diffing | Config snapshots per run + `dex diff` |
| G21 | DuckDB extension management | Auto-install on first use |
| G22 | No data versioning | Partition by run date; Iceberg for time-travel |
| G23 | Agent SQL security risk | allowed_tables + read-only connection |
| G24 | Feature store online serving | In-memory at startup; Feast for Redis-backed |
| G25 | Pipeline failure recovery | Checkpoint per step + retry from last |
| G26 | Cross-pipeline dependencies | `depends_on` in config → DAG ordering |
| G30 | Embedding model download at runtime | Pre-download during `dex init` |
| G34 | No auto-populate collections | Post-pipeline hook triggers embedding |
| G38 | No visual DAG in NiceGUI | v1: Mermaid render; v2: drag-and-drop |
| G39 | Studio can't edit config | CodeMirror YAML editor + PUT API |
| G40 | Agent chat streaming | WebSocket token-by-token |
| G41 | SQL query guardrails | Read-only DuckDB connection |
| G42 | No multi-project support | Server manages registered projects |
| G50 | `dex diff` needs run storage | `.dex/runs/` directory + SQLite index |
| G52 | No health-check orchestration | Docker healthcheck + depends_on conditions |

### Deferred (v2+)

| ID | Gap | Resolution |
|----|-----|------------|
| G13 | No multi-user auth | JWT for v1; API key rotation in v2 |
| G19 | Secret management basic | Env vars for v1; Vault integration in v2 |
| G31 | LanceDB as alternative default | DuckDB VSS default; LanceDB in [vectors] |
| G32 | ColBERT storage heavy | Document tradeoff; recommend for accuracy-critical |
| G33 | PageIndex requires LLM per query | Document: no embed cost but LLM cost per query |
| G35 | pgvector missing | Add in v2 when users request it |
| G43 | NiceGUI charts | ui.echart() for all metric visualization |
| G53 | DuckDB in Docker stateless | Mount volumes for persistence |
| G54 | GPU optional for Ollama | Document: GPU for >7B models, CPU for ≤7B |
| G55 | No backup strategy | backup.sh: pg_dump + models + .dex → S3 |
| G56 | Helm per-project ConfigMap | One ConfigMap per project; namespace isolation |
| G57 | MLflow not in compose | Docker compose profiles: `--profile mlflow` |
| G58 | No Loki in Tier 2 | Compose profiles: `--profile full-observability` |

---

## Architectural Decisions (from spec review)

### AD1: FastAPI is a core dependency (not optional)

FastAPI is required for: `dex serve`, built-in model serving, WebSocket live logs, Studio
communication, and agent chat streaming. It cannot be optional. Included in base install.

### AD2: Logging — structlog only

v1 standardizes on `structlog`. Remove `loguru` dependency. One logging library for an
opinionated platform. structlog's processor pipeline + JSON output + stdlib integration
covers all needs.

### AD3: DuckDB single-writer concurrency model

DuckDB is single-writer, multiple-reader. Impact on `dex serve`:
- **Pipeline writes:** Serialized via asyncio queue. Only one pipeline writes at a time.
  Multiple pipelines can run transforms in parallel (read-only), but the final Load step
  is serialized.
- **`dex serve --workers N`:** Each worker gets its own DuckDB connection for reads.
  Writes go through a single writer process (FastAPI lifespan manages the writer).
- **Tier 2/3:** When scaling beyond single-node, pipeline writes go to Postgres/S3
  (configured in `dex.prod.yaml`). DuckDB remains the transform engine (read path only).
- **Run data stored in `.dex/runs.db`:** SQLite (not DuckDB) for run metadata — SQLite
  handles concurrent writes from multiple workers via WAL mode.

### AD4: Built-in tracker uses SQLite (not DuckDB)

The experiment tracker uses SQLite for metadata (runs, params, metrics) because:
- SQLite supports concurrent writers (WAL mode)
- DuckDB is optimized for analytics, not OLTP metadata writes
- MLflow also uses SQLite as its default backend
- DuckDB remains the data processing engine for pipeline transforms and queries

### AD5: Embedding models require explicit opt-in

`pip install dataenginex` does NOT include sentence-transformers or PyTorch/ONNX.
Retrieval/RAG features require `pip install dataenginex[embeddings]` which pulls
sentence-transformers + ONNX runtime (~200MB, no PyTorch).

For users who want zero ML deps: BM25 keyword search works without `[embeddings]`.
Vector search and hybrid search require it.

### AD6: Project isolation on multi-project server

Each project gets its own:
- DuckDB database file (data isolation)
- `.dex/` directory (run history, tracker)
- Data directory (lakehouse layers)

API routes are scoped: `/api/v1/projects/{name}/pipelines/...`
Agent SQL queries are sandboxed to the project's DuckDB instance.
No cross-project data access in v1. Multi-user auth deferred to v2.

### AD7: Python 3.12+ (relaxed from 3.13+)

Current `pyproject.toml` requires 3.13+. This excludes many enterprise users.
v1 targets `>=3.12` which is the current LTS-equivalent. Python 3.12 has the
performance improvements (specializing adaptive interpreter) and 3.13 features
(free-threading) are not needed.

### AD8: Error handling and graceful degradation

- **Ollama not running:** `dex agent` fails fast with clear message: "Ollama not
  reachable at localhost:11434. Install: https://ollama.com"
- **Optional extra not installed:** Config validation catches this at load time, not
  runtime. `dex validate` reports: "ai.vectorstore.backend: qdrant requires
  `pip install dataenginex[vectors]`"
- **DuckDB OOM on large dataset:** Catch MemoryError, suggest: "Dataset exceeds
  available memory. Options: (1) increase system RAM, (2) use [spark] extra for
  distributed processing, (3) partition your pipeline source."
- **Missed cron triggers:** Built-in scheduler persists last-run timestamps to
  `.dex/scheduler.db`. On restart, checks for missed triggers and runs them
  immediately (configurable: `schedule.catch_up: true|false`).

---

## Testing Strategy

### Interface Conformance Tests

Every `Base*` ABC gets a conformance test suite. Backend implementations (both built-in
and extras) must pass the same tests:

```python
# tests/conformance/test_tracker.py
class TrackerConformanceTests:
    """Both BuiltinTracker and MLflowTracker must pass these."""

    def test_create_experiment(self, tracker: BaseTracker): ...
    def test_log_params(self, tracker: BaseTracker): ...
    def test_log_metrics(self, tracker: BaseTracker): ...
    def test_list_runs(self, tracker: BaseTracker): ...

# tests/unit/test_builtin_tracker.py
class TestBuiltinTracker(TrackerConformanceTests):
    @pytest.fixture
    def tracker(self, tmp_path):
        return BuiltinTracker(db_path=tmp_path / "tracker.db")

# tests/integration/test_mlflow_tracker.py (requires mlflow server)
class TestMLflowTracker(TrackerConformanceTests):
    @pytest.fixture
    def tracker(self):
        return MLflowTracker(uri="http://localhost:5000")
```

### Test Tiers

| Tier | What | When | External services |
|------|------|------|-------------------|
| Unit | Built-in backends, config, CLI, transforms | Every PR | None |
| Integration | External backends (Qdrant, Postgres, MLflow) | Nightly CI | Docker Compose test stack |
| E2E | Full `dex init` → `dex run` → `dex train` → `dex serve` | Pre-release | Docker Compose |
| Conformance | Interface compliance for all backends | Every PR (unit), nightly (integration) | Depends on backend |

### CI Matrix

```yaml
# .github/workflows/ci.yml
jobs:
  unit:
    # Runs on every PR — fast, no external deps
    - uv run poe lint
    - uv run poe typecheck
    - uv run poe test-unit          # built-in backends only

  integration:
    # Nightly — spins up test services
    services: [postgres, qdrant, redis, mlflow]
    - uv run poe test-integration   # external backend tests

  e2e:
    # Pre-release — full pipeline
    - uv run poe test-e2e
```

### Coverage Target

- 80%+ on new code (enforced by CI)
- Conformance tests are the quality gate for new backends
- `dex validate` is the user-facing test tool (validates config without executing)

---

## Phased Delivery Plan

### Phase 0: Foundation (weeks 1-3)

**Goal:** Monorepo setup + config system + core interfaces

- [ ] Create new monorepo structure (git subtree merge datadex, agentdex)
- [ ] Implement `dex.yaml` config loader (Pydantic schema, env var interpolation)
- [ ] Define all Base* ABCs (BaseConnector, BaseTracker, BaseRetriever, etc.)
- [ ] Implement registry pattern for backend discovery
- [ ] Port existing passing tests
- [ ] `dex validate` command working

**Exit criteria:** `dex validate` validates a `dex.yaml` with all sections.

### Phase 1: Data Layer (weeks 4-6)

**Goal:** Pipelines work end-to-end with DuckDB

- [ ] DuckDB connector (default engine)
- [ ] CSV connector
- [ ] PipelineRunner: extract → transform → quality → load
- [ ] DuckDB SQL transforms (filter, derive, cast, deduplicate)
- [ ] Medallion architecture (bronze/silver/gold)
- [ ] Quality gate (completeness, uniqueness)
- [ ] Lineage tracking
- [ ] `dex run` command working
- [ ] Built-in cron scheduler

**Exit criteria:** `dex run ingest-movies` processes CSV → Silver parquet with quality check.

### Phase 2: ML Layer (weeks 7-9)

**Goal:** Train, track, serve, detect drift

- [ ] SQLite-backed experiment tracker (built-in)
- [ ] DuckDB-backed feature store (built-in)
- [ ] Sklearn/XGBoost training
- [ ] Model registry (versioning, stages)
- [ ] Built-in model serving (FastAPI endpoints)
- [ ] PSI drift detection
- [ ] `dex train` and `dex diff` commands
- [ ] MLflow backend (`[mlflow]` extra)

**Exit criteria:** `dex train` trains a model, logs to tracker, serves via `dex serve`.

### Phase 3: AI Layer (weeks 10-12)

**Goal:** Agents work with tools, retrieval, memory

- [ ] Built-in ReAct agent runtime
- [ ] Ollama LLM provider
- [ ] Tool registry (sql_query, predict, search)
- [ ] BM25 sparse retrieval (DuckDB FTS)
- [ ] Dense retrieval (DuckDB VSS)
- [ ] Hybrid retrieval (RRF fusion)
- [ ] Agent memory (short-term, episodic)
- [ ] `dex agent` command (interactive + single-shot)
- [ ] `[embeddings]` extra with ONNX runtime
- [ ] LangGraph backend (`[agents]` extra)
- [ ] Qdrant backend (`[vectors]` extra)

**Exit criteria:** `dex agent movie-expert` chats, uses SQL + vector search tools.

### Phase 4: CLI + API + Studio (weeks 13-16)

**Goal:** Full user-facing experience

- [ ] Complete CLI (init, run, train, agent, serve, query, status, diff, studio)
- [ ] Project management API (CRUD, multi-project)
- [ ] WebSocket endpoints (live logs, agent chat streaming)
- [ ] `dex init --template` with all 6 templates
- [ ] DEX Studio: projects, pipelines, data explorer, ML workspace
- [ ] DEX Studio: agent playground, retrieval tester
- [ ] `dex query` interactive SQL REPL
- [ ] SecOps (PII detection, masking, audit)

**Exit criteria:** Full `dex init → run → train → agent → serve --studio` flow works.

### Phase 5: Infrastructure + Release (weeks 17-20)

**Goal:** Production deployment + PyPI publish + docs live

- [ ] Dockerfile (multi-stage, push to `ghcr.io/thedataenginex/dataenginex`)
- [ ] docker-compose.yml (Tier 2 full stack, images from GHCR)
- [ ] InfraDEX Helm chart (unified, `ghcr.io/thedataenginex/*` image refs)
- [ ] ArgoCD configuration
- [ ] One-click VPS deploy script
- [ ] Dagster backend (`[dagster]` extra)
- [ ] Feast backend (`[feast]` extra)
- [ ] BentoML backend (`[bentoml]` extra)
- [ ] Cloud connectors (S3, GCS, BigQuery)
- [ ] GitHub Actions: CI → build → push GHCR → ArgoCD sync
- [ ] Documentation (MkDocs Material → deploy to `docs.dataenginex.org` via Cloudflare Pages)
- [ ] GitHub org profile (`TheDataEngineX/.github/profile/README.md`)
- [ ] PyPI publish as `dataenginex` 1.0.0

**Exit criteria:** `pip install dataenginex && dex init demo && dex serve --studio` works.
`docker compose up` deploys full platform. Docs live at `docs.dataenginex.org`.

---

## GitHub Organization & Domain

### GitHub: TheDataEngineX

| Repo | URL | Visibility |
|------|-----|------------|
| `dataenginex` | `github.com/TheDataEngineX/dataenginex` | Public |
| `dex-studio` | `github.com/TheDataEngineX/dex-studio` | Public |
| `infradex` | `github.com/TheDataEngineX/infradex` | Public |
| `.github` | `github.com/TheDataEngineX/.github` | Public (org profile + shared workflows) |

- Container images: `ghcr.io/thedataenginex/dataenginex`, `ghcr.io/thedataenginex/dex-studio`
- PyPI: `pip install dataenginex` (already published, currently 0.8.x)
- GitHub Actions: reusable workflows in `.github` repo, CI/CD per repo

### Domain: dataenginex.org

| Subdomain | Purpose | Hosting |
|-----------|---------|---------|
| `dataenginex.org` | Landing page + project overview | Cloudflare Pages |
| `docs.dataenginex.org` | MkDocs Material documentation | Cloudflare Pages |
| `api.dataenginex.org` | Demo API (optional, Tier 2 VPS) | Hetzner VPS |
| `studio.dataenginex.org` | Demo Studio instance (optional) | Hetzner VPS |

- DNS + CDN via Cloudflare (free tier)
- Email: `admin@dataenginex.org` via Cloudflare Email Routing (free)
- SSL: automatic via Cloudflare (all subdomains) and Let's Encrypt (VPS)

---

## Success Criteria

1. `pip install dataenginex && dex init demo --template full-stack && dex serve --studio` works end-to-end (first run may take longer due to model downloads if `[embeddings]` installed)
2. User can define a complete data → ML → AI pipeline in ONE `dex.yaml`
3. Zero external services required for laptop development (data + ML layers; AI retrieval needs `[embeddings]`)
4. `docker compose up` deploys the full platform on a VPS
5. All built-in backends pass the same conformance test suite as external backends
6. DEX Studio can create projects, trigger pipelines, train models, and chat with agents
7. Published on PyPI as `dataenginex` 1.0.0 with `[all]` extras bundle
8. 80%+ test coverage on new code, conformance tests for all backend interfaces
9. Container images published to `ghcr.io/thedataenginex/*`
10. Documentation live at `docs.dataenginex.org`
