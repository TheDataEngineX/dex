Run the full DEX validation pipeline in order. Stop on first failure.

1. **Lint:** `uv run poe lint`
1. **Typecheck:** `uv run poe typecheck`
1. **Tests:** `uv run poe test`
1. **Real app:** Start `uv run python examples/02_api_quickstart.py` and verify:
   - `curl http://localhost:8000/health`
   - `curl http://localhost:8000/`
   - `curl http://localhost:8000/metrics`
   - Check response bodies — not just status codes
1. **Standalone import:** `uv run python -c "import dataenginex; print('OK', dataenginex.__file__)"`

Report results for each step. If any step fails, stop and report the failure.
