# dataenginex.middleware

Structured logging, Prometheus metrics, and domain-specific instrumentation for pipelines and models.

## Quick import

```python
from dataenginex.middleware import (
    get_logger,
    get_metrics,
    pipeline_run_duration_seconds,
    ml_drift_score,
    ml_model_predictions_total,
)
```

______________________________________________________________________

## Logging

`dataenginex.middleware.logging_config`

Configures `structlog` with JSON or console rendering, log level, and request-scoped context binding.

::: dataenginex.middleware.logging_config

**Key function:** `get_logger`

```python
from dataenginex.middleware.logging_config import get_logger

logger = get_logger()
logger.info("pipeline_started", pipeline="ingest_events", run_id="abc123")
logger.error("step_failed", step="transform", error=str(exc))
```

______________________________________________________________________

## Metrics

`dataenginex.middleware.metrics`

Prometheus counter, histogram, and gauge definitions for the DEX engine. Exposes metrics via the standard `prometheus_client` registry.

::: dataenginex.middleware.metrics

**Key exports:** `get_metrics`, `pipeline_run_duration_seconds`, `pipeline_runs_total`

```python
from dataenginex.middleware.metrics import get_metrics, pipeline_run_duration_seconds

metrics = get_metrics()
with pipeline_run_duration_seconds.labels(pipeline="ingest_events").time():
    runner.run("ingest_events")
```

______________________________________________________________________

## Domain Metrics

`dataenginex.middleware.domain_metrics`

Higher-level domain metrics for ML models and data quality — drift scores, prediction counts, model latency.

::: dataenginex.middleware.domain_metrics

**Key exports:** `ml_drift_score`, `ml_model_predictions_total`, `model_prediction_latency_seconds`

```python
from dataenginex.middleware.domain_metrics import ml_drift_score

ml_drift_score.labels(model="churn_v1", feature="age").set(0.12)
```
