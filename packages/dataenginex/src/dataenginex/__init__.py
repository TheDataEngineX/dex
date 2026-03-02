"""
DataEngineX (DEX) — Core framework for data engineering projects.

Public API surface. Import from top-level or from subpackages:

    from dataenginex import __version__
    from dataenginex.api import HealthChecker, HealthStatus
    from dataenginex.core import MedallionArchitecture, DataLayer
    from dataenginex.data import DataConnector, DataProfiler, SchemaRegistry
    from dataenginex.lakehouse import DataCatalog, ParquetStorage
    from dataenginex.middleware import configure_logging, configure_tracing
    from dataenginex.ml import ModelRegistry, SklearnTrainer, DriftDetector
    from dataenginex.warehouse import PersistentLineage, TransformPipeline

Submodules:
    api        – FastAPI application, health checks, error handling, pagination
    core       – Schemas, validators, medallion architecture, pipeline config
    data       – Data connectors, profiler, schema registry
    lakehouse  – Storage backends, data catalog, partitioning
    middleware – Logging, metrics, tracing, request middleware
    ml         – ML training, model registry, drift detection, serving
    warehouse  – Transforms, persistent lineage tracking
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("dataenginex")
except PackageNotFoundError:
    __version__ = "0.5.0"

# Re-export key public symbols for convenience top-level imports
from dataenginex.api import HealthChecker, HealthStatus
from dataenginex.core import DataLayer, MedallionArchitecture, QualityGate
from dataenginex.data import DataConnector, DataProfiler, SchemaRegistry
from dataenginex.lakehouse import DataCatalog, ParquetStorage, StorageBackend
from dataenginex.middleware import configure_logging, configure_tracing, get_logger
from dataenginex.ml import DriftDetector, ModelRegistry, SklearnTrainer
from dataenginex.warehouse import PersistentLineage, TransformPipeline

__all__ = [
    "__version__",
    # api
    "HealthChecker",
    "HealthStatus",
    # core
    "DataLayer",
    "MedallionArchitecture",
    "QualityGate",
    # data
    "DataConnector",
    "DataProfiler",
    "SchemaRegistry",
    # lakehouse
    "DataCatalog",
    "ParquetStorage",
    "StorageBackend",
    # middleware
    "configure_logging",
    "configure_tracing",
    "get_logger",
    # ml
    "DriftDetector",
    "ModelRegistry",
    "SklearnTrainer",
    # warehouse
    "PersistentLineage",
    "TransformPipeline",
]
