# Validate (DEX)

Run the full DEX validation pipeline in order. Stop and report on first failure.

1. **Lint**

   ```bash
   uv run poe lint
   ```

1. **Typecheck**

   ```bash
   uv run poe typecheck
   ```

1. **Tests**

   ```bash
   uv run poe test
   ```

1. **Real server** — start the quickstart example and verify all endpoints

   ```bash
   uv run python examples/02_api_quickstart.py &
   sleep 2
   curl -sf http://localhost:17000/health   | python -m json.tool
   curl -sf http://localhost:17000/         | python -m json.tool
   curl -sf http://localhost:17000/metrics  | head -20
   curl -sf -X POST http://localhost:17000/echo -H "Content-Type: application/json" -d '{"message":"test"}' | python -m json.tool
   ```

   Check response **bodies** — not just status codes. Kill the server after.

1. **Standalone import**

   ```bash
   uv run python -c "import dataenginex; print('OK', dataenginex.__file__)"
   ```

Tests passing ≠ app working. Step 4 is NON-NEGOTIABLE.

Report pass/fail for each step with exact output. On failure, identify root cause — do not skip ahead.
