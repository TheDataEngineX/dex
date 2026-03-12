"""CareerDEX Phase 1: Foundation & Infrastructure (Issue #65).

Provides core infrastructure for the CareerDEX platform:
- Configuration loading from ``config/job_config.json`` (Pydantic-validated)
- Schema validation for job postings and user profiles
- Data quality framework (completeness, accuracy, dedup hashing, scoring)
- Medallion architecture initialisation (Bronze/Silver/Gold layers)
- Sample data generation for **development and testing only**
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from dataenginex.core.medallion_architecture import (
    DataLineage,
    DualStorage,
    MedallionArchitecture,
)
from dataenginex.core.validators import DataQualityChecks
from loguru import logger

from careerdex.core.pipeline_config import PipelineConfig
from careerdex.core.schemas import JobPosting, PipelineExecutionMetadata, UserProfile
from careerdex.core.settings import CareerDEXSettings
from careerdex.core.validators import DataHash, QualityScorer, SchemaValidator

__all__ = [
    "Phase1Foundation",
    "bootstrap_phase1",
    "get_sample_jobs",
    "load_config",
]

_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "job_config.json"


def load_config(path: Path | None = None) -> dict[str, Any]:
    """Load and validate CareerDEX pipeline configuration.

    Loads the JSON config and validates it through Pydantic models.
    Raises immediately on missing file or invalid values — never
    returns partial or default config.

    Args:
        path: Optional override to the config file path.

    Returns:
        Parsed JSON configuration dictionary.

    Raises:
        FileNotFoundError: If the config file does not exist.
        pydantic.ValidationError: If any required config value is missing.
    """
    config_path = path or _CONFIG_PATH
    if not config_path.exists():
        msg = f"Config file not found: {config_path}"
        raise FileNotFoundError(msg)
    with config_path.open() as fh:
        raw = json.load(fh)

    # Validate through Pydantic — raises ValidationError on bad config
    CareerDEXSettings.model_validate(raw)

    return raw


class Phase1Foundation:
    """Phase 1 Foundation bootstrap for CareerDEX v0.5.0.

    Validates that all DataEngineX primitives (schemas, validators,
    medallion architecture, pipeline config) are wired correctly and
    ready for data ingestion.
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or load_config()
        # Validate config through Pydantic at construction time
        self.settings = CareerDEXSettings.model_validate(self.config)
        self.timestamp = datetime.now(tz=UTC).isoformat()
        self.components: list[str] = []
        self.errors: list[str] = []

    # ------------------------------------------------------------------
    # Step helpers
    # ------------------------------------------------------------------

    def _run_step(self, name: str, fn: Any) -> bool:
        """Run a bootstrap step, catching and recording errors."""
        try:
            fn()
            return True
        except Exception as exc:
            msg = f"{name} failed: {exc}"
            logger.error(msg)
            self.errors.append(msg)
            return False

    # ------------------------------------------------------------------
    # Individual bootstrap steps
    # ------------------------------------------------------------------

    def initialize_schemas(self) -> None:
        """Validate that all Pydantic schemas instantiate correctly."""
        logger.info("Phase 1: validating schemas")

        now = datetime.now(tz=UTC)
        JobPosting(
            job_id="test_001",
            source="indeed",
            source_job_id="indeed_12345",
            company_name="TestCorp",
            job_title="Software Engineer",
            job_description="Looking for a talented engineer to build data systems.",
            location={"country": "US", "city": "San Francisco", "remote_eligible": True},
            employment_type="full_time",
            posted_date=now,
            last_modified_date=now,
            dex_hash="abc123def456",
        )
        self.components.append("JobPosting")

        UserProfile(
            user_id="user_001",
            email="test@example.com",
            first_name="John",
            last_name="Doe",
            created_date=now,
            last_activity_date=now,
        )
        self.components.append("UserProfile")

        PipelineExecutionMetadata(
            pipeline_name="careerdex-job-ingestion",
            execution_id="exec_001",
            execution_start_time=now,
            status="running",
            layer="bronze",
        )
        self.components.append("PipelineExecutionMetadata")

        logger.info("schemas validated, count={}", len(self.components))

    def initialize_validators(self) -> None:
        """Exercise every validator to confirm they work."""
        logger.info("Phase 1: validating quality framework")

        now = datetime.now(tz=UTC)
        test_data: dict[str, Any] = {
            "job_id": "test_001",
            "source": "indeed",
            "source_job_id": "indeed_12345",
            "company_name": "TestCorp",
            "job_title": "Software Engineer",
            "job_description": "Looking for a talented engineer.",
            "location": {"country": "US", "city": "San Francisco"},
            "employment_type": "full_time",
            "posted_date": now,
            "last_modified_date": now,
            "dex_hash": "hash123",
        }

        is_valid, errs = SchemaValidator.validate_job_posting(test_data)
        logger.info("SchemaValidator check valid={} errors={}", is_valid, len(errs))
        self.components.append("SchemaValidator")

        required = set(self.settings.quality.required_fields)
        is_complete, missing = DataQualityChecks.check_completeness(test_data, required)
        logger.info("completeness check complete={} missing={}", is_complete, missing)
        self.components.append("DataQualityChecks")

        hash_val = DataHash.generate_job_hash(
            "indeed_12345", "indeed", "TestCorp", "Software Engineer"
        )
        logger.info("DataHash generated prefix={}", hash_val[:16])
        self.components.append("DataHash")

        score = QualityScorer.score_job_posting(test_data)
        logger.info("QualityScorer result score={:.2f}", score)
        self.components.append("QualityScorer")

    def initialize_medallion(self) -> None:
        """Configure medallion architecture layers and storage."""
        logger.info("Phase 1: initialising medallion architecture")

        layers = MedallionArchitecture.get_all_layers()
        layer_names = [layer.layer_name for layer in layers]
        logger.info("medallion layers=%s", layer_names)

        storage_cfg = self.settings.storage
        DualStorage(
            local_base_path=storage_cfg.local_base_path,
            bigquery_project=None,
            enable_bigquery=False,
        )
        self.components.append("DualStorage")

        DataLineage()
        self.components.append("DataLineage")

        for layer in layers:
            logger.info(
                "layer name={} threshold={} retention={}",
                layer.layer_name,
                layer.quality_threshold,
                layer.retention_days,
            )

    def initialize_pipeline_config(self) -> None:
        """Verify pipeline config is loadable."""
        logger.info("Phase 1: verifying pipeline configuration")

        logger.info(
            "pipeline schedule={} cycle_min={} jobs={}",
            PipelineConfig.EXECUTION_SCHEDULE,
            PipelineConfig.EXPECTED_CYCLE_TIME_MINUTES,
            PipelineConfig.EXPECTED_JOBS_PER_CYCLE,
        )
        self.components.append("PipelineConfig")

    # ------------------------------------------------------------------
    # Bootstrap
    # ------------------------------------------------------------------

    def bootstrap(self) -> dict[str, Any]:
        """Execute the full Phase 1 bootstrap.

        Returns:
            Summary dict with status, components initialised, and any errors.
        """
        logger.info("CAREERDEX PHASE 1 FOUNDATION — bootstrap started ts={}", self.timestamp)

        steps = [
            ("schemas", self.initialize_schemas),
            ("validators", self.initialize_validators),
            ("medallion", self.initialize_medallion),
            ("pipeline_config", self.initialize_pipeline_config),
        ]
        step_results: list[dict[str, Any]] = []
        for name, fn in steps:
            ok = self._run_step(name, fn)
            step_results.append({"name": name, "status": "success" if ok else "failed"})

        overall = "success" if all(s["status"] == "success" for s in step_results) else "failed"

        summary = {
            "phase": "Phase 1 Foundation",
            "timestamp": self.timestamp,
            "status": overall,
            "steps": step_results,
            "components": self.components,
            "errors": self.errors,
        }

        logger.info(
            "PHASE 1 BOOTSTRAP COMPLETE status={} components={} errors={}",
            overall,
            len(self.components),
            len(self.errors),
        )
        return summary


# ------------------------------------------------------------------
# Sample data generation — DEVELOPMENT AND TESTING ONLY
#
# WARNING: This data is synthetic. These are fictional companies
# and fabricated job postings for schema validation during bootstrap.
# This data must NEVER be served to users or treated as real.
# ------------------------------------------------------------------

_SAMPLE_COMPANIES = [
    ("Acme Corp", "Data Engineer", "San Francisco", "Build scalable data pipelines."),
    ("Globex", "ML Engineer", "New York", "Design and deploy ML models at scale."),
    ("Initech", "Backend Developer", "Austin", "Develop high-performance APIs."),
    ("Hooli", "Data Scientist", "Seattle", "Analyse petabytes of user data."),
    ("Pied Piper", "DevOps Engineer", "Palo Alto", "Automate cloud infrastructure."),
]

_SOURCES = ["indeed", "linkedin", "glassdoor", "company_career_pages"]


def get_sample_jobs() -> list[dict[str, Any]]:
    """Return synthetic job postings for development and testing ONLY.

    WARNING: This returns fabricated data with fictional companies.
    Never expose this data through production API endpoints.
    """
    logger.warning("get_sample_jobs() returns SYNTHETIC data — do not use in production")
    jobs: list[dict[str, Any]] = []
    for i, (company, title, city, desc) in enumerate(_SAMPLE_COMPANIES):
        jobs.append(
            {
                "job_id": f"sample_{i:03d}",
                "source": _SOURCES[i % len(_SOURCES)],
                "source_job_id": f"src_{i:05d}",
                "company_name": company,
                "job_title": title,
                "job_description": desc,
                "location": {
                    "country": "US",
                    "city": city,
                    "remote_eligible": i % 3 == 0,
                },
                "employment_type": "full_time",
                "posted_date": datetime(2026, 1, 15, tzinfo=UTC).isoformat(),
                "last_modified_date": datetime(2026, 1, 15, tzinfo=UTC).isoformat(),
                "dex_hash": DataHash.generate_job_hash(
                    f"src_{i:05d}", _SOURCES[i % len(_SOURCES)], company, title
                ),
            }
        )
    return jobs


def bootstrap_phase1(config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Convenience function to bootstrap Phase 1."""
    return Phase1Foundation(config).bootstrap()
