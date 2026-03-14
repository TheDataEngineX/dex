---
applyTo: "src/**/data/**/*.py,src/**/lakehouse/**/*.py,src/**/warehouse/**/*.py,examples/07_*.py"
---

# Data Pipelines — Project Specifics

## Architecture
- Medallion pattern: Bronze (raw) → Silver (cleaned) → Gold (aggregated)
- Pipelines must be idempotent — log processing counts/IDs

## Orchestration
- Airflow DAGs: use `default_args`, XCom, clear task dependencies
- PySpark: for large-scale transforms (see `examples/08_spark_ml.py`, `examples/09_feature_engineering.py`)

## Quality & Governance
- `SchemaRegistry`: `src/dataenginex/data/registry.py` (schema versioning)
- `DataCatalog`: `src/dataenginex/lakehouse/catalog.py` (dataset discovery)
- Data contracts: Pydantic schemas in `src/dataenginex/core/schemas.py`
- Validators: `src/dataenginex/core/validators.py`

## Transform & Lineage
- `TransformPipeline`: composable transforms (`src/dataenginex/warehouse/transforms.py`)
- `PersistentLineage`: data lineage tracking (`src/dataenginex/warehouse/lineage.py`)
- Partitioning: `DatePartitioner`, `HashPartitioner` (`src/dataenginex/lakehouse/partitioning.py`)
- Profiling: `src/dataenginex/data/profiler.py`

## Project Map
- `src/dataenginex/data/` — connectors, profiler, registry
- `src/dataenginex/lakehouse/` — catalog, partitioning, storage
- `src/dataenginex/warehouse/` — transforms, lineage, metrics
- `examples/07_api_ingestion.py` — HTTP API ingestion with medallion architecture
- `examples/08_spark_ml.py` — PySpark feature engineering + model training

## Testing
- See `tests/unit/test_data.py`, `test_medallion.py`, `test_warehouse.py`
