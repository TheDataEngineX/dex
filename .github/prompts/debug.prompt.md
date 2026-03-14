---
description: "Structured debugging workflow for an issue"
tools: ["search/codebase", "execute/runInTerminal", "execute/getTerminalOutput", "read/terminalLastCommand", "read/terminalSelection"]
---

Debug the issue in or related to ${file}.

## Debugging workflow

1. **Understand** — Read the error message, traceback, or unexpected behavior description
2. **Locate** — Find the relevant source code and trace the execution path
3. **Hypothesize** — Form a theory about root cause based on:
   - Recent changes to the file or its dependencies
   - Error handling gaps (bare `except:`, swallowed errors)
   - Type mismatches (check with `poe typecheck`)
   - Missing validation at boundaries
4. **Verify** — Run targeted tests:
   - `poe test-unit` for unit tests
   - `poe test-integration` for API/integration tests
   - Check lint/type errors: `poe lint` and `poe typecheck`
5. **Fix** — Apply the minimal change that resolves the issue
   - Follow project error patterns from `src/dataenginex/api/errors.py`
   - Add structured logging for observability
   - Add a test that reproduces the bug (prevents regression)
6. **Validate** — Run `poe check-all` to confirm nothing else broke

## Project-specific debug tips
- API issues: check middleware order (logging → metrics → auth → rate limit)
- Auth issues: check `DEX_AUTH_ENABLED` and `DEX_JWT_SECRET` env vars
- Import errors: check for circular deps (use lazy imports in routers)
- Test failures: warnings are treated as errors (except uvicorn/websockets)
