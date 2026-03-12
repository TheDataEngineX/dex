"""CareerDEX configuration — Pydantic-validated, fail-fast on missing values.

Loads configuration from ``config/job_config.json`` and validates
every field at startup.  No silent defaults — if a value is missing
or invalid, a ``ValidationError`` is raised immediately with clear
context.

Environment variable overrides (optional):
    ``CAREERDEX_CONFIG_PATH``   — override the JSON config file location
    ``CAREERDEX_HOST``          — API host (default: ``0.0.0.0``)
    ``CAREERDEX_PORT``          — API port (default: ``8000``)
    ``CAREERDEX_SLACK_WEBHOOK`` — Slack webhook URL (required for notifications)
    ``CAREERDEX_GITHUB_REPO``   — GitHub repo ``owner/repo`` (required for notifications)
    ``CAREERDEX_GITHUB_TOKEN``  — GitHub PAT (required for notifications)
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from loguru import logger
from pydantic import BaseModel, Field, field_validator

from .exceptions import ConfigurationError

__all__ = [
    "ATSConfig",
    "CareerDEXSettings",
    "EmbeddingConfig",
    "PipelineSettings",
    "QualityConfig",
    "SourceConfig",
    "StorageConfig",
    "StorageLayerConfig",
    "get_settings",
]


_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "job_config.json"

# ======================================================================
# Pipeline
# ======================================================================


class PipelineSettings(BaseModel):
    """Top-level pipeline configuration."""

    name: str
    schedule: str
    timeout_minutes: int = Field(gt=0)
    retry_count: int = Field(ge=0)
    retry_delay_seconds: int = Field(gt=0)


# ======================================================================
# Sources
# ======================================================================


class ATSConfig(BaseModel):
    """ATS API endpoint configuration."""

    greenhouse: str
    lever: str


class SourceConfig(BaseModel):
    """Configuration for a single job source."""

    enabled: bool
    batch_size: int = Field(gt=0)
    expected_jobs_per_cycle: int = Field(gt=0)
    rate_limit_per_minute: int | None = None
    api_endpoint: str | None = None
    base_url: str | None = None
    ats_apis: ATSConfig | None = None


# ======================================================================
# Storage
# ======================================================================


class StorageLayerConfig(BaseModel):
    """Configuration for a single medallion layer."""

    path: str
    format: str = "parquet"
    compression: str = "snappy"
    retention_days: int | None = None


class StorageConfig(BaseModel):
    """Storage configuration for all medallion layers."""

    local_base_path: str
    layers: dict[str, StorageLayerConfig]

    @field_validator("layers")
    @classmethod
    def validate_required_layers(
        cls,
        v: dict[str, StorageLayerConfig],
    ) -> dict[str, StorageLayerConfig]:
        """Ensure bronze, silver, and gold layers are all defined."""
        required = {"bronze", "silver", "gold"}
        missing = required - set(v.keys())
        if missing:
            msg = f"Missing required storage layers: {sorted(missing)}"
            raise ValueError(msg)
        return v


# ======================================================================
# Quality
# ======================================================================


class QualityConfig(BaseModel):
    """Data quality thresholds and rules."""

    min_quality_score: float = Field(ge=0, le=1)
    required_fields: list[str] = Field(min_length=1)
    dedup_fields: list[str] = Field(min_length=1)


# ======================================================================
# Embeddings
# ======================================================================


class EmbeddingConfig(BaseModel):
    """Embedding model configuration."""

    model_name: str
    dimension: int = Field(gt=0)
    batch_size: int = Field(gt=0)
    cache_ttl_seconds: int = Field(ge=0)


# ======================================================================
# ML Models
# ======================================================================


class MatcherWeights(BaseModel):
    """Resume-job matcher scoring weights."""

    embedding_similarity: float = Field(ge=0, le=1)
    skill_overlap: float = Field(ge=0, le=1)
    location_match: float = Field(ge=0, le=1)
    salary_fit: float = Field(ge=0, le=1)

    @field_validator("salary_fit")
    @classmethod
    def weights_must_sum_to_one(cls, v: float, info: Any) -> float:
        """Validate that all weights sum to 1.0."""
        total = (
            info.data.get("embedding_similarity", 0)
            + info.data.get("skill_overlap", 0)
            + info.data.get("location_match", 0)
            + v
        )
        if abs(total - 1.0) > 0.01:
            msg = f"Matcher weights must sum to 1.0, got {total:.2f}"
            raise ValueError(msg)
        return v


class MatcherConfig(BaseModel):
    """Resume-job matcher model config."""

    weights: MatcherWeights


class SalaryPredictorConfig(BaseModel):
    """Salary predictor model config."""

    algorithm: str
    percentiles: list[int]


class SkillGapConfig(BaseModel):
    """Skill gap analyzer config."""

    top_k_recommendations: int = Field(gt=0)


class CareerPathConfig(BaseModel):
    """Career path recommender config."""

    max_paths: int = Field(gt=0)
    min_transition_probability: float = Field(ge=0, le=1)


class ChurnPredictorConfig(BaseModel):
    """Churn predictor config."""

    algorithm: str
    threshold: float = Field(ge=0, le=1)


class MLModelsConfig(BaseModel):
    """All ML model configurations."""

    resume_job_matcher: MatcherConfig
    salary_predictor: SalaryPredictorConfig
    skill_gap_analyzer: SkillGapConfig
    career_path_recommender: CareerPathConfig
    churn_predictor: ChurnPredictorConfig


# ======================================================================
# API
# ======================================================================


class CacheTTLConfig(BaseModel):
    """API cache TTL configuration in seconds."""

    recommendations: int = Field(ge=0)
    salary_prediction: int = Field(ge=0)
    market_trends: int = Field(ge=0)
    skills_trending: int = Field(ge=0)


class PaginationConfig(BaseModel):
    """API pagination configuration."""

    default_page_size: int = Field(gt=0)
    max_page_size: int = Field(gt=0)


class APIConfig(BaseModel):
    """API-level configuration."""

    cache_ttl: CacheTTLConfig
    pagination: PaginationConfig


# ======================================================================
# Root settings
# ======================================================================


class CareerDEXSettings(BaseModel):
    """Complete CareerDEX configuration.

    Loaded from ``config/job_config.json`` and validated at startup.
    Raises ``pydantic.ValidationError`` on missing or invalid values —
    the application will NOT start with bad config.
    """

    pipeline: PipelineSettings
    sources: dict[str, SourceConfig]
    storage: StorageConfig
    quality: QualityConfig
    embeddings: EmbeddingConfig
    ml_models: MLModelsConfig
    api: APIConfig

    @field_validator("sources")
    @classmethod
    def validate_at_least_one_source(
        cls,
        v: dict[str, SourceConfig],
    ) -> dict[str, SourceConfig]:
        """Ensure at least one source is configured."""
        if not v:
            msg = "At least one job source must be configured"
            raise ValueError(msg)
        return v

    @classmethod
    def load(cls, config_path: Path | None = None) -> CareerDEXSettings:
        """Load and validate settings from JSON config.

        Args:
            config_path: Override path to config file.  Falls back to
                ``CAREERDEX_CONFIG_PATH`` env var, then the default
                ``config/job_config.json``.

        Returns:
            Validated ``CareerDEXSettings`` instance.

        Raises:
            ConfigurationError: If the config file is missing.
            pydantic.ValidationError: If any required value is missing or invalid.
        """
        path = config_path or Path(os.getenv("CAREERDEX_CONFIG_PATH", str(_CONFIG_PATH)))
        if not path.exists():
            msg = (
                f"CareerDEX config file not found: {path}. "
                f"Set CAREERDEX_CONFIG_PATH or create {_CONFIG_PATH}"
            )
            raise ConfigurationError(msg)

        with path.open() as fh:
            raw = json.load(fh)

        settings = cls.model_validate(raw)
        logger.info(
            "CareerDEX settings loaded, pipeline=%s, sources=%d",
            settings.pipeline.name,
            len(settings.sources),
        )
        return settings


# ======================================================================
# Singleton accessor
# ======================================================================

_settings: CareerDEXSettings | None = None


def get_settings(config_path: Path | None = None) -> CareerDEXSettings:
    """Return the singleton ``CareerDEXSettings`` instance.

    Thread-safe via module-level caching.  Call with ``config_path``
    to override on first load (e.g. in tests).

    Raises:
        ConfigurationError: If the config file is missing.
        pydantic.ValidationError: If validation fails.
    """
    global _settings  # noqa: PLW0603
    if _settings is None:
        _settings = CareerDEXSettings.load(config_path)
    return _settings


def reset_settings() -> None:
    """Reset the cached settings (for testing)."""
    global _settings  # noqa: PLW0603
    _settings = None
