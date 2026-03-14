---
description: "Create a new Airflow DAG using the dataenginex medallion pattern"
tools: ["search/codebase", "execute/runInTerminal", "execute/getTerminalOutput", "read/terminalLastCommand", "read/terminalSelection"]
---

Create a new Airflow DAG using the DataEngineX medallion architecture pattern.

## Requirements

1. **Structure**:
   - Use `default_args` with owner, retries, retry_delay
   - Define clear task dependencies with `>>` operator
   - Use XCom for inter-task data passing
   - DAG must be idempotent (safe to rerun)
2. **Medallion pattern**:
   - Bronze: raw ingestion → Silver: cleaned/validated → Gold: aggregated
   - Log processing counts and record IDs at each stage
   - Reference `examples/07_api_ingestion.py` for the full pattern
3. **Data quality**:
   - Validate schemas at entry point using project validators
   - Reference `src/dataenginex/core/validators.py` for patterns
4. **Logging**:
   - Use `from loguru import logger` (not structlog in data pipelines)
   - Log with structured key-value pairs: `logger.info("processed records", count=n)`
5. **Error handling**:
   - Catch specific exceptions, log context, re-raise
   - Never silently swallow errors
6. **Tests** — Add tests in `tests/unit/` following patterns in `test_data.py`
