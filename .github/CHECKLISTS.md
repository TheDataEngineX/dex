# Code Review Checklists by Domain

Quick reference checklists for common tasks. **Reference actual code patterns in the repository for detailed examples.**

---

## Python Code

**Before submitting:**
- [ ] Type hints on all public functions (parameters and return types)
- [ ] No hardcoded secrets, passwords, or API keys
- [ ] Tests written for new functionality (80%+ coverage target)
- [ ] Docstrings on public functions/classes
- [ ] Ran `uv run poe lint-fix` and `uv run poe lint` locally
- [ ] No bare `except:` clauses
- [ ] Specific exception types caught and logged

**Code review questions:**
- Does this function do one thing well?
- Are error messages helpful for debugging?
- Is sensitive data logged or exposed?
- Can this be tested independently?

**See examples:**
- Clean code patterns → [src/dataenginex/core/](../src/dataenginex/core/)
- Error handling → [src/dataenginex/api/](../src/dataenginex/api/)
- Tests → [tests/unit/](../tests/unit/)

---

## REST API Endpoints (FastAPI)

**Before submitting:**
- [ ] Endpoint has clear HTTP verb (GET, POST, PATCH, DELETE)
- [ ] Request/response models define shapes (Pydantic)
- [ ] Input validation on all user-provided data
- [ ] Authentication check on protected endpoints
- [ ] Specific status codes (200, 201, 400, 401, 403, 404, etc.)
- [ ] Errors return consistent format with code + message
- [ ] Docstring explains what endpoint does

**Code review questions:**
- Can a user access data they shouldn't?
- What happens if someone sends bad data?
- Are all required fields validated?
- Is the response schema documented?

**See examples:**
- API endpoints → [src/dataenginex/api/](../src/dataenginex/api/)
- Request models → [src/dataenginex/core/schemas.py](../src/dataenginex/core/schemas.py)
- Tests → [tests/integration/test_e2e_api.py](../tests/integration/test_e2e_api.py)

---

## Data Pipelines

**Before submitting:**
- [ ] Pipeline is idempotent (safe to rerun)
- [ ] Source data validated at entry point
- [ ] Transformation logic clear and testable
- [ ] Error handling: specific exceptions with context
- [ ] Logging includes what data was processed (counts, IDs)
- [ ] Documentation explains source → transform → destination
- [ ] Tests verify behavior with sample data

**Code review questions:**
- What happens if source data changes schema?
- Is late-arriving data handled?
- Can this pipeline be paused/resumed?
- What metrics would tell us if it failed silently?

**See examples:**
- Pipeline patterns → [examples/07_api_ingestion.py](../examples/07_api_ingestion.py)
- Data validation → [src/dataenginex/core/validators.py](../src/dataenginex/core/validators.py)
- Tests → [tests/unit/test_data.py](../tests/unit/test_data.py)

---

## Database & SQL

**Before submitting:**
- [ ] Queries use parameterized statements (not string concatenation)
- [ ] Appropriate indexes on frequently filtered columns
- [ ] No N+1 queries (use JOINs or eager loading)
- [ ] Migrations are backwards compatible
- [ ] Foreign key constraints defined
- [ ] Type-appropriate columns (BIGINT for IDs, DECIMAL for money)

**Code review questions:**
- Could this query timeout on large datasets?
- Are we over-fetching data we don't need?
- If schema changes, does this still work?
- Is this data connection secured?

**See examples:**
- SQLAlchemy ORM → [src/dataenginex/core/database.py](../src/dataenginex/core/database.py)
- Schema patterns → Check database documentation
- Schema patterns → Check database documentation

---

## Tests

**Before submitting:**
- [ ] Test name describes what it's testing
- [ ] Tests are independent (no dependencies on other tests)
- [ ] Mock external services, not code being tested
- [ ] Edge cases covered (empty, None, boundary values)
- [ ] Error cases tested
- [ ] Tests pass locally

**Code review questions:**
- Does this test verify behavior or implementation?
- What happens if I delete one test, do others break?
- Is this testing the right layer (unit vs integration)?
- Could you understand the test from the name alone?

**See examples:**
- Unit tests → [tests/unit/](../tests/unit/)
- Integration tests → [tests/integration/](../tests/integration/)
- Fixtures → [tests/conftest.py](../tests/conftest.py)

---

## Documentation & Comments

**Before submitting:**
- [ ] Public functions have docstrings
- [ ] Comments explain "why", not "what"
- [ ] Examples work (or link to real code)
- [ ] Complex logic has explanatory comments
- [ ] No credentials in examples

**Code review questions:**
- Could a new developer understand this?
- Is the code obvious without the comment?
- Do examples match current code?

**See examples:**
- Docstrings → Any file in [src/](../src/)
- README patterns → [README.md](../README.md)
- Architecture → [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md)

---

## Security (Critical - Check Every PR)

**Before submitting:**
- [ ] No hardcoded secrets (API keys, passwords, tokens)
- [ ] All user input validated
- [ ] SQL uses parameterized queries
- [ ] Passwords hashed, never stored plaintext
- [ ] Authentication on protected endpoints
- [ ] No sensitive data in logs
- [ ] HTTPS only in production
- [ ] Dependency versions managed in [pyproject.toml](../pyproject.toml)

**Code review questions:**
- Can someone exploit this to access data they shouldn't?
- Is there a hardcoded secret anywhere?
- Could this be an SQL injection?
- What happens if someone sends malicious input?

**See examples:**
- Auth patterns → [src/dataenginex/api/auth.py](../src/dataenginex/api/auth.py)
- Validation → [src/dataenginex/core/validators.py](../src/dataenginex/core/validators.py)
- Configuration → [.env.example](.env.example)

---

## Performance

**Before submitting:**
- [ ] Used profiler/debugger to find actual bottlenecks
- [ ] No obvious N+1 queries
- [ ] Not loading huge datasets into memory unnecessarily
- [ ] Appropriate use of indexes
- [ ] Reasonable algorithm complexity

**Code review questions:**
- How does this scale to 10x current data volume?
- Are we making unnecessary database round trips?
- Could this timeout with large datasets?

**See examples:**
- Efficient queries → Check [src/dataenginex/core/database.py](../src/dataenginex/core/database.py)
- Async patterns → [src/dataenginex/api/](../src/dataenginex/api/)

---

## Principles That Apply Everywhere

Regardless of domain:

✅ **Do:**
- Single responsibility: each function does one thing well
- Explicit error handling (catch specific exceptions)
- Type hints and validation
- Tests for new code
- Clear naming
- Code that explains itself

❌ **Don't:**
- Hardcode secrets
- Catch all exceptions with bare `except:`
- Use dynamic typing without reason
- Ignore errors silently
- Write functions >50 lines
- Skip testing

---

## When in Doubt

1. **Check for existing patterns** in the codebase (better than any doc)
2. **Run the tests locally** - they show expected behavior
3. **Run the real app** - tests passing doesn't mean the app works
4. **Ask the team** - better to clarify than guess
5. **Refer to principles** in [copilot-instructions.md](copilot-instructions.md)

---

## Real App Validation (Run Before Every PR)

Tests and lint passing is necessary but NOT sufficient. Always run the real application.

**Server startup:**
```bash
uv run python examples/02_api_quickstart.py
```

**Endpoint validation checklist:**
- [ ] Server starts without import errors or crashes
- [ ] `GET /health` → `{"status": "healthy"}`
- [ ] `GET /ready` → all components `ready`
- [ ] `GET /startup` → `started: true`
- [ ] `GET /` → root response with version
- [ ] `POST /echo` → echoes message back
- [ ] `GET /metrics` → Prometheus metrics
- [ ] `GET /openapi.json` → all routes registered
- [ ] All new/changed endpoints return correct response bodies (not just 200 OK)
- [ ] Validation errors return 422 with detail (send bad input on purpose)

**Standalone module validation:**
```bash
uv run python -c "import dataenginex; print('OK', dataenginex.__file__)"
```
- [ ] Key classes instantiate and produce correct output outside the API
- [ ] No hidden import-time side effects or crashes

**Full validation pipeline order:**
1. `uv run poe lint` (or `uv run python -m ruff check src/ tests/`)
2. `uv run poe typecheck` (or `uv run python -m mypy src/dataenginex/ --strict`)
3. `uv run poe test` (or `uv run python -m pytest tests/ -x --tb=short -q`)
4. Start real server and curl all endpoints (above)
5. Run standalone module imports (above)
