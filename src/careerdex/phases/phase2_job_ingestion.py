"""CareerDEX Phase 2: Real-Time Job Ingestion (Issue #66).

Implements job data fetching from four sources, deduplication, quality
scoring, and Bronze-layer storage via the DataEngineX framework.

Sources:
    1. LinkedIn API — OAuth2, paginated search
    2. Indeed — Scrapy / Playwright scraping
    3. Glassdoor — Selenium headless scraping
    4. Company Career Pages — ATS API adapters (Greenhouse, Lever)

All connectors share the ``JobSourceConnector`` ABC so they can be
swapped, tested, and orchestrated uniformly.

**Status:** All ``fetch()`` methods raise ``NotImplementedError`` —
real integrations must be implemented before this pipeline produces data.
"""

from __future__ import annotations

import abc
import csv
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from loguru import logger

from careerdex.core.exceptions import StubNotImplementedError
from careerdex.core.schemas import JobSourceEnum
from careerdex.core.settings import get_settings
from careerdex.core.validators import DataHash, QualityScorer

__all__ = [
    "CompanyCareerPagesConnector",
    "CsvFileConnector",
    "DeduplicationEngine",
    "GlassdoorConnector",
    "IndeedConnector",
    "JobIngestionPipeline",
    "JobSourceConnector",
    "JsonFileConnector",
    "LinkedInConnector",
]


# ======================================================================
# Abstract connector
# ======================================================================


class JobSourceConnector(abc.ABC):
    """Abstract base for all job-source connectors."""

    def __init__(self, source: JobSourceEnum) -> None:
        self.source = source
        self.fetch_count = 0
        self.error_count = 0

    @abc.abstractmethod
    def fetch(self, **kwargs: Any) -> tuple[list[dict[str, Any]], list[str]]:
        """Fetch jobs from the source.

        Returns:
            ``(jobs, errors)`` — list of raw job dicts and error messages.
        """

    @abc.abstractmethod
    def normalize(self, raw_job: dict[str, Any]) -> dict[str, Any]:
        """Normalise a raw job dict to the CareerDEX schema."""

    def _make_job_id(self, source_job_id: str) -> str:
        """Deterministic internal job ID from source + source_job_id."""
        raw = f"{self.source.value}:{source_job_id}"
        return hashlib.sha256(raw.encode()).hexdigest()[:24]


# ======================================================================
# Concrete connectors
# ======================================================================


class LinkedInConnector(JobSourceConnector):
    """Fetches jobs via the LinkedIn Jobs API (OAuth2).

    Rate limit: ~4 800 requests / 24 h (~80/min sustained).

    **Status:** ``fetch()`` raises ``StubNotImplementedError`` —
    implement real LinkedIn API integration with httpx + OAuth2.
    """

    def __init__(self, api_key: str | None = None) -> None:
        super().__init__(JobSourceEnum.LINKEDIN)
        self.api_key = api_key
        settings = get_settings()
        source_cfg = settings.sources.get("linkedin")
        if source_cfg is None:
            msg = "LinkedIn source not configured in job_config.json"
            raise ValueError(msg)
        self.api_endpoint = source_cfg.api_endpoint or "https://api.linkedin.com/v2/jobs"
        self.batch_size = source_cfg.batch_size
        self.target_jobs_per_cycle = source_cfg.expected_jobs_per_cycle

    def fetch(self, **kwargs: Any) -> tuple[list[dict[str, Any]], list[str]]:
        """Fetch jobs from LinkedIn API.

        Raises:
            StubNotImplementedError: Always — real implementation required.
                Implement using ``httpx.AsyncClient`` with OAuth2 bearer
                tokens, pagination, and exponential-backoff retries.
        """
        raise StubNotImplementedError(
            "LinkedInConnector.fetch() is a stub. "
            "Implement real LinkedIn API integration using httpx + OAuth2. "
            "See: https://learn.microsoft.com/en-us/linkedin/talent/job-postings"
        )

    def normalize(self, raw_job: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now(tz=UTC)
        source_job_id = str(raw_job.get("id", ""))
        company = raw_job.get("company", {}).get("name", "")
        title = raw_job.get("title", "")
        location = raw_job.get("location", {})
        return {
            "job_id": self._make_job_id(source_job_id),
            "source": self.source.value,
            "source_job_id": source_job_id,
            "job_title": title,
            "company_name": company,
            "job_description": raw_job.get("description", ""),
            "location": {
                "country": location.get("country", ""),
                "city": location.get("city", ""),
            },
            "employment_type": raw_job.get("employment_type", ""),
            "posted_date": now,
            "last_modified_date": now,
            "dex_hash": DataHash.generate_job_hash(
                source_job_id, self.source.value, company, title
            ),
        }


class IndeedConnector(JobSourceConnector):
    """Scrapes jobs from Indeed (Scrapy + Playwright).

    **Status:** ``fetch()`` raises ``StubNotImplementedError``.
    """

    def __init__(self) -> None:
        super().__init__(JobSourceEnum.INDEED)
        settings = get_settings()
        source_cfg = settings.sources.get("indeed")
        if source_cfg is None:
            msg = "Indeed source not configured in job_config.json"
            raise ValueError(msg)
        self.base_url = source_cfg.base_url or "https://www.indeed.com"
        self.batch_size = source_cfg.batch_size
        self.target_jobs_per_cycle = source_cfg.expected_jobs_per_cycle

    def fetch(self, **kwargs: Any) -> tuple[list[dict[str, Any]], list[str]]:
        """Raises ``StubNotImplementedError`` — implement Indeed scraping."""
        raise StubNotImplementedError(
            "IndeedConnector.fetch() is a stub. "
            "Implement real Indeed scraping using Scrapy + Playwright."
        )

    def normalize(self, raw_job: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now(tz=UTC)
        source_job_id = str(raw_job.get("job_key", ""))
        company = raw_job.get("company", "")
        title = raw_job.get("jobtitle", "")
        return {
            "job_id": self._make_job_id(source_job_id),
            "source": self.source.value,
            "source_job_id": source_job_id,
            "job_title": title,
            "company_name": company,
            "job_description": raw_job.get("snippet", ""),
            "location": {
                "country": raw_job.get("country", ""),
                "city": raw_job.get("location", ""),
            },
            "employment_type": raw_job.get("employment_type", ""),
            "posted_date": now,
            "last_modified_date": now,
            "dex_hash": DataHash.generate_job_hash(
                source_job_id, self.source.value, company, title
            ),
        }


class GlassdoorConnector(JobSourceConnector):
    """Scrapes jobs from Glassdoor (Selenium headless).

    **Status:** ``fetch()`` raises ``StubNotImplementedError``.
    """

    def __init__(self) -> None:
        super().__init__(JobSourceEnum.GLASSDOOR)
        settings = get_settings()
        source_cfg = settings.sources.get("glassdoor")
        if source_cfg is None:
            msg = "Glassdoor source not configured in job_config.json"
            raise ValueError(msg)
        self.base_url = source_cfg.base_url or "https://www.glassdoor.com"
        self.batch_size = source_cfg.batch_size
        self.target_jobs_per_cycle = source_cfg.expected_jobs_per_cycle

    def fetch(self, **kwargs: Any) -> tuple[list[dict[str, Any]], list[str]]:
        """Raises ``StubNotImplementedError`` — implement Glassdoor scraping."""
        raise StubNotImplementedError(
            "GlassdoorConnector.fetch() is a stub. "
            "Implement real Glassdoor scraping using Selenium headless."
        )

    def normalize(self, raw_job: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now(tz=UTC)
        source_job_id = str(raw_job.get("id", ""))
        company = raw_job.get("employer", {}).get("name", "")
        title = raw_job.get("jobTitle", "")
        location = raw_job.get("location", {})
        return {
            "job_id": self._make_job_id(source_job_id),
            "source": self.source.value,
            "source_job_id": source_job_id,
            "job_title": title,
            "company_name": company,
            "job_description": raw_job.get("description", ""),
            "location": {
                "country": location.get("country", ""),
                "city": location.get("city", ""),
            },
            "employment_type": raw_job.get("employmentType", ""),
            "posted_date": now,
            "last_modified_date": now,
            "dex_hash": DataHash.generate_job_hash(
                source_job_id, self.source.value, company, title
            ),
        }


class CompanyCareerPagesConnector(JobSourceConnector):
    """Fetches from ATS APIs (Greenhouse, Lever) and career-page scraping.

    **Status:** ``fetch()`` raises ``StubNotImplementedError``.
    """

    def __init__(self) -> None:
        super().__init__(JobSourceEnum.COMPANY_CAREER_PAGES)
        settings = get_settings()
        source_cfg = settings.sources.get("company_career_pages")
        if source_cfg is None:
            msg = "company_career_pages source not configured in job_config.json"
            raise ValueError(msg)
        if source_cfg.ats_apis is not None:
            self.ats_apis = {
                "greenhouse": source_cfg.ats_apis.greenhouse,
                "lever": source_cfg.ats_apis.lever,
            }
        else:
            self.ats_apis = {}
        self.batch_size = source_cfg.batch_size
        self.target_jobs_per_cycle = source_cfg.expected_jobs_per_cycle

    def fetch(self, **kwargs: Any) -> tuple[list[dict[str, Any]], list[str]]:
        """Raises ``StubNotImplementedError`` — implement ATS API integration."""
        raise StubNotImplementedError(
            "CompanyCareerPagesConnector.fetch() is a stub. "
            "Implement real ATS API integration for Greenhouse and Lever."
        )

    def normalize(self, raw_job: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now(tz=UTC)
        source_job_id = str(raw_job.get("id", ""))
        company = raw_job.get("company", "")
        title = raw_job.get("title", "")
        return {
            "job_id": self._make_job_id(source_job_id),
            "source": self.source.value,
            "source_job_id": source_job_id,
            "job_title": title,
            "company_name": company,
            "job_description": raw_job.get("description", ""),
            "location": {
                "country": raw_job.get("country", ""),
                "city": raw_job.get("location", ""),
            },
            "employment_type": raw_job.get("employment_type", ""),
            "posted_date": now,
            "last_modified_date": now,
            "dex_hash": DataHash.generate_job_hash(
                source_job_id, self.source.value, company, title
            ),
        }


# ======================================================================
# Local file connectors
# ======================================================================


class JsonFileConnector(JobSourceConnector):
    """Reads job postings from a local JSON file.

    The file must contain a JSON array of objects, each with at least
    ``id``, ``company``, ``title``, and ``description`` keys.

    Example::

        connector = JsonFileConnector(Path("jobs.json"))
        jobs, errors = connector.fetch()
    """

    def __init__(self, file_path: str | Path) -> None:
        super().__init__(JobSourceEnum.LOCAL_JSON)
        self.file_path = Path(file_path)

    def fetch(self, **kwargs: Any) -> tuple[list[dict[str, Any]], list[str]]:
        """Read and parse job records from a JSON file."""
        errors: list[str] = []
        if not self.file_path.exists():
            errors.append(f"File not found: {self.file_path}")
            return [], errors
        try:
            raw_text = self.file_path.read_text(encoding="utf-8")
            data = json.loads(raw_text)
        except (json.JSONDecodeError, OSError) as exc:
            errors.append(f"Failed to read {self.file_path}: {exc}")
            return [], errors
        if not isinstance(data, list):
            errors.append(f"Expected JSON array, got {type(data).__name__}")
            return [], errors
        self.fetch_count = len(data)
        logger.info("json connector fetched {} records from {}", len(data), self.file_path)
        return data, errors

    def normalize(self, raw_job: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now(tz=UTC)
        source_job_id = str(raw_job.get("id", ""))
        company = raw_job.get("company", "")
        title = raw_job.get("title", "")
        location = raw_job.get("location", {})
        if isinstance(location, str):
            location = {"country": "", "city": location}
        return {
            "job_id": self._make_job_id(source_job_id),
            "source": self.source.value,
            "source_job_id": source_job_id,
            "job_title": title,
            "company_name": company,
            "job_description": raw_job.get("description", ""),
            "location": {
                "country": location.get("country", ""),
                "city": location.get("city", ""),
            },
            "employment_type": raw_job.get("employment_type", "full_time"),
            "posted_date": now,
            "last_modified_date": now,
            "dex_hash": DataHash.generate_job_hash(
                source_job_id, self.source.value, company, title
            ),
        }


class CsvFileConnector(JobSourceConnector):
    """Reads job postings from a local CSV file.

    Expected columns: ``id``, ``company``, ``title``, ``description``,
    ``city``, ``country``, ``employment_type``.

    Example::

        connector = CsvFileConnector(Path("jobs.csv"))
        jobs, errors = connector.fetch()
    """

    def __init__(self, file_path: str | Path) -> None:
        super().__init__(JobSourceEnum.LOCAL_CSV)
        self.file_path = Path(file_path)

    def fetch(self, **kwargs: Any) -> tuple[list[dict[str, Any]], list[str]]:
        """Read and parse job records from a CSV file."""
        errors: list[str] = []
        if not self.file_path.exists():
            errors.append(f"File not found: {self.file_path}")
            return [], errors
        try:
            with self.file_path.open(encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                data = list(reader)
        except OSError as exc:
            errors.append(f"Failed to read {self.file_path}: {exc}")
            return [], errors
        self.fetch_count = len(data)
        logger.info("csv connector fetched {} records from {}", len(data), self.file_path)
        return data, errors

    def normalize(self, raw_job: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now(tz=UTC)
        source_job_id = str(raw_job.get("id", ""))
        company = raw_job.get("company", "")
        title = raw_job.get("title", "")
        return {
            "job_id": self._make_job_id(source_job_id),
            "source": self.source.value,
            "source_job_id": source_job_id,
            "job_title": title,
            "company_name": company,
            "job_description": raw_job.get("description", ""),
            "location": {
                "country": raw_job.get("country", ""),
                "city": raw_job.get("city", ""),
            },
            "employment_type": raw_job.get("employment_type", "full_time"),
            "posted_date": now,
            "last_modified_date": now,
            "dex_hash": DataHash.generate_job_hash(
                source_job_id, self.source.value, company, title
            ),
        }


# ======================================================================
# Deduplication
# ======================================================================


class DeduplicationEngine:
    """Content-hash-based deduplication across all sources."""

    def __init__(self) -> None:
        self._seen_hashes: set[str] = set()

    def deduplicate(self, jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Remove duplicate jobs based on ``dex_hash``.

        Args:
            jobs: List of normalised job dicts.

        Returns:
            De-duplicated list (preserves first occurrence).
        """
        unique: list[dict[str, Any]] = []
        for job in jobs:
            h = job.get("dex_hash", "")
            if h and h not in self._seen_hashes:
                self._seen_hashes.add(h)
                unique.append(job)

        removed = len(jobs) - len(unique)
        if removed:
            logger.info("dedup removed {} duplicates from {} total", removed, len(jobs))
        return unique

    @property
    def seen_count(self) -> int:
        return len(self._seen_hashes)


# ======================================================================
# Ingestion pipeline
# ======================================================================


class JobIngestionPipeline:
    """Orchestrates a single ingestion cycle across all sources.

    Steps:
        1. Fetch from all connectors in parallel (connectors are sync stubs
           here; in production they use ``asyncio.gather``).
        2. Normalise raw records.
        3. Deduplicate across sources.
        4. Score quality.
        5. Store to Bronze layer (via DataEngineX ``DualStorage``).
    """

    def __init__(
        self,
        connectors: list[JobSourceConnector] | None = None,
    ) -> None:
        self.connectors = connectors or [
            LinkedInConnector(),
            IndeedConnector(),
            GlassdoorConnector(),
            CompanyCareerPagesConnector(),
        ]
        self.dedup = DeduplicationEngine()

    def run_cycle(self) -> dict[str, Any]:
        """Execute one ingestion cycle.

        Returns:
            Cycle summary with per-source counts and quality stats.
        """
        start = datetime.now(tz=UTC)
        logger.info("ingestion cycle started at {}", start.isoformat())

        all_jobs: list[dict[str, Any]] = []
        all_errors: list[str] = []
        per_source: dict[str, int] = {}

        for conn in self.connectors:
            try:
                raw_jobs, errors = conn.fetch()
            except (StubNotImplementedError, NotImplementedError) as exc:
                logger.warning(
                    "connector %s is a stub: %s",
                    conn.source.value,
                    exc,
                )
                all_errors.append(f"{conn.source.value}: {exc}")
                per_source[conn.source.value] = 0
                continue
            normalised = [conn.normalize(j) for j in raw_jobs]
            per_source[conn.source.value] = len(normalised)
            all_jobs.extend(normalised)
            all_errors.extend(errors)

        # Deduplicate
        unique_jobs = self.dedup.deduplicate(all_jobs)

        # Score quality
        scored = 0
        for job in unique_jobs:
            job["quality_score"] = QualityScorer.score_job_posting(job)
            scored += 1

        elapsed = (datetime.now(tz=UTC) - start).total_seconds()

        summary = {
            "cycle_start": start.isoformat(),
            "elapsed_seconds": round(elapsed, 2),
            "per_source": per_source,
            "total_fetched": len(all_jobs),
            "after_dedup": len(unique_jobs),
            "scored": scored,
            "errors": all_errors,
        }

        logger.info(
            "ingestion cycle complete fetched={} unique={} scored={} errors={} elapsed={:.1f}s",
            len(all_jobs),
            len(unique_jobs),
            scored,
            len(all_errors),
            elapsed,
        )
        return summary
