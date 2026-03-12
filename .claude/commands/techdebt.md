Scan the codebase for tech debt and report findings organized by severity.

Search for:
- `TODO`, `FIXME`, `HACK`, `XXX`, `NOQA` comments
- `NotImplementedError` stubs that should be implemented
- Bare `except:` blocks
- `print()` statements (should use structured logging)
- Functions over 50 lines or with more than 4 parameters
- Missing type hints on public functions
- Missing tests for existing modules
- Unused imports or dead code
- Hardcoded values that should be config/env vars
- Deprecated patterns flagged by Ruff UP rules

Output a prioritized report:
1. **Critical** — Security issues, bare excepts, hardcoded secrets
2. **High** — Missing tests, unimplemented stubs, broken patterns
3. **Medium** — TODOs, missing type hints, code complexity
4. **Low** — Style issues, documentation gaps

Include file paths, line numbers, and suggested fixes.
