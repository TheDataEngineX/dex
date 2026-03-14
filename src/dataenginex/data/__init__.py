"""Data connectors, profiling, and schema registry.

Public API::

    from dataenginex.data import (
        DataConnector, RestConnector, FileConnector,
        ConnectorStatus, FetchResult,
        DataProfiler, ProfileReport, ColumnProfile,
        SchemaRegistry, SchemaVersion,
    )
"""

from __future__ import annotations

from .connectors import ConnectorStatus, DataConnector, FetchResult, FileConnector, RestConnector
from .profiler import ColumnProfile, DataProfiler, ProfileReport
from .registry import SchemaRegistry, SchemaVersion

__all__ = [
    # Connectors
    "ConnectorStatus",
    "DataConnector",
    "FetchResult",
    "FileConnector",
    "RestConnector",
    # Profiler
    "ColumnProfile",
    "DataProfiler",
    "ProfileReport",
    # Schema registry
    "SchemaRegistry",
    "SchemaVersion",
]
