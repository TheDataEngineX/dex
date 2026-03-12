# dataenginex

`dataenginex` is the core DataEngineX framework package for building observable, production-ready data and API services.

It provides:

- FastAPI application primitives and API extensions
- Middleware for structured logging, metrics, and tracing
- Data quality and validation utilities
- Lakehouse and warehouse building blocks (S3, GCS, BigQuery, Parquet)
- Reusable ML support modules for model-serving workflows

## Install

```bash
# Core (no web framework dependencies)
pip install dataenginex

# With FastAPI, middleware, auth, health checks
pip install dataenginex[api]

# With cloud storage backends
pip install dataenginex[s3]        # AWS S3 via boto3
pip install dataenginex[gcs]       # Google Cloud Storage
pip install dataenginex[bq]        # Google BigQuery
pip install dataenginex[cloud]     # All cloud storage (S3 + GCS)

# Everything
pip install dataenginex[all]
```

## Package Scope

This package is the core library from the DEX monorepo.
`careerdex` and `weatherdex` are maintained in the same repository but are not part of this package release flow.

## Submodules

| Module | Requires Extra | Description |
|--------|---------------|-------------|
| `dataenginex.core` | — | Medallion architecture, schemas, quality gates, validators |
| `dataenginex.data` | — | Schema registry, data contracts, catalog |
| `dataenginex.lakehouse` | optional `[s3]` `[gcs]` `[bq]` | Storage backends (JSON, Parquet, S3, GCS, BigQuery), catalog, partitioning |
| `dataenginex.warehouse` | — | Warehouse layers, lineage tracking |
| `dataenginex.ml` | — | Model registry, vectorstore, LLM adapters, drift detection |
| `dataenginex.api` | `[api]` | Auth (JWT), health checks, error handling, pagination, rate limiting |
| `dataenginex.middleware` | `[api]` | Structured logging, Prometheus metrics, OpenTelemetry tracing |

## Quick Usage

```python
# Core — always available
from dataenginex.core import MedallionArchitecture, QualityGate
from dataenginex.data import SchemaRegistry
from dataenginex.ml import ModelRegistry

# API — requires pip install dataenginex[api]
from dataenginex.api import HealthChecker, AuthMiddleware, paginate
from dataenginex.middleware import configure_logging, configure_tracing

# Storage — requires the relevant extra
from dataenginex.lakehouse import JsonStorage, get_storage
storage = get_storage("file://./data")       # always works
storage = get_storage("s3://my-bucket")      # requires [s3]
storage = get_storage("gs://my-bucket")      # requires [gcs]
storage = get_storage("bq://my-project/ds")  # requires [bq]
```

## Source and Docs

- Repository: https://github.com/TheDataEngineX/DEX
- CI/CD guide: `docs/CI_CD.md`
- Release notes: `packages/dataenginex/src/dataenginex/RELEASE_NOTES.md`
