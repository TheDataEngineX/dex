# dataenginex.warehouse

SQL-style transforms and persistent data lineage tracking for warehouse workloads.

## Quick import

```python
from dataenginex.warehouse import (
    SqlTransformRunner,
    LineageTracker,
    LineageEvent,
)
```

______________________________________________________________________

## Transforms

`dataenginex.warehouse.transforms`

SQL transform runner for warehouse-layer batch transformations. Executes DuckDB SQL with named input/output dataset binding, supports CTEs and multi-statement scripts.

::: dataenginex.warehouse.transforms

**Key class:** `SqlTransformRunner`

```python
from dataenginex.warehouse.transforms import SqlTransformRunner

runner = SqlTransformRunner(db_path=".dex/store.duckdb")
runner.run(
    sql="""
    CREATE OR REPLACE TABLE gold.user_summary AS
    SELECT user_id, COUNT(*) AS events, MAX(ts) AS last_seen
    FROM silver.events
    GROUP BY 1
    """,
)
```

______________________________________________________________________

## Lineage

`dataenginex.warehouse.lineage`

Column-level and dataset-level data lineage tracking. Records source → transform → destination relationships to DuckDB for audit and impact analysis.

::: dataenginex.warehouse.lineage

**Key classes:** `LineageTracker`, `LineageEvent`, `LineageNode`

```python
from dataenginex.warehouse.lineage import LineageTracker

tracker = LineageTracker(db_path=".dex/store.duckdb")

tracker.record(
    source="silver.events",
    transform="user_summary_agg",
    destination="gold.user_summary",
    columns={"user_id": ["user_id"], "events": ["event_id"]},
)

upstream = tracker.upstream("gold.user_summary")
downstream = tracker.downstream("silver.events")
```
