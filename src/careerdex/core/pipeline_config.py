"""CareerDEX pipeline configuration — schedule, sources, metrics.

Extracted from ``dataenginex.core.pipeline_config`` because this module
is 100% CareerDEX-specific: job sources, job volume targets, job metrics.
A generic data-engineering framework should not prescribe job-board specifics.
"""

from __future__ import annotations

__all__ = [
    "PipelineConfig",
    "PipelineMetrics",
]


class PipelineConfig:
    """Configuration for CareerDEX data pipelines."""

    # Pipeline execution constants
    EXECUTION_SCHEDULE = "0 */3 * * *"  # Every 3 hours
    EXPECTED_CYCLE_TIME_MINUTES = 45  # Expected runtime per cycle
    TIMEOUT_MINUTES = 120  # Kill pipeline if running >2 hours

    # Job ingestion sources and target volumes
    CAREERDEX_JOB_SOURCES: dict[str, dict[str, object]] = {
        "linkedin": {
            "type": "rest_api",
            "expected_daily_jobs": 10000,
            "cycles_per_day": 8,  # 24h / 3h
            "expected_cycle_jobs": 1250,
            "timeout_seconds": 900,
        },
        "indeed": {
            "type": "rest_api",
            "expected_daily_jobs": 50000,
            "cycles_per_day": 8,
            "expected_cycle_jobs": 6250,
            "timeout_seconds": 1200,
        },
        "glassdoor": {
            "type": "rest_api",
            "expected_daily_jobs": 20000,
            "cycles_per_day": 8,
            "expected_cycle_jobs": 2500,
            "timeout_seconds": 1000,
        },
        "company_career_pages": {
            "type": "scraper",
            "expected_daily_jobs": 30000,
            "cycles_per_day": 8,
            "expected_cycle_jobs": 3750,
            "timeout_seconds": 1500,
        },
    }

    # Total expected jobs per cycle: 13,750 posts
    EXPECTED_JOBS_PER_CYCLE: int = 13750  # 1250 + 6250 + 2500 + 3750

    # Total expected jobs in system (live): ~110K per day
    EXPECTED_JOBS_TOTAL: int = 110000  # 10000 + 50000 + 20000 + 30000


class PipelineMetrics:
    """Metrics tracking for CareerDEX pipeline monitoring."""

    METRICS: dict[str, dict[str, object]] = {
        "jobs_fetched": {
            "description": "Total jobs fetched from all sources",
            "type": "counter",
            "unit": "count",
        },
        "jobs_ingested": {
            "description": "Jobs successfully ingested into system",
            "type": "counter",
            "unit": "count",
        },
        "jobs_deduplicated": {
            "description": "Duplicate jobs detected and marked",
            "type": "counter",
            "unit": "count",
        },
        "jobs_enriched": {
            "description": "Jobs with embeddings and enrichments",
            "type": "counter",
            "unit": "count",
        },
        "data_quality_score": {
            "description": "Average quality score of ingested jobs",
            "type": "gauge",
            "unit": "percentage",
            "target": 85,  # Target 85%+
        },
        "pipeline_duration": {
            "description": "Total execution time for pipeline",
            "type": "histogram",
            "unit": "seconds",
            "target_max": 2700,  # 45 minute target
        },
        "bronze_to_silver_loss": {
            "description": "Percentage of data lost in cleaning",
            "type": "gauge",
            "unit": "percentage",
            "target_max": 5,  # Max 5% loss acceptable
        },
        "silver_to_gold_loss": {
            "description": "Percentage of data lost in enrichment",
            "type": "gauge",
            "unit": "percentage",
            "target_max": 2,  # Max 2% loss acceptable
        },
    }
