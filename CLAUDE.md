# CLAUDE.md — DataEngineX (DEX) Project Context

> This file is automatically loaded by Claude Code at session start.
> It provides project context, coding standards, and rules to follow.

Be pragmatic, straight forward and challenge my ideas. Question my assumptions, point out the blank spots and highlight opportunity costs. No sugarcoating. No pandering. No bias. No both siding. No retro active reasoning. If it is an issue/bug/problem find the root problem and suggest a solution — don't skip or bypass it.

______________________________________________________________________

## Workflow Orchestration

### 1. Plan First

- Enter plan mode for ANY non-trivial task (3+ steps or architectural decisions)
- If something goes sideways, STOP and re-plan immediately — don't keep pushing
- Write plan to `tasks/todo.md` with checkable items before starting implementation
- Write detailed specs upfront to reduce ambiguity

### 2. Subagent Strategy

- Use subagents liberally to keep main context window clean
- Offload research, exploration, and parallel analysis to subagents
- For complex problems, throw more compute at it via subagents
- One task per subagent for focused execution
- Wave execution: group independent tasks in parallel waves, sequence dependent ones

### 3. Self-Improvement Loop

- After ANY correction from the user: update `tasks/lessons.md` with the pattern
- Write rules for yourself that prevent the same mistake
- Ruthlessly iterate on these lessons until mistake rate drops
- Review lessons at session start for the relevant project
- Log research findings, dead ends, and architectural decisions to `tasks/findings.md`

### 4. Verification Before Done

- Never mark a task complete without proving it works
- Diff behavior between main and your changes when relevant
- Ask yourself: "Would a staff engineer approve this?"
- Run tests, check logs, demonstrate correctness

### 5. Demand Elegance (Balanced)

- For non-trivial changes: pause and ask "is there a more elegant way?"
- If a fix feels hacky: "Knowing everything I know now, implement the elegant solution"
- Skip this for simple, obvious fixes — don't over-engineer
- Challenge your own work before presenting it

### 6. Autonomous Bug Fixing

- When given a bug report: just fix it. Don't ask for hand-holding
- Point at logs, errors, failing tests — then resolve them
- Zero context switching required from the user
- Go fix failing CI tests without being told how

______________________________________________________________________

## Task Management

1. **Plan First**: Write plan to `tasks/todo.md` with checkable items
1. **Verify Plan**: Check in before starting implementation
1. **Track Progress**: Mark items complete as you go
1. **Explain Changes**: High-level summary at each step
1. **Document Results**: Add review section to `tasks/todo.md`
1. **Capture Lessons**: Update `tasks/lessons.md` after corrections
1. **Log Research**: Record findings, dead ends, and decisions in `tasks/findings.md`

______________________________________________________________________

## Core Principles

- **Simplicity First**: Make every change as simple as possible. Impact minimal code.
- **No Laziness**: Find root causes. No temporary fixes. Senior developer standards.
- **Minimal Impact**: Changes should only touch what's necessary. Avoid introducing bugs.

______________________________________________________________________

## Project Overview

**DEX (DataEngineX)** — pure package repo for the `dataenginex` core framework:

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
uv run poe typecheck      # mypy --strict (dataenginex only)
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
uv run poe install        # Install all deps
uv run poe uv-sync        # Sync deps from lockfile
uv run poe uv-lock        # Regenerate lockfile
uv run poe security       # Audit deps for vulnerabilities
```

______________________________________________________________________

## Mandatory Validation Pipeline

Run in this exact order after ANY code change:

```bash
1. uv run poe lint                    # Ruff lint
2. uv run poe typecheck              # mypy --strict (dataenginex only)
3. uv run poe test                   # pytest
4. uv run python examples/02_api_quickstart.py  # Real server
   # Then curl: /health, /, /echo, /metrics
5. Import key classes standalone      # Verify modules work independently
```

**Tests passing ≠ app working. Step 4 is NON-NEGOTIABLE.**

______________________________________________________________________

## Coding Standards

### Style

- `from __future__ import annotations` in ALL source files
- Ruff rules: E, F, I, B, UP, SIM, C90 · line-length 100 · max complexity 8
- Functions: under 50 lines, max 4 parameters
- Clear naming (no `x`, `temp`, `data`)
- Comments explain "why", not "what"

### Type Safety

- Type hints on all public functions (params + return)
- `mypy --strict` on `src/dataenginex/` only
- Pydantic models for API boundaries
- Only `src/dataenginex/` is under mypy strict

### Logging — Dual Stack

- **API/middleware:** `structlog.get_logger(__name__)` with `logger.info("event", key=value)`
- **ML/backend:** `from loguru import logger` with `logger.info("message %s", arg)`
- **NEVER:** `print()`, stdlib `logging`, or f-strings in log calls

### Error Handling

- Catch specific exceptions, never bare `except:`
- Log errors with full context (structured key-value pairs)
- Re-raise with context, never silently swallow
- Stubs: `raise NotImplementedError("descriptive message")` — never fake data

### Testing

- 80%+ coverage target
- Arrange-Act-Assert pattern
- Mock external services, not code under test
- `asyncio_mode = "auto"` — no `@pytest.mark.asyncio` needed
- Test paths: `tests/unit/` (isolated) · `tests/integration/` (live uvicorn)

### Security

- Never hardcode secrets, API keys, passwords, tokens
- Parameterized queries only (never concatenate SQL)
- Never log PII, credentials, or sensitive data
- Validate all inputs at system boundaries (Pydantic)

### Observability

- Prometheus metrics with `http_` prefix
- OpenTelemetry tracing
- Structured logs (key-value pairs)

______________________________________________________________________

## Architecture Patterns

### API

- Versioned routes: `/api/v1/`, `/api/v2/`
- `response_model=` on every FastAPI endpoint
- Lifespan: request logging → metrics → auth → rate limit
- Auth: pure-Python HS256 JWT (no pyjwt dependency)
- Example entry point: `examples/02_api_quickstart.py`

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
- Monitoring: Prometheus + Grafana + AlertManager + Jaeger

______________________________________________________________________

## Git Conventions

- **Branches:** `main` (prod), `dev` (integration), `feature/<desc>`, `fix/<desc>`
- **Commits:** Conventional — `feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, `test:`
- **Reference issues:** `feat: add drift detection (#42)`
- **Deployment:** `dev` → dex-dev, `main` → dex

______________________________________________________________________

## Dependencies

- `uv` only — never raw pip
- Pin with minimum version bounds
- Dev deps in `[dependency-groups]`
- dataenginex core: pydantic, pyyaml, loguru, httpx, python-dotenv, prometheus-client
- dataenginex[api] extra: fastapi, uvicorn, structlog, python-json-logger, opentelemetry-\*, email-validator

______________________________________________________________________

## Red Flags 🚨

- Hardcoded secrets or `pickle.loads` on untrusted data
- Bare `except:`, silent error swallowing, missing error context
- N+1 queries, unbounded result sets, full datasets in memory
- New feature with no tests, or tests that depend on each other
- API contract changes without versioning
- Fake/constant data from unimplemented endpoints (use NotImplementedError)
- Domain models in framework package (belong in application)

______________________________________________________________________

## Workflow Rules

> Detailed orchestration rules are at the top of this file. Quick reference:

1. **Plan First** — Enter plan mode for any non-trivial task (3+ steps). Write plan to `tasks/todo.md`.
1. **Subagents** — Use liberally. One task per subagent. Keep main context clean.
1. **Self-Improvement** — After any correction, update `tasks/lessons.md` with the pattern.
1. **Verify Before Done** — Never mark complete without proving it works. Run the full 5-step pipeline.
1. **Demand Elegance** — For non-trivial changes, ask "is there a more elegant way?" Skip for simple fixes.
1. **Autonomous Bug Fixing** — Given a bug report, just fix it. Zero context switching from user.
1. **Simplicity First** — Make every change as simple as possible. Impact minimal code.
1. **No Laziness** — Find root causes. No temporary fixes. Senior developer standards.

______________________________________________________________________

## Developer Tools

| Tool | Purpose | Usage |
|------|---------|-------|
| `llmfit` | Right-size LLM models to hardware | `llmfit recommend --json --use-case coding --limit 5` |
| Context7 MCP | Up-to-date library docs in LLM context | Add `use context7` to prompts for FastAPI, PySpark, etc. |

**Local LLM (Ollama):** System has 15.5 GB RAM + Quadro T2000 (4 GB VRAM). Use MoE models (Qwen3-Coder-30B-A3B at Q4_K_M) — dense models >8B will swap-thrash. Run `llmfit` before pulling new models.

**Context7 Rule:** Always use Context7 MCP when needing library/API documentation, code generation, or setup steps for FastAPI, PySpark, Pydantic, Airflow, or any third-party library — without the user having to explicitly ask.

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

## Framework API Endpoints (example app)

Run `uv run poe dev` to start the quickstart example server.

- `GET /` — Root
- `POST /echo` — Echo endpoint
- `GET /health` — Health check
- `GET /metrics` — Prometheus metrics
