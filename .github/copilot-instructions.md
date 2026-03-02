# DataEngineX — Copilot Instructions

Be pragmatic , straight forward and challenge my ideas. Question my assumptions , point out the blank spots and highlight opportunity costs. No sugarcoating. No pandering. No bias. No Both siding. No Retro Active Reasoning. If it is an issues/bug/problem find the root problem and suggest a solution don't skip or bypass it.

These standards apply to **all code** across the DataEngineX project.
Domain-specific guidance lives in [instructions/](instructions/) — loaded automatically by file path.

---

## Project Overview

**DEX (DataEngineX)** — data engineering and ML platform with three packages:
- `dataenginex` — Core API framework (FastAPI, middleware, observability)
- `careerdex` — Job data platform (Airflow DAGs, data models)
- `weatherdex` — Weather pipeline (PySpark ML, notebooks)

**Stack:** Python 3.11+ | FastAPI | uv | Ruff | mypy strict | pytest | Docker | Kubernetes (ArgoCD)

**Build:** `hatchling` backend + `uv` package manager | Dep groups: `dev`, `data` (PySpark/Airflow), `notebook`

**Commands:**
- Quality: `uv run poe lint` | `uv run poe lint-fix` | `uv run poe typecheck` | `uv run poe check-all`
- Test: `uv run poe test` | `uv run poe test-unit` | `uv run poe test-integration` | `uv run poe test-cov`
- Run: `uv run poe dev` | `uv run poe docker-up` | `uv run poe docker-down`
- Deps: `uv run poe install` | `uv run poe security` | `uv run poe uv-sync` | `uv run poe uv-lock`

---

## Core Principles

### 1. Security 🔒
- Never hardcode secrets, API keys, passwords, tokens
- Validate all inputs at system boundaries
- Parameterized queries only (never concatenate SQL)
- Never log PII, credentials, or sensitive data

### 2. Clarity 📖
- Single responsibility — one function does one thing
- Functions under 50 lines, max 4 parameters
- Clear naming (no `x`, `temp`, `data`)
- Comments explain "why", not "what"

### 3. Error Handling 🛡️
- Catch specific exceptions, never bare `except:`
- Log errors with full context (structured key-value pairs)
- Re-raise with context, never silently swallow

### 4. Testing 🧪
- Write tests alongside code — 80%+ coverage target
- Tests are independent, use Arrange-Act-Assert
- Mock external services, not code under test
- Cover edge cases: empty, None, boundary, error paths

### 5. Type Safety 🏷️
- Type hints on all public functions (params + return)
- `mypy --strict` on `packages/dataenginex/src/dataenginex/` only (careerdex/weatherdex not yet covered)
- Validate input at API boundaries (Pydantic)
- Use `from __future__ import annotations` in all source files

### 6. Observability 📊
- `loguru` + `structlog` — never `print()` or stdlib `logging`
- API/middleware: `structlog.get_logger(__name__)` with `logger.info("event", key=value)`
- ML/backend: `from loguru import logger` with `logger.info("message %s", arg)`
- Prometheus metrics (`http_` prefix) + OpenTelemetry tracing

### 7. Dependencies 📦
- `uv` only (never raw pip) — pin with minimum version bounds
- Dev deps in `[dependency-groups]` — run `poe security` to audit

### 8. Compatibility 🔄
- API changes backwards compatible within major version
- Deprecate before removing — version via `/api/v1/`, `/api/v2/`

### 9. Git 🌿
- Branches: `main` (prod), `dev` (integration), `feature/<desc>` or `fix/<desc>`
- Branch-based deployment: `dev` → dex-dev, `main` → dex
- Conventional commits: `feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, `test:`
- Reference issues: `feat: add drift detection (#42)`

---

## Red Flags 🚨

- Hardcoded secrets or `pickle.loads` on untrusted data
- Bare `except:`, silent error swallowing, missing error context
- N+1 queries, unbounded result sets, full datasets in memory
- New feature with no tests, or tests that depend on each other
- API contract changes without versioning

---

## For AI Agents 🤖

1. Check [instructions/](instructions/) for domain-specific guidance by file path
2. Reference [CHECKLISTS.md](CHECKLISTS.md) for review checklists
3. Match existing patterns in [src/](../src/) and [tests/](../tests/)
4. Config: [pyproject.toml](../pyproject.toml) | [poe_tasks.toml](../poe_tasks.toml) | [.pre-commit-config.yaml](../.pre-commit-config.yaml)

**When generating code:** include type hints, docstrings, error handling, and tests. Use structured logging (key-value pairs, not f-strings). Create/use images, design diagrams wherever required.

**After generating code:** run `uv run poe lint`, `uv run poe typecheck`, and `uv run poe test` to validate. Fix any issues before submitting PRs.

**Before submitting PRs:** Update/remove all the files in the entire project whether they are affeted or not. This is to ensure that the codebase is consistent and up to date with the latest changes. Bumping up versions.This includes code, tests, workflows, configs, documentation, all files in .github folder, comments, and any relevant files that may be impacted by the changes made in the PR.
