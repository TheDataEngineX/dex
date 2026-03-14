---
description: "Create a new FastAPI endpoint with models and tests"
tools: ["search/codebase", "execute/runInTerminal", "execute/getTerminalOutput", "read/terminalLastCommand", "read/terminalSelection"]
---

Create a new FastAPI endpoint for the DataEngineX project.

## Requirements

1. **Route** — Add the endpoint to your application router
   - Use `@router.get`, `@router.post`, etc. with `response_model=`
   - Use `structlog.get_logger(__name__)` for logging
   - Reference `examples/02_api_quickstart.py` for a minimal working app

2. **Models** — Add Pydantic request/response models in `src/dataenginex/core/schemas.py`
   - Include `model_config = {"json_schema_extra": {"examples": [...]}}`
   - Use `from __future__ import annotations` at top of file

3. **Error Handling** — Use project error classes from `src/dataenginex/api/errors.py`
   - `BadRequestError`, `NotFoundError`, `ServiceUnavailableError`
   - Never use bare `except:`

4. **Tests** — Add tests in `tests/unit/`
   - Use `TestClient` from Starlette for sync tests
   - Test happy path, validation errors, edge cases
   - Group in a `Test<Endpoint>` class

5. **Verify** — Run `poe check-all` to confirm lint + typecheck + tests pass
