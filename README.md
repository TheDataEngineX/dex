# DataEngineX

[![CI](https://github.com/TheDataEngineX/dataenginex/actions/workflows/ci.yml/badge.svg?branch=dev)](https://github.com/TheDataEngineX/dataenginex/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/dataenginex)](https://pypi.org/project/dataenginex/)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Unified Data + ML + AI framework. One `dex.yaml` defines your entire pipeline — from data ingestion through ML training to AI agents. Self-hosted, config-driven, production-ready.

______________________________________________________________________

## Quick Start

```bash
pip install dataenginex
dex init my-project --template full-stack
dex validate dex.yaml
dex serve
```

```bash
# Development
git clone https://github.com/TheDataEngineX/dataenginex && cd dataenginex
uv sync
uv run poe check-all          # lint + typecheck + tests
uv run poe dev                 # dev server on http://localhost:17000
```

______________________________________________________________________

## What It Does

```
dex.yaml
  ├── data:       CSV/Parquet/DuckDB → transforms → quality checks
  ├── ml:         Experiment tracking → training → serving → drift detection
  ├── ai:         LLM providers → retrieval (BM25/dense/hybrid) → agents
  ├── server:     FastAPI with auth, metrics, rate limiting
  └── observability: structlog + Prometheus metrics + tracing
```

**Opinionated defaults, swappable backends.** Everything works out of the box with built-in implementations. Swap any layer for industry tools via extras:

```bash
pip install dataenginex[dagster]     # Dagster orchestration
pip install dataenginex[mlflow]      # MLflow tracking
pip install dataenginex[agents]      # LangGraph agent runtime
pip install dataenginex[vectors]     # Qdrant/LanceDB vector stores
pip install dataenginex[embeddings]  # sentence-transformers + ONNX
pip install dataenginex[spark]       # PySpark transforms
pip install dataenginex[all]         # Everything
```

______________________________________________________________________

## Project Structure

```
dataenginex/
├── src/dataenginex/
│   ├── cli/                # dex CLI (validate, version, init, serve)
│   ├── config/             # dex.yaml schema, loader, env var resolution
│   ├── core/               # Exceptions, interfaces (10 Base* ABCs), registry
│   ├── api/                # FastAPI app, auth (JWT), rate limiting, health
│   ├── data/               # Connectors, schema registry, profiler
│   ├── ml/                 # Training, model registry, serving, drift
│   ├── middleware/         # Structured logging, Prometheus metrics, tracing
│   ├── lakehouse/          # Catalog, partitioning, storage
│   ├── warehouse/          # SQL/Spark transforms, lineage
│   └── plugins/            # Plugin system (entry-point discovery)
│
├── examples/               # Runnable examples + dex.yaml
├── tests/                  # Unit + integration tests
├── docs/                   # MkDocs documentation
└── pyproject.toml          # Package config (version source of truth)
```

______________________________________________________________________

## Architecture

**Config-Driven Pipeline:**

```
dex.yaml → load + validate → register backends → execute pipeline
                                    │
              ┌─────────────────────┼─────────────────────┐
              │                     │                     │
         Data Layer            ML Layer             AI Layer
     (DuckDB built-in)    (builtin tracker)    (Ollama + DuckDB)
     (Dagster extra)       (MLflow extra)      (LangGraph extra)
```

**Backend Registry Pattern:** Every subsystem has a `Base*` ABC + `BackendRegistry`. Built-in backends implement the ABC. Extras implement the same interface. Conformance tests verify both.

**Tech Stack:**

| Layer | Built-in | Optional Extra |
|-------|----------|----------------|
| Data Engine | DuckDB | PySpark |
| Orchestration | croniter scheduler | Dagster |
| ML Tracking | JSON-based tracker | MLflow |
| Model Serving | Built-in HTTP | BentoML |
| LLM | Ollama / LiteLLM | Any OpenAI-compatible |
| Vector Store | DuckDB VSS | Qdrant, LanceDB |
| Retrieval | BM25 + Dense + Hybrid | ColBERT (RAGatouille) |
| API | FastAPI + Uvicorn | — |
| Logging | structlog | — |

______________________________________________________________________

## Development

See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) for full setup.

```bash
uv run poe check-all         # lint + typecheck + tests
uv run poe lint-fix          # auto-fix lint issues
uv run poe dev               # dev server with hot-reload (port 17000)
uv run poe test-cov          # tests + coverage report
```

______________________________________________________________________

## Documentation

| Guide | Description |
|-------|-------------|
| [Docs Hub](docs/docs-hub.md) | Complete index |
| [Architecture](docs/ARCHITECTURE.md) | System design |
| [Development](docs/DEVELOPMENT.md) | Local setup and workflow |
| [Contributing](docs/CONTRIBUTING.md) | Code style and PR process |
| [API Reference](docs/api-reference/index.md) | Auto-generated module docs |

> Docs: [docs.dataenginex.org](https://docs.dataenginex.org) | Community standards at [org level](https://github.com/TheDataEngineX/.github)

______________________________________________________________________

## The DEX Ecosystem

```
TheDataEngineX/
├── dataenginex    — Core framework (this repo)
├── dex-studio     — Web UI (NiceGUI) — single pane of glass
└── infradex       — Terraform + Helm + K3s deployment
```

______________________________________________________________________

## License

MIT License. See [LICENSE](LICENSE).

______________________________________________________________________

**Version**: [![PyPI](https://img.shields.io/pypi/v/dataenginex)](https://pypi.org/project/dataenginex/) | **License**: MIT | **Python**: 3.12+ | **Docs**: [docs.dataenginex.org](https://docs.dataenginex.org)
