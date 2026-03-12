# DEX Lessons Learned

> Self-improvement log. After any correction, mistake, or insight — record it here.
> Agent reviews this at session start to avoid repeating mistakes.

---

## Enforced Instincts

> These are NOT suggestions. These are rules that MUST be followed every time.
> Violations of these rules should trigger immediate self-correction.

1. **Always run the real app** — Tests + lint passing is NOT sufficient. `curl` the endpoints.
2. **Never return fake data** — Unimplemented code raises `NotImplementedError`, never returns constants.
3. **Grep after migrations** — After any rename/move, grep the entire codebase for stale references.
4. **Lock after pyproject changes** — Run `uv lock && uv sync` after ANY pyproject.toml change.
5. **Log findings** — Record research, dead ends, and decisions in `tasks/findings.md`.
6. **Fresh context for complex tasks** — Use subagents to avoid context rot on multi-step work.
7. **Use Context7 for library docs** — Add `use context7` to prompts involving FastAPI, PySpark, Pydantic, etc.
8. **Use llmfit before pulling models** — Run `llmfit recommend --json --use-case <use-case>` before `ollama pull`.

---

## Patterns & Anti-Patterns

### Do This
- Always run the real app (step 4) — tests + lint alone are NOT sufficient
- Use `NotImplementedError` with descriptive messages for stubs, not fake/fallback data
- Structured logging: `logger.info("event", key=value)` — never f-strings in log calls
- When cleaning domain refs, check docstrings and comments too — not just code
- After moving files between packages, run `uv lock && uv sync` before validation
- Grep for the old pattern after any rename/migration to catch stragglers

### Don't Do This
- Don't return fake/constant data from unimplemented endpoints — fail loud
- Don't leave domain-specific examples (JobPosting, salary_min) in generic framework code
- Don't skip `uv lock` after changing pyproject.toml — stale lockfile breaks CI
- Don't assume tests passing = working app — curl the actual endpoints
- Don't silently swallow exceptions — always re-raise with context

---

## Corrections Log

<!-- Format: date | what went wrong | lesson -->

| Date | Issue | Lesson |
|------|-------|--------|
| 2026-03-06 | Domain references persisted in dataenginex docstrings after code migration | Always grep both code AND comments/docstrings when cleaning up after migrations |
| 2026-03-06 | Import sorting errors (I001) after moving router files | After moving imports between packages, always run `uv run poe lint-fix` before manual lint check |
| 2026-03-05 | Constant/fallback values masked missing implementations | Stubs should raise `NotImplementedError` with actionable message, never return plausible fake data |
| 2026-03-05 | CareerDEX schemas lived in generic dataenginex package | Domain models belong in the application package, not the framework — enforce package boundaries |

---

## Version History

| Date | Root Version | dataenginex Version | Key Change |
|------|-------------|--------------------:|------------|
| 2026-03-07 | 0.5.0 | 0.6.0 | Python 3.12, FastAPI optional, routers migrated |
| 2026-03-05 | 0.4.0 | 0.6.0 | Domain extraction, RAG/LLM modules, constant cleanup |
