# DataEngineX — Copilot Instructions

Be pragmatic, straight forward and challenge my ideas. Question my assumptions, point out the blank spots and highlight opportunity costs. No sugarcoating. No pandering. No bias. No Both siding. No Retro Active Reasoning. If it is an issue/bug/problem find the root problem and suggest a solution don't skip or bypass it.

These standards apply to **all code** across the DataEngineX project.
Domain-specific guidance lives in [instructions/](instructions/) — loaded automatically by file path.

---

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

---

## Task Management

1. **Plan First**: Write plan to `tasks/todo.md` with checkable items
2. **Verify Plan**: Check in before starting implementation
3. **Track Progress**: Mark items complete as you go
4. **Explain Changes**: High-level summary at each step
5. **Document Results**: Add review section to `tasks/todo.md`
6. **Capture Lessons**: Update `tasks/lessons.md` after corrections
7. **Log Research**: Record findings, dead ends, and decisions in `tasks/findings.md`

---

## Core Principles

- **Simplicity First**: Make every change as simple as possible. Impact minimal code.
- **No Laziness**: Find root causes. No temporary fixes. Senior developer standards.
- **Minimal Impact**: Changes should only touch what's necessary. Avoid introducing bugs.

---

## Project Overview

**DEX (DataEngineX)** — data engineering and ML platform.
- `dataenginex` — Core framework (FastAPI optional via `[api]` extra, middleware, observability, quality gates, ML lifecycle)

**Stack:** Python 3.12+ | FastAPI | uv | Ruff | mypy strict | pytest | Docker | Kubernetes (ArgoCD)

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
- `mypy --strict` on `src/dataenginex/` only (all packages use mypy strict)
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

**After generating code:** run the full validation pipeline in this exact order:

1. **Lint:** `uv run poe lint` (or `uv run python -m ruff check src/ tests/`)
2. **Typecheck:** `uv run poe typecheck` (or `uv run python -m mypy src/dataenginex/ --strict`)
3. **Unit tests:** `uv run poe test` (or `uv run python -m pytest tests/ -x --tb=short -q`)
4. **Run the real app:** Start the server with `uv run python examples/02_api_quickstart.py` and verify:
   - Health probes: `curl http://localhost:8000/health`, `/ready`, `/startup`
   - Existing endpoints still work: `/`, `/echo`, `/api/v1/data/sources`, `/api/v1/system/config`
   - New/changed endpoints respond with correct data (not just 200 OK — check response bodies)
   - Metrics endpoint: `curl http://localhost:8000/metrics`
   - OpenAPI spec includes all routes: `curl http://localhost:8000/openapi.json`
5. **Standalone module validation:** Import and run key classes outside the API to verify they work independently (not just through endpoints)

Tests and lint passing is necessary but NOT sufficient. The real app must boot, serve requests, and return correct data. Never skip step 4.

**Before submitting PRs:** Update/remove all the files in the entire project whether they are affeted or not. This is to ensure that the codebase is consistent and up to date with the latest changes. Bumping up versions.This includes code, tests, workflows, configs, documentation, all files in .github folder, comments, and any relevant files that may be impacted by the changes made in the PR.
