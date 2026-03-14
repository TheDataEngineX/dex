---
applyTo: "src/**/*.py"
---

# Python — Project Specifics

## Style (Ruff: E, F, I, B, UP, SIM, C90 — max complexity 8)
- Line length: 100 | `snake_case` functions/vars | `PascalCase` classes | `StrEnum` for enums
- `from __future__ import annotations` in all source files
- Imports: stdlib → third-party → local (auto-sorted by ruff)
- Run `poe check-all` (lint + typecheck + test) before committing
- `mypy --strict` covers `src/dataenginex/` only — all packages use mypy strict

## Logging — Dual Stack
- API/middleware: `logger = structlog.get_logger(__name__)` → `logger.info("event", key=value)`
- ML/backend: `from loguru import logger` → `logger.info("message %s", arg)`
- `X-Request-ID` propagated via `structlog.contextvars`
- stdlib `logging` is intercepted → loguru (never use it directly)

## Key Patterns
- Pydantic: centralized in `src/dataenginex/core/schemas.py` with `model_config = {"json_schema_extra": {"examples": [...]}}`
- Config: `python-dotenv` | Key env vars: `LOG_LEVEL`, `LOG_FORMAT`, `DEX_AUTH_ENABLED`, `DEX_JWT_SECRET`
- Error hierarchy: `APIHTTPException` → `BadRequestError`, `NotFoundError`, `ServiceUnavailableError`
- Validators: `src/dataenginex/core/validators.py`
- Observability: `src/dataenginex/middleware/`
