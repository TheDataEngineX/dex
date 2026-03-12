Run the full DEX validation pipeline in order. Stop on first failure.

1. **Lint:** `uv run poe lint`
2. **Typecheck:** `uv run poe typecheck`
3. **Tests:** `uv run poe test`
4. **Real app:** Start `uv run uvicorn careerdex.api.main:app --port 8000` and verify:
   - `curl http://localhost:8000/health`
   - `curl http://localhost:8000/ready`
   - `curl http://localhost:8000/startup`
   - `curl http://localhost:8000/`
   - `curl http://localhost:8000/metrics`
   - `curl http://localhost:8000/api/v1/data/sources`
   - `curl http://localhost:8000/api/v1/system/config`
   - Check response bodies — not just status codes
5. **Standalone import:** `uv run python -c "from careerdex.phases.phase1_foundation import bootstrap_phase1; print('OK')"`

Report results for each step. If any step fails, stop and report the failure.
