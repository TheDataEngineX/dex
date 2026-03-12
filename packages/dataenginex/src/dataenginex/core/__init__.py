"""Core framework — schemas, validators, medallion architecture, quality.

Domain-specific symbols should live in the application package
(e.g. ``myapp.core``).

Public API::

    from dataenginex.core import (
        # Medallion
        MedallionArchitecture, DataLayer, StorageFormat, LayerConfiguration,
        StorageBackend, LocalParquetStorage, BigQueryStorage, DualStorage,
        DataLineage,
        # Quality
        QualityGate, QualityStore, QualityResult, QualityDimension,
        # Schemas (generic API)
        ErrorDetail, ErrorResponse, RootResponse, HealthResponse,
        StartupResponse, ComponentStatus, ReadinessResponse,
        EchoRequest, EchoResponse,
        # Validators (generic)
        DataQualityChecks, ValidationReport,
    )
"""

from __future__ import annotations

from .medallion_architecture import (
    BigQueryStorage,
    DataLayer,
    DataLineage,
    DualStorage,
    LayerConfiguration,
    LocalParquetStorage,
    MedallionArchitecture,
    StorageBackend,
    StorageFormat,
)
from .quality import QualityDimension, QualityGate, QualityResult, QualityStore
from .schemas import (
    ComponentStatus,
    EchoRequest,
    EchoResponse,
    ErrorDetail,
    ErrorResponse,
    HealthResponse,
    ReadinessResponse,
    RootResponse,
    StartupResponse,
)
from .validators import (
    DataQualityChecks,
    ValidationReport,
)

__all__ = [
    # Medallion architecture
    "BigQueryStorage",
    "DataLayer",
    "DataLineage",
    "DualStorage",
    "LayerConfiguration",
    "LocalParquetStorage",
    "MedallionArchitecture",
    "StorageBackend",
    "StorageFormat",
    # Quality gate
    "QualityDimension",
    "QualityGate",
    "QualityResult",
    "QualityStore",
    # Schemas (generic API only)
    "ComponentStatus",
    "EchoRequest",
    "EchoResponse",
    "ErrorDetail",
    "ErrorResponse",
    "HealthResponse",
    "ReadinessResponse",
    "RootResponse",
    "StartupResponse",
    # Validators (generic only)
    "DataQualityChecks",
    "ValidationReport",
]
