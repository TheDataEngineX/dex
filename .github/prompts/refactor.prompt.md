---
description: "Refactor code following project patterns and best practices"
tools: ["search/codebase", "execute/runInTerminal", "execute/getTerminalOutput", "read/terminalLastCommand", "read/terminalSelection"]
---

Refactor the code in ${file} to improve quality while preserving behavior.

## Refactoring checklist

1. **Single responsibility** — Split functions doing multiple things
2. **Function size** — Keep under 50 lines, max 4 parameters
3. **Naming** — Replace vague names (`x`, `temp`, `data`) with descriptive ones
4. **Error handling** — Replace bare `except:` with specific exceptions + context
5. **Type safety** — Add missing type hints (params + return), add `from __future__ import annotations`
6. **Logging** — Replace `print()` / stdlib `logging` with structlog (API) or loguru (ML/backend)
7. **Duplication** — Extract shared logic into helpers in appropriate module

## Constraints

- Do NOT change external behavior or API contracts
- Run `poe check-all` after refactoring to verify lint + typecheck + tests pass
- If tests break, the refactoring is wrong — revert and try differently
- Follow existing patterns in `src/dataenginex/` for style reference
