"""CareerDEX Core Business Logic.

This module contains the core implementations for CareerDEX, including:
- Configuration loading and validation (fail-fast)
- Custom exception hierarchy
- Notification system (Slack, GitHub)
- Domain schemas (JobPosting, UserProfile, etc.)
- Domain validators and quality scoring
- Pipeline configuration and metrics
"""

from .exceptions import (
    CareerDEXError,
    ConfigurationError,
    MissingDependencyError,
    NotificationError,
    StubNotImplementedError,
)
from .notifier import GitHubStatusNotifier, PipelineNotifier, SlackNotifier
from .pipeline_config import PipelineConfig, PipelineMetrics
from .schemas import (
    DataQualityReport,
    JobBenefits,
    JobLocation,
    JobPosting,
    JobSourceEnum,
    PipelineExecutionMetadata,
    UserProfile,
)
from .settings import CareerDEXSettings, get_settings, reset_settings
from .validators import (
    CareerDEXQualityChecks,
    DataHash,
    QualityScorer,
    SchemaValidator,
)

__all__ = [
    # Exceptions
    "CareerDEXError",
    "ConfigurationError",
    "MissingDependencyError",
    "NotificationError",
    "StubNotImplementedError",
    # Notifier
    "GitHubStatusNotifier",
    "PipelineNotifier",
    "SlackNotifier",
    # Pipeline config
    "PipelineConfig",
    "PipelineMetrics",
    # Schemas
    "DataQualityReport",
    "JobBenefits",
    "JobLocation",
    "JobPosting",
    "JobSourceEnum",
    "PipelineExecutionMetadata",
    "UserProfile",
    # Settings
    "CareerDEXSettings",
    "get_settings",
    "reset_settings",
    # Validators
    "CareerDEXQualityChecks",
    "DataHash",
    "QualityScorer",
    "SchemaValidator",
]
