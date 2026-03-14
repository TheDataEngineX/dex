---
description: "Fix all lint, type, and formatting errors"
tools: ["search/codebase", "execute/runInTerminal", "execute/getTerminalOutput", "read/terminalLastCommand", "read/terminalSelection"]
---

Fix all lint, type-checking, and formatting errors in the project.

## Steps

1. Run `uv run poe lint` — fix all ruff errors (rules: E, F, I, B, UP, SIM, C90)
2. Run `uv run poe lint-fix` — apply Ruff auto-fixes/formatting (line length 100)
3. Run `uv run poe typecheck` — fix mypy strict errors in `src/dataenginex/`
4. Run `uv run poe check-all` — confirm everything passes together

## Common fixes

- Missing `from __future__ import annotations`
- Missing type hints on public functions
- Unused imports (F401) — remove them
- Unsorted imports (I001) — let ruff auto-sort
- Bare `except:` (E722) — catch specific exceptions
- f-string in logging (G004) — use structured key-value pairs
- Complexity > 8 (C901) — break function into smaller pieces
