---
applyTo: "src/**/ml/**/*.py"
---

# ML — Project Specifics

## Model Lifecycle
- Stages: development → staging → production → archived (auto-archival on promotion)
- `ModelRegistry` (`registry.py`) — JSON-persisted, one production version per model name

## Training & Serving
- Implement `BaseTrainer` ABC (`training.py`) — train → evaluate → save
- Serving contracts: `PredictionRequest`/`PredictionResponse` (`serving.py`)
- Prediction latency tracked via Prometheus histograms
- Use `from loguru import logger` (not structlog) in all ML modules

## Drift Detection
- PSI-based distribution drift (`drift.py`) — severity: none → low → medium → high
- Alert on medium+ severity, log per-feature drift scores

## PySpark ML
- `Pipeline` + `PipelineModel` for reproducible transforms
- Feature engineering: lag, rolling, interaction terms
- Models: RandomForest, GBT — see `examples/08_spark_ml.py`, `examples/09_feature_engineering.py`

## Security
- `pickle.loads` only from trusted sources — never deserialize untrusted artifacts

## Testing
- Dummy estimators + small datasets — see `tests/unit/test_ml.py`
