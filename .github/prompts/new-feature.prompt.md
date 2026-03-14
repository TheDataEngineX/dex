---
description: "Scaffold a complete feature with code, tests, and docs"
tools: ["search/codebase", "execute/runInTerminal", "execute/getTerminalOutput", "read/terminalLastCommand", "read/terminalSelection"]
---

Scaffold a new feature for the DataEngineX project.

## Workflow

1. **Plan** — Identify which module this belongs to in `src/dataenginex/`:
   - `api/` — health, auth, errors, pagination, rate limiting
   - `core/` — schemas, validators, medallion architecture, quality gates
   - `data/` — connectors, profiler, schema registry
   - `lakehouse/` — catalog, partitioning, storage
   - `middleware/` — logging, metrics, request logging, tracing
   - `ml/` — registry, training, drift, serving, LLM, vectorstore
   - `warehouse/` — transforms, lineage

2. **Implement** — Create the feature code:
   - `from __future__ import annotations` at top of every file
   - Type hints on all public functions (params + return)
   - Structured logging (structlog for API, loguru for ML/backend)
   - Error handling with specific exceptions and context
   - Docstrings on public functions/classes

3. **Models** — If API-facing, add Pydantic models in `src/dataenginex/core/schemas.py`

4. **Tests** — Write tests in `tests/unit/test_<module>.py`:
   - Happy path, error paths, edge cases
   - Use `TestClient` for API, `tmp_path` for files
   - Group in `Test<Feature>` classes
   - No `@pytest.mark.asyncio` needed (auto mode)

5. **Validate**:
   - `poe check-all` — lint + typecheck + tests
   - `poe test-cov` — verify 80%+ coverage maintained

6. **Commit** — Use conventional commit: `feat: <description> (#issue)`

## Quality gates
- No hardcoded secrets
- No bare `except:`
- Functions under 50 lines, max 4 params
- No `print()` or stdlib `logging`
