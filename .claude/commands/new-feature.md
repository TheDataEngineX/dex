Scaffold a new feature for the DEX project. Ask me for the feature name and description if not provided as an argument.

Steps:
1. **Plan** — Write the implementation plan to `tasks/todo.md` with checkable items
2. **Explore** — Search the codebase for related patterns, existing code to build on
3. **Design** — Identify which package this belongs to (dataenginex, careerdex, or weatherdex)
4. **Implement** — Follow existing patterns in the target package:
   - API endpoint → `src/careerdex/api/routers/` with `response_model=`, type hints
   - Data pipeline → Medallion pattern (Bronze → Silver → Gold)
   - ML feature → Model lifecycle pattern with `ModelRegistry`
   - Framework util → `packages/dataenginex/src/dataenginex/`
5. **Test** — Write tests in `tests/unit/` and/or `tests/integration/`
6. **Validate** — Run `/validate` to verify everything works
7. **Update** — Mark items complete in `tasks/todo.md`, update `TODO.md` if relevant

Follow all coding standards from CLAUDE.md. Include type hints, structured logging, error handling.
