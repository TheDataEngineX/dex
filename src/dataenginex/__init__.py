"""
DataEngineX (DEX) — Core framework for data engineering projects.

Public API surface. Import from top-level or from subpackages:

    from dataenginex import __version__
    from dataenginex.core import MedallionArchitecture, DataLayer, QualityGate
    from dataenginex.data import DataConnector, DataProfiler, SchemaRegistry
    from dataenginex.lakehouse import DataCatalog, ParquetStorage
    from dataenginex.ml import ModelRegistry, SklearnTrainer, DriftDetector
    from dataenginex.ml import RAGPipeline, InMemoryBackend, VectorStoreBackend
    from dataenginex.ml import OllamaProvider, MockProvider, LLMProvider
    from dataenginex.warehouse import PersistentLineage, TransformPipeline

Optional (requires ``pip install dataenginex[api]``):

    from dataenginex.api import HealthChecker, AuthMiddleware, paginate
    from dataenginex.middleware import configure_logging, configure_tracing

Submodules:
    api        – Reusable API utilities (auth, health, errors, pagination, rate limiting)
               Requires ``dataenginex[api]`` extra.
    core       – Schemas, validators, medallion architecture, quality gate
    data       – Data connectors, profiler, schema registry
    lakehouse  – Storage backends, data catalog, partitioning
    middleware – Logging, metrics, tracing, request middleware
               Requires ``dataenginex[api]`` extra.
    ml         – ML training, model registry, drift, serving, vectorstore, LLM
    warehouse  – Transforms, persistent lineage tracking
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("dataenginex")
except PackageNotFoundError:
    __version__ = "1.1.0"

# Re-export core symbols that don't require optional dependencies
from dataenginex.core import DataLayer, MedallionArchitecture, QualityGate
from dataenginex.data import DataConnector, DataProfiler, SchemaRegistry
from dataenginex.lakehouse import DataCatalog, ParquetStorage, StorageBackend
from dataenginex.ml import (
    DriftDetector,
    InMemoryBackend,
    LLMProvider,
    MockProvider,
    ModelRegistry,
    OllamaProvider,
    RAGPipeline,
    SklearnTrainer,
    VectorStoreBackend,
)
from dataenginex.warehouse import PersistentLineage, TransformPipeline

__all__ = [
    "__version__",
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
    # ml
    "DriftDetector",
    "InMemoryBackend",
    "LLMProvider",
    "MockProvider",
    "ModelRegistry",
    "OllamaProvider",
    "RAGPipeline",
    "SklearnTrainer",
    "VectorStoreBackend",
    # warehouse
    "PersistentLineage",
    "TransformPipeline",
]
