# CLAUDE.md — DEX (dataenginex)

> Repo-specific context. Workspace-level rules, coding standards, and git conventions are in `../CLAUDE.md`.

## Project Overview

**DEX** — pure package repo for the `dataenginex` core framework.

| Package | Location | Purpose |
|---------|----------|---------|
| `dataenginex` | `src/dataenginex/` | Core framework (FastAPI, middleware, observability, quality gates, ML registry) |

**Stack:** Python 3.12+ · FastAPI · uv · Ruff · mypy strict · pytest · Docker · Kubernetes (ArgoCD)

**Version:** dataenginex 0.6.0

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

# Run
uv run poe dev            # Dev server (uvicorn reload, port 8000)
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
4. uv run python examples/02_api_quickstart.py  # Real server
   # Then curl: /health, /, /echo, /metrics
5. Import key classes standalone      # Verify modules work independently
```

**Tests passing ≠ app working. Step 4 is NON-NEGOTIABLE.**

______________________________________________________________________

## Architecture Patterns

### API

- Versioned routes: `/api/v1/`, `/api/v2/`
- `response_model=` on every FastAPI endpoint
- Lifespan: request logging → metrics → auth → rate limit
- Auth: pure-Python HS256 JWT (no pyjwt dependency)

### Data

- Medallion architecture: Bronze → Silver → Gold
- Airflow DAGs for orchestration
- PySpark for transforms
- `SchemaRegistry`, `DataCatalog`, data contracts via Pydantic

### ML

- Model lifecycle: development → staging → production → archived
- `ModelRegistry` (JSON-persisted)
- Drift detection: PSI-based
- PySpark ML pipelines — see `examples/08_spark_ml.py`

### Infrastructure

- Docker: multi-stage, Python 3.12-slim, non-root `dex` user
- Kubernetes: Kustomize base + overlays (dev, prod)
- ArgoCD GitOps: `dev` → dex-dev, `main` → dex

______________________________________________________________________

## Key Files

| File | Purpose |
|------|---------|
| `pyproject.toml` | Package config (dataenginex 0.6.0) |
| `poe_tasks.toml` | All poe task definitions |
| `src/dataenginex/` | Framework source |
| `examples/` | Runnable examples (01–10) |
| `tests/` | All tests (unit + integration) |
| `tasks/todo.md` | Task tracker — plan here first |
| `tasks/lessons.md` | Lessons learned — update after corrections |
| `tasks/findings.md` | Research log — decisions, dead ends, context |
| `.github/CHECKLISTS.md` | Code review checklists |
| `TODO.md` | Project-level task board |

______________________________________________________________________

## Framework API Endpoints

Run `uv run poe dev` to start the example server.

- `GET /` — Root
- `POST /echo` — Echo endpoint
- `GET /health` — Health check
- `GET /metrics` — Prometheus metrics
