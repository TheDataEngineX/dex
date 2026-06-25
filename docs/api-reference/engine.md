# dataenginex.engine

`DexEngine` — the central runtime that wires config, pipelines, ML, AI, and storage together.

## Quick import

```python
from dataenginex import DexEngine

engine = DexEngine("dex.yaml")
```

______________________________________________________________________

## DexEngine

`dataenginex.engine`

Top-level entry point. Loads config, initialises subsystems (connector registry, ML registry, AI router, scheduler, stores), and exposes a unified API for running pipelines, training models, and querying state.

::: dataenginex.engine

**Key class:** `DexEngine`

### Lifecycle

```python
from dataenginex import DexEngine

engine = DexEngine("dex.yaml")

# Health check
status = engine.health()
print(status.ok, status.components)

# Run a pipeline
result = engine.run_pipeline("ingest_events")
print(result.rows_written, result.duration_ms)

# Train a model
train_result = engine.train("churn_model")
print(train_result.metrics)

# Predict
prediction = engine.predict("churn_model", features={"age": 34, "tenure": 12})
print(prediction.label, prediction.probability)
```

### Config-first usage

All subsystems are driven by `dex.yaml`. `DexEngine` is the only object most applications need:

```yaml
# dex.yaml
pipelines:
  ingest_events:
    source:
      type: csv
      path: data/raw/events.csv
    destination:
      type: parquet
      path: data/bronze/events

ml:
  churn_model:
    trainer: sklearn
    algorithm: random_forest
    target: churned
    features: [age, tenure, spend]
```

```python
engine = DexEngine("dex.yaml")
engine.run_pipeline("ingest_events")
engine.train("churn_model")
```

______________________________________________________________________

## Store

`dataenginex.store`

Low-level DuckDB store used by all DEX subsystems (lineage, run history, feature store, audit log, catalog). Applications rarely need to interact with this directly.

::: dataenginex.store

______________________________________________________________________

## Worker

`dataenginex.worker`

Background worker process for async pipeline and model job execution. Used by the scheduler and queue backends.

::: dataenginex.worker
