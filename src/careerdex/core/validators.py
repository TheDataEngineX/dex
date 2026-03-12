"""CareerDEX domain validators — schema validation, quality scoring, hashing.

Extracted from ``dataenginex.core.validators`` because these validators encode
CareerDEX domain knowledge (job postings, user profiles, salary ranges, job IDs)
that does not belong in a generic data-engineering framework.

Generic checks (``check_completeness``, ``check_consistency_dates``, ``ValidationReport``)
remain in ``dataenginex.core.validators``.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from typing import Any

from loguru import logger

from careerdex.core.schemas import JobPosting, UserProfile

# Configure loguru
logger.enable("careerdex")

__all__ = [
    "CareerDEXQualityChecks",
    "DataHash",
    "QualityScorer",
    "SchemaValidator",
]


class SchemaValidator:
    """Validates that data conforms to CareerDEX schema specifications."""

    @staticmethod
    def validate_job_posting(
        data: Mapping[str, Any],
    ) -> tuple[bool, list[str]]:
        """Validate job posting data against JobPosting schema.

        Args:
            data: Dictionary containing job posting data.

        Returns:
            Tuple of (is_valid, error_messages).
        """
        errors: list[str] = []
        try:
            JobPosting(**data)
            return True, []
        except Exception as e:
            errors.append(str(e))
            return False, errors

    @staticmethod
    def validate_user_profile(
        data: dict[str, Any],
    ) -> tuple[bool, list[str]]:
        """Validate user profile data against UserProfile schema."""
        errors: list[str] = []
        try:
            UserProfile(**data)
            return True, []
        except Exception as e:
            errors.append(str(e))
            return False, errors


class CareerDEXQualityChecks:
    """CareerDEX-specific data quality checks.

    For generic checks (completeness, date consistency), use
    ``dataenginex.core.validators.DataQualityChecks``.
    """

    @staticmethod
    def check_accuracy_salary(
        salary_min: float | None,
        salary_max: float | None,
    ) -> tuple[bool, list[str]]:
        """Check salary range accuracy and reasonableness.

        Thresholds:
            - salary_max > 500_000: flagged as unreasonably high
            - salary_min < 15_000: flagged as below US minimum wage equivalent

        Returns:
            Tuple of (is_accurate, issues).
        """
        issues: list[str] = []

        if salary_min is not None and salary_max is not None:
            if salary_min > salary_max:
                issues.append(f"Salary min ({salary_min}) > max ({salary_max})")
            # 500_000 — reasonable upper bound for most positions
            if salary_max > 500_000:
                issues.append(f"Salary max ({salary_max}) exceeds reasonable threshold")
            # 15_000 — below US minimum wage annual equivalent
            if salary_min < 15_000:
                issues.append(f"Salary min ({salary_min}) below reasonable threshold")

        return len(issues) == 0, issues

    @staticmethod
    def check_uniqueness_job_id(
        current_id: str,
        seen_ids: set[str],
    ) -> tuple[bool, str]:
        """Check if job ID is unique in the batch.

        Returns:
            Tuple of (is_unique, issue_message).
        """
        if current_id in seen_ids:
            return False, f"Duplicate job ID: {current_id}"
        return True, ""

    @staticmethod
    def check_validity_location(
        country: str,
        city: str,
        latitude: float | None = None,
        longitude: float | None = None,
    ) -> tuple[bool, list[str]]:
        """Check location validity.

        Returns:
            Tuple of (is_valid, issues).
        """
        issues: list[str] = []

        if len(country) != 2:
            issues.append(f"Country code should be 2 chars, got: {country}")

        if not city or len(city) < 2:
            issues.append("City name is too short")

        if latitude is not None and not (-90 <= latitude <= 90):
            issues.append(f"Latitude out of range: {latitude}")

        if longitude is not None and not (-180 <= longitude <= 180):
            issues.append(f"Longitude out of range: {longitude}")

        return len(issues) == 0, issues


class DataHash:
    """Generates content hashes for CareerDEX deduplication."""

    @staticmethod
    def generate_job_hash(
        job_id: str,
        source: str,
        company_name: str,
        job_title: str,
    ) -> str:
        """Generate a SHA-256 hash for job posting deduplication.

        Uses job_id + source + company + title as content identifier.

        Args:
            job_id: Source job ID.
            source: Job source (linkedin, indeed, etc.).
            company_name: Company name.
            job_title: Job title.

        Returns:
            SHA-256 hash hex digest.
        """
        content = f"{source}:{company_name}:{job_title}:{job_id}"
        return hashlib.sha256(content.encode()).hexdigest()

    @staticmethod
    def generate_user_hash(
        email: str,
        first_name: str,
        last_name: str,
    ) -> str:
        """Generate a SHA-256 hash for user profile deduplication.

        Returns:
            SHA-256 hash hex digest.
        """
        content = f"{email}:{first_name.lower()}:{last_name.lower()}"
        return hashlib.sha256(content.encode()).hexdigest()


class QualityScorer:
    """Calculates quality scores for CareerDEX data records."""

    @staticmethod
    def _score_salary(record: dict[str, Any]) -> float:
        """Award score for salary info. Returns 0.1 or 0.0."""
        benefits = record.get("benefits", {})
        if benefits.get("salary_min") and benefits.get("salary_max"):
            return 0.1
        return 0.0

    @staticmethod
    def _score_location(record: dict[str, Any]) -> float:
        """Award score for location. Returns 0.1 or 0.0."""
        if record.get("location", {}).get("city"):
            return 0.1
        return 0.0

    @staticmethod
    def _score_skills(record: dict[str, Any]) -> float:
        """Award score for skills. Returns 0.15 or 0.0."""
        if record.get("required_skills"):
            return 0.15
        return 0.0

    @staticmethod
    def _score_description(record: dict[str, Any]) -> float:
        """Award score for description. Returns 0.2 or 0.0."""
        job_desc = record.get("job_description", "")
        if job_desc and len(job_desc) > 200:
            return 0.2
        return 0.0

    @staticmethod
    def _score_dates(record: dict[str, Any]) -> float:
        """Award score for dates. Returns 0.1 or 0.0."""
        try:
            posted = record.get("posted_date")
            modified = record.get("last_modified_date")
            if posted and modified and posted <= modified:
                return 0.1
        except TypeError:
            logger.debug("Date comparison failed for record")
        return 0.0

    @staticmethod
    def _score_company(record: dict[str, Any]) -> float:
        """Award score for company. Returns 0.1 or 0.0."""
        if record.get("company_name"):
            return 0.1
        return 0.0

    @staticmethod
    def _score_employment(record: dict[str, Any]) -> float:
        """Award score for employment type. Returns 0.1 or 0.0."""
        if record.get("employment_type"):
            return 0.1
        return 0.0

    @staticmethod
    def _score_benefits(record: dict[str, Any]) -> float:
        """Award score for benefits. Returns 0.05 or 0.0."""
        if record.get("benefits", {}).get("benefits"):
            return 0.05
        return 0.0

    @staticmethod
    def score_job_posting(record: dict[str, Any]) -> float:
        """Calculate quality score for job posting (0–1 scale).

        Scoring criteria:
            - Has salary range: +0.10
            - Has location details: +0.10
            - Has skill requirements: +0.15
            - Has job description (>200 chars): +0.20
            - Has reasonable dates: +0.10
            - Has company info: +0.10
            - Has employment type: +0.10
            - Has benefits listed: +0.05

        Args:
            record: Job posting record dict.

        Returns:
            Quality score (0.0–1.0).
        """
        score = (
            QualityScorer._score_salary(record)
            + QualityScorer._score_location(record)
            + QualityScorer._score_skills(record)
            + QualityScorer._score_description(record)
            + QualityScorer._score_dates(record)
            + QualityScorer._score_company(record)
            + QualityScorer._score_employment(record)
            + QualityScorer._score_benefits(record)
        )
        return min(score, 1.0)

    @staticmethod
    def score_user_profile(record: dict[str, Any]) -> float:
        """Calculate quality score for user profile (0–1 scale).

        Scoring criteria:
            - Has email: +0.15
            - Has name: +0.10
            - Has professional info: +0.20
            - Has skills: +0.15
            - Has experience: +0.10
            - Has preferences: +0.15
            - Profile completion >50%: +0.15

        Returns:
            Quality score (0.0–1.0).
        """
        score = 0.0

        if record.get("email"):
            score += 0.15

        if record.get("first_name") and record.get("last_name"):
            score += 0.1

        if record.get("current_title") or record.get("current_company"):
            score += 0.2

        if record.get("skills"):
            score += 0.15

        if record.get("years_experience"):
            score += 0.1

        if record.get("preferred_job_titles") or record.get("preferred_locations"):
            score += 0.15

        if record.get("profile_completion_percentage", 0) > 50:
            score += 0.15

        return min(score, 1.0)
