# CLAUDE.md — DEX (dataenginex)

Brief answers only. No explanations unless asked.
Goal is to save Claude code tokens for lower cost without loosing quality.

> Repo-specific context. Workspace-level rules, coding standards, and git conventions are in `../CLAUDE.md`.

## Project Overview

**DEX** — unified Data + ML + AI framework. Config-driven, self-hosted, production-ready.

| Package | Location | Purpose |
|---------|----------|---------|
| `dataenginex` | `src/dataenginex/` | Core framework — config, registry, CLI, API, ML, AI (routing, runtime, memory, observability, workflows) |

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

## Mandatory Validation

Run `/validate` after ANY code change. Steps 4-5 (config validation + server smoke test) are NON-NEGOTIABLE.
Tests passing ≠ app working.
