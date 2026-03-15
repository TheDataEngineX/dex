# New Feature (DEX)

Scaffold a new feature for the `dataenginex` core framework. Ask for the feature name and description if not provided as $ARGUMENTS.

Steps:

1. **Plan** — Write the implementation plan to `tasks/todo.md`. Check in before implementing.
1. **Explore** — Search `src/dataenginex/` for related patterns. Use Context7 MCP for library docs.
1. **Design** — Identify the right module:
   - API endpoint → `src/dataenginex/api/` — `response_model=` required, type hints, auth via lifespan middleware
   - Middleware → `src/dataenginex/middleware/` — follows request logging → metrics → auth → rate limit order
   - Data pipeline → Medallion pattern (bronze → silver → gold) via `SchemaRegistry` / `DataCatalog`
   - ML feature → `src/dataenginex/ml/` — `ModelRegistry` lifecycle (development → staging → production → archived)
   - Quality gate → `src/dataenginex/quality/`
   - Plugin hook → `src/dataenginex/plugins/` — entry-point based discovery
   - Framework util → `src/dataenginex/core/`
1. **Implement** — Follow existing patterns. `from __future__ import annotations` at top. structlog for API/middleware, loguru for ML/backend. No `print()`.
1. **Test** — Unit tests in `tests/unit/`, integration tests in `tests/integration/` (live uvicorn). `asyncio_mode = "auto"` — no `@pytest.mark.asyncio` needed.
1. **Validate** — Run `/validate` (dex version — includes real server step)
1. **Update** — Mark complete in `tasks/todo.md`; update `TODO.md` if relevant

Follow all standards in `CLAUDE.md` and `../CLAUDE.md`.
