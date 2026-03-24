# CLAUDE.md — DEX (dataenginex)

Brief answers only. No explanations unless asked.
Goal is to save Claude code tokens for lower cost without loosing quality.

> Repo-specific context. Workspace-level rules, coding standards, and git conventions are in `../CLAUDE.md`.

## Project Overview

**DEX** — unified Data + ML + AI framework. Config-driven, self-hosted, production-ready.

| Package | Location | Purpose |
|---------|----------|---------|
| `dataenginex` | `src/dataenginex/` | Core framework — config system, backend registry, CLI, API, ML, AI agents |

**Stack:** Python 3.13+ · FastAPI · DuckDB · structlog · Pydantic · Click · Rich · uv · Ruff · mypy strict · pytest

**Version:** `uv run poe version`

**Domain:** thedataenginex.org | **Org:** github.com/TheDataEngineX

______________________________________________________________________

## Build & Run Commands

```bash
# Quality
uv run poe lint           # Ruff lint
uv run poe lint-fix       # Ruff lint + auto-fix
uv run poe typecheck      # mypy --strict (src/dataenginex/ only)
uv run poe check-all      # lint + typecheck + test

# Test
uv run poe test           # All tests
uv run poe test-unit      # Unit tests only
uv run poe test-integration  # Integration tests only
uv run poe test-cov       # Tests with coverage

# CLI
dex validate dex.yaml     # Validate config file
dex version               # Show version + environment

# Run
uv run poe dev            # Dev server (uvicorn reload, port 17000)
uv run poe docker-up      # Docker compose up
uv run poe docker-down    # Docker compose down

# Deps
uv run poe uv-sync        # Sync deps from lockfile
uv run poe uv-lock        # Regenerate lockfile
uv run poe security       # Audit deps for vulnerabilities
```

______________________________________________________________________

## Mandatory Validation Pipeline

Run in this exact order after ANY code change:

```bash
1. uv run poe lint                    # Ruff lint
2. uv run poe typecheck              # mypy --strict
3. uv run poe test                   # pytest
4. uv run dex validate examples/dex.yaml  # Config validation
5. uv run python examples/02_api_quickstart.py  # Real server
   # Then curl: /health, /, /echo, /metrics
6. Import key classes standalone      # Verify modules work independently
```

**Tests passing ≠ app working. Steps 4-5 are NON-NEGOTIABLE.**

______________________________________________________________________

## Architecture Patterns

### Config System (`dex.yaml`)

- Single YAML defines entire Data + ML + AI pipeline
- Pydantic models in `src/dataenginex/config/schema.py`
- Env var resolution: `${VAR:-default}` syntax
- Config layering: base + overlay (e.g. `dex.prod.yaml`)
- Cross-reference validation (pipeline sources, dependencies)

### Backend Registry

- Every subsystem has a `Base*` ABC in `core/interfaces.py`
- `BackendRegistry[T]` in `core/registry.py` discovers and registers implementations
- Built-in backends work out of the box; extras implement same interface
- Conformance test suites verify both built-in and extra backends

### API

- Versioned routes: `/api/v1/`, `/api/v2/`
- `response_model=` on every FastAPI endpoint
- Lifespan: request logging → metrics → auth → rate limit
- Auth: pure-Python HS256 JWT (no pyjwt dependency)

### Data

- DuckDB as default engine (built-in, zero config)
- Medallion architecture: Bronze → Silver → Gold
- PySpark available via `[spark]` extra
- `SchemaRegistry`, `DataCatalog`, data contracts via Pydantic

### ML

- Model lifecycle: development → staging → production → archived
- Built-in JSON tracker (MLflow via `[mlflow]` extra)
- Drift detection: PSI-based
- Feature store interface

### AI

- LLM: Ollama/LiteLLM (default), any OpenAI-compatible provider
- Retrieval: BM25 + Dense + Hybrid + Reranking
- Vector store: DuckDB VSS (built-in), Qdrant/LanceDB via extras
- Agent runtime: built-in or LangGraph via `[agents]` extra

### Logging

- **structlog only** — no loguru, no print()
- Structured JSON logging in production, human-readable in dev

### Infrastructure

- Docker: multi-stage, Python 3.13-slim, non-root `dex` user
- Container images: `ghcr.io/thedataenginex/dex`
- Kubernetes: Kustomize base + overlays (dev, prod)
- ArgoCD GitOps: `dev` → dex-dev, `main` → dex

______________________________________________________________________

## Key Files

| File | Purpose |
|------|---------|
| `pyproject.toml` | Package config (version source of truth) |
| `poe_tasks.toml` | All poe task definitions |
| `src/dataenginex/config/` | Config schema, loader, defaults |
| `src/dataenginex/core/` | Exceptions, interfaces (ABCs), registry |
| `src/dataenginex/cli/` | `dex` CLI entry point |
| `examples/dex.yaml` | Example full-stack config |
| `examples/` | Runnable examples (01–10) |
| `tests/` | All tests (unit + integration) |
| `tasks/todo.md` | Task tracker — plan here first |
| `tasks/lessons.md` | Lessons learned — update after corrections |
| `tasks/findings.md` | Research log — decisions, dead ends, context |
| `docs/superpowers/specs/` | System redesign spec |
| `TODO.md` | Project-level task board |

______________________________________________________________________

## Framework API Endpoints

Run `uv run poe dev` to start the example server on port 17000.

- `GET /` — Root
- `POST /echo` — Echo endpoint
- `GET /health` — Health check
- `GET /metrics` — Prometheus metrics

______________________________________________________________________

## Ecosystem (3 repos)

```
TheDataEngineX/
├── dataenginex    — Core framework (this repo) — PyPI: dataenginex
├── dex-studio     — Web UI (NiceGUI) — single pane of glass
└── infradex       — Terraform + Helm + K3s deployment
```
