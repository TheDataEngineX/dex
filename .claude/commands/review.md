Review the current changes (staged and unstaged) against DEX project standards.

Steps:

1. Run `git diff` and `git diff --staged` to see all changes
1. Check against `.github/CHECKLISTS.md` review criteria
1. Verify each changed file follows its domain-specific instructions:
   - `src/**/api/**/*.py` → fastapi.instructions.md
   - `src/careerdex/**/*.py` → data-pipelines.instructions.md
   - `src/**/ml/**/*.py` → ml.instructions.md
   - `src/**/*.py` → python.instructions.md
   - `tests/**/*.py` → testing.instructions.md
   - `.github/workflows/**` → workflows.instructions.md
   - `infra/**/*` → infrastructure.instructions.md

Review priorities:

1. **Security** — No hardcoded secrets, parameterized queries, no PII in logs
1. **Correctness** — Specific exceptions, error context, type safety
1. **Testing** — Tests exist for new code, 80%+ coverage
1. **Standards** — Type hints, structured logging, docstrings on public APIs

Flag any red flags from CLAUDE.md. Be direct — no sugarcoating.
