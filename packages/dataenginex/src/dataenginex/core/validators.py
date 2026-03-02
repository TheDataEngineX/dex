"""
Data Quality Validators (Issue #33 - Data Quality Framework)

This module provides validation and data quality checking utilities for DEX
using Pydantic validators and Great Expectations.

Classes:
    SchemaValidator: Validates records against Pydantic schemas.
    DataQualityChecks: Multi-dimensional data quality checks.
    DataHash: Content hashing for deduplication.
    QualityScorer: Computes quality scores for records.
    ValidationReport: Aggregates validation results.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from loguru import logger

from .schemas import JobPosting, UserProfile

# Configure loguru
logger.enable("dataenginex")

__all__ = [
    "DataHash",
    "DataQualityChecks",
    "QualityScorer",
    "SchemaValidator",
    "ValidationReport",
]


class SchemaValidator:
    """Validates that data conforms to DEX schema specifications."""

    @staticmethod
    def validate_job_posting(data: Mapping[str, Any]) -> tuple[bool, list[str]]:
        """
        Validate job posting data against JobPosting schema.

        Args:
            data: Dictionary containing job posting data

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        try:
            JobPosting(**data)
            return True, []
        except Exception as e:
            errors.append(str(e))
            return False, errors

    @staticmethod
    def validate_user_profile(data: dict[str, Any]) -> tuple[bool, list[str]]:
        """Validate user profile data against schema."""
        errors = []
        try:
            UserProfile(**data)
            return True, []
        except Exception as e:
            errors.append(str(e))
            return False, errors


class DataQualityChecks:
    """Implements data quality checks across multiple dimensions."""

    @staticmethod
    def check_completeness(
        record: dict[str, Any], required_fields: set[str]
    ) -> tuple[bool, list[str]]:
        """
        Check that all required fields are present and non-null.

        Args:
            record: Data record to check
            required_fields: Set of field names that must be present

        Returns:
            Tuple of (is_complete, missing_fields)
        """
        missing = []
        for field in required_fields:
            if field not in record or record[field] is None:
                missing.append(field)

        return len(missing) == 0, missing

    @staticmethod
    def check_accuracy_salary(
        salary_min: float | None, salary_max: float | None
    ) -> tuple[bool, list[str]]:
        """
        Check salary range accuracy and reasonableness.

        Returns:
            Tuple of (is_accurate, issues)
        """
        issues = []

        if salary_min is not None and salary_max is not None:
            if salary_min > salary_max:
                issues.append(f"Salary min ({salary_min}) > max ({salary_max})")
            if salary_max > 500000:  # Reasonable upper bound for most positions
                issues.append(f"Salary max ({salary_max}) exceeds reasonable threshold")
            if salary_min < 15000:  # Below US minimum wage equivalent
                issues.append(f"Salary min ({salary_min}) below reasonable threshold")

        return len(issues) == 0, issues

    @staticmethod
    def check_consistency_dates(
        posted_date: datetime,
        last_modified_date: datetime,
        expiration_date: datetime | None = None,
    ) -> tuple[bool, list[str]]:
        """
        Check temporal consistency of dates.

        Returns:
            Tuple of (is_consistent, issues)
        """
        issues = []

        if posted_date > last_modified_date:
            issues.append("Posted date is after last modified date")

        if expiration_date and expiration_date < posted_date:
            issues.append("Expiration date is before posted date")

        if posted_date > datetime.now(tz=UTC):
            issues.append("Posted date is in the future")

        return len(issues) == 0, issues

    @staticmethod
    def check_uniqueness_job_id(current_id: str, seen_ids: set[str]) -> tuple[bool, str]:
        """
        Check if job ID is unique in the batch.

        Returns:
            Tuple of (is_unique, issue_message)
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
        """
        Check location validity.

        Returns:
            Tuple of (is_valid, issues)
        """
        issues = []

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
    """Generates content hashes for deduplication (DEX requirement)."""

    @staticmethod
    def generate_job_hash(job_id: str, source: str, company_name: str, job_title: str) -> str:
        """
        Generate a hash for job posting content to identify duplicates.
        Uses job_id + source + company + title as content identifier.

        Args:
            job_id: Source job ID
            source: Job source (linkedin, indeed, etc.)
            company_name: Company name
            job_title: Job title

        Returns:
            SHA256 hash of content
        """
        content = f"{source}:{company_name}:{job_title}:{job_id}"
        return hashlib.sha256(content.encode()).hexdigest()

    @staticmethod
    def generate_user_hash(email: str, first_name: str, last_name: str) -> str:
        """
        Generate a hash for user profile to identify duplicates.

        Returns:
            SHA256 hash of user identity
        """
        content = f"{email}:{first_name.lower()}:{last_name.lower()}"
        return hashlib.sha256(content.encode()).hexdigest()


class QualityScorer:
    """Calculates quality scores for data records."""

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
        except Exception:
            pass
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
        """
        Calculate quality score for job posting (0-1 scale).

        Scoring criteria:
        - Has salary range: +0.1
        - Has location details: +0.1
        - Has skill requirements: +0.15
        - Has job description (>200 chars): +0.2
        - Has reasonable dates: +0.1
        - Has company info: +0.1
        - Has employment type: +0.1
        - Has benefits listed: +0.05

        Args:
            record: Job posting record

        Returns:
            Quality score (0.0 - 1.0)
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
        """
        Calculate quality score for user profile (0-1 scale).

        Scoring criteria:
        - Has email: +0.15
        - Has name: +0.1
        - Has professional info: +0.2
        - Has skills: +0.15
        - Has experience: +0.1
        - Has preferences: +0.15
        - Profile completion >50%: +0.15

        Returns:
            Quality score (0.0 - 1.0)
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


class ValidationReport:
    """Generates validation reports for data quality assessment."""

    def __init__(self) -> None:
        self.total_records = 0
        self.valid_records = 0
        self.invalid_records = 0
        self.errors: list[dict[str, Any]] = []
        self.warnings: list[dict[str, Any]] = []

    def add_error(self, record_id: str, error_type: str, message: str) -> None:
        """Record a validation error."""
        self.invalid_records += 1
        self.errors.append({"record_id": record_id, "type": error_type, "message": message})

    def add_warning(self, record_id: str, warning_type: str, message: str) -> None:
        """Record a validation warning."""
        self.warnings.append({"record_id": record_id, "type": warning_type, "message": message})

    def mark_valid(self) -> None:
        """Mark a record as valid."""
        self.valid_records += 1

    def finalize(self) -> dict[str, Any]:
        """Generate final validation report."""
        total = self.valid_records + self.invalid_records
        valid_pct = (self.valid_records / total * 100) if total > 0 else 0

        return {
            "total_records": total,
            "valid_records": self.valid_records,
            "invalid_records": self.invalid_records,
            "validity_percentage": valid_pct,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "errors": self.errors[:100],  # Top 100 errors
            "warnings": self.warnings[:100],  # Top 100 warnings
        }
