"""Data layer — connectors, transforms, quality gates, pipelines.

Public API::

    from dataenginex.data import (
        connector_registry, transform_registry,
        DuckDBConnector, CsvConnector,
        PipelineRunner, PipelineResult,
        QualityResult, check_quality,
        DataProfiler, ProfileReport, ColumnProfile,
        SchemaRegistry, SchemaVersion,
    )
"""

from __future__ import annotations

from dataenginex.data.connectors import connector_registry
from dataenginex.data.connectors.csv import CsvConnector
from dataenginex.data.connectors.duckdb import DuckDBConnector
from dataenginex.data.connectors.parquet import ParquetConnector
from dataenginex.data.pipeline.runner import PipelineResult, PipelineRunner
from dataenginex.data.profiler import ColumnProfile, DataProfiler, ProfileReport
from dataenginex.data.quality.gates import QualityResult, check_quality
from dataenginex.data.registry import SchemaRegistry, SchemaVersion
from dataenginex.data.transforms import transform_registry

__all__ = [
    "CsvConnector",
    "DuckDBConnector",
    "ParquetConnector",
    "PipelineResult",
    "PipelineRunner",
    "QualityResult",
    "check_quality",
    "connector_registry",
    "transform_registry",
    "ColumnProfile",
    "DataProfiler",
    "ProfileReport",
    "SchemaRegistry",
    "SchemaVersion",
]
