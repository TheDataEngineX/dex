---
description: "Create a new FastAPI endpoint with models and tests"
tools: ["search/codebase", "execute/runInTerminal", "execute/getTerminalOutput", "read/terminalLastCommand", "read/terminalSelection"]
---

Create a new FastAPI endpoint for the DataEngineX project.

## Requirements

1. **Route** — Add the endpoint in `src/careerdex/api/routers/v1.py` (or create a new router)
   - Use `@router.get`, `@router.post`, etc. with `response_model=`
   - Follow existing patterns in that file (lazy imports, structlog logging)
   - Use `structlog.get_logger(__name__)` for logging

2. **Models** — Add Pydantic request/response models in `packages/dataenginex/src/dataenginex/core/schemas.py`
   - Include `model_config = {"json_schema_extra": {"examples": [...]}}`
   - Use `from __future__ import annotations` at top of file

3. **Error Handling** — Use project error classes from `packages/dataenginex/src/dataenginex/api/errors.py`
   - `BadRequestError`, `NotFoundError`, `ServiceUnavailableError`
   - Never use bare `except:`

4. **Tests** — Add tests in `tests/unit/`
   - Use `TestClient` from Starlette for sync tests
   - Test happy path, validation errors, edge cases
   - Group in a `Test<Endpoint>` class

5. **Verify** — Run `poe check-all` to confirm lint + typecheck + tests pass

Refer to existing endpoints in `src/careerdex/api/routers/v1.py` for patterns.
