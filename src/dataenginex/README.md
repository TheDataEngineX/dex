# dataenginex

Unified Data + ML + AI framework. Config-driven, self-hosted, production-ready.

## Install

```bash
# Core (DuckDB, FastAPI, structlog, Pydantic, Click, Rich)
pip install dataenginex

# With optional extras
pip install dataenginex[dagster]      # Dagster orchestration
pip install dataenginex[mlflow]       # MLflow experiment tracking
pip install dataenginex[agents]       # LangGraph agent runtime
pip install dataenginex[vectors]      # Qdrant + LanceDB vector stores
pip install dataenginex[embeddings]   # sentence-transformers + ONNX
pip install dataenginex[spark]        # PySpark transforms
pip install dataenginex[cloud]        # S3 + GCS storage backends
pip install dataenginex[all]          # Everything
```

## Submodules

| Module | Requires Extra | Description |
|--------|---------------|-------------|
| `dataenginex.config` | — | dex.yaml schema, loader, env var resolution, layering |
| `dataenginex.core` | — | Exceptions, interfaces (10 Base* ABCs), backend registry |
| `dataenginex.cli` | — | `dex` CLI (validate, version, init, serve) |
| `dataenginex.api` | — | FastAPI app, auth (JWT), health, rate limiting |
| `dataenginex.data` | — | Connectors, schema registry, profiler |
| `dataenginex.ml` | — | Training, model registry, serving, drift detection |
| `dataenginex.middleware` | — | Structured logging, Prometheus metrics, tracing |
| `dataenginex.lakehouse` | optional `[cloud]` | Storage backends (local, S3, GCS), catalog |
| `dataenginex.warehouse` | — | SQL/Spark transforms, lineage |
| `dataenginex.plugins` | — | Plugin system (entry-point discovery) |

## Quick Usage

```python
# Config system
from dataenginex.config import load_config
cfg = load_config(Path("dex.yaml"))

# Core interfaces + registry
from dataenginex.core.interfaces import BaseConnector
from dataenginex.core.registry import BackendRegistry

# Exceptions
from dataenginex.core.exceptions import DataEngineXError, BackendNotInstalledError

# ML
from dataenginex.ml import ModelRegistry

# CLI
# dex validate dex.yaml
# dex version
```

## Source and Docs

- Repository: https://github.com/TheDataEngineX/DEX
- Documentation: https://docs.thedataenginex.org
- Release notes: `CHANGELOG.md`
