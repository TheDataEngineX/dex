# Weather Pipeline Examples

The WeatherDEX reference implementation has been converted into standalone numbered examples in `examples/`.

## Examples

| File | What It Shows |
|------|--------------|
| [`examples/07_api_ingestion.py`](../../examples/07_api_ingestion.py) | HTTP API ingestion with Bronze→Silver→Gold medallion pipeline |
| [`examples/08_spark_ml.py`](../../examples/08_spark_ml.py) | PySpark feature engineering + RandomForest training via `ModelRegistry` |
| [`examples/09_feature_engineering.py`](../../examples/09_feature_engineering.py) | Time features, lag features, rolling window stats, interaction features |
| [`examples/10_model_analysis.py`](../../examples/10_model_analysis.py) | Prediction error analysis, groupBy stats, PSI-based drift detection |

## Quick Start

```bash
# API ingestion pipeline (no external deps)
uv run python examples/07_api_ingestion.py

# PySpark ML (requires Java 17+)
uv run python examples/08_spark_ml.py
uv run python examples/09_feature_engineering.py

# Model analysis + drift detection
uv run python examples/10_model_analysis.py
```

## Reference

- [Examples Guide](../../examples/GUIDE.md) — Full example index
- [Architecture](../ARCHITECTURE.md) — Medallion architecture design
- [ADR-0001](../adr/0001-medallion-architecture.md) — Medallion architecture decision

______________________________________________________________________

**[← Documentation Hub](../docs-hub.md)**
