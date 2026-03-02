"""Core framework — schemas, validators, medallion architecture, pipeline config, quality.

Public API::

    from dataenginex.core import (
        # Medallion
        MedallionArchitecture, DataLayer, StorageFormat, LayerConfiguration,
        StorageBackend, LocalParquetStorage, BigQueryStorage, DualStorage, DataLineage,
        # Pipeline
        PipelineConfig, PipelineMetrics,
        # Quality
        QualityGate, QualityStore, QualityResult, QualityDimension,
        # Schemas
        JobPosting, JobSourceEnum, UserProfile,
        ErrorDetail, ErrorResponse, RootResponse, HealthResponse,
        StartupResponse, ComponentStatus, ReadinessResponse,
        EchoRequest, EchoResponse,
        DataQualityReport, PipelineExecutionMetadata,
        # Validators
        SchemaValidator, DataQualityChecks, DataHash,
        QualityScorer, ValidationReport,
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
from .pipeline_config import PipelineConfig, PipelineMetrics
from .quality import QualityDimension, QualityGate, QualityResult, QualityStore
from .schemas import (
    ComponentStatus,
    DataQualityReport,
    EchoRequest,
    EchoResponse,
    ErrorDetail,
    ErrorResponse,
    HealthResponse,
    JobPosting,
    JobSourceEnum,
    PipelineExecutionMetadata,
    ReadinessResponse,
    RootResponse,
    StartupResponse,
    UserProfile,
)
from .validators import (
    DataHash,
    DataQualityChecks,
    QualityScorer,
    SchemaValidator,
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
    # Pipeline
    "PipelineConfig",
    "PipelineMetrics",
    # Quality gate
    "QualityDimension",
    "QualityGate",
    "QualityResult",
    "QualityStore",
    # Schemas
    "ComponentStatus",
    "DataQualityReport",
    "EchoRequest",
    "EchoResponse",
    "ErrorDetail",
    "ErrorResponse",
    "HealthResponse",
    "JobPosting",
    "JobSourceEnum",
    "PipelineExecutionMetadata",
    "ReadinessResponse",
    "RootResponse",
    "StartupResponse",
    "UserProfile",
    # Validators
    "DataHash",
    "DataQualityChecks",
    "QualityScorer",
    "SchemaValidator",
    "ValidationReport",
]
