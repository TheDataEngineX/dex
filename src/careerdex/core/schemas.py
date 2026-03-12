"""CareerDEX domain schemas — job postings, user profiles, pipeline metadata.

These are CareerDEX-specific data models that were extracted from the generic
``dataenginex`` framework. They live here because they encode domain knowledge
(job sources, salary, skills, user preferences) that does not belong in a
reusable data-engineering toolkit.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, EmailStr, Field

__all__ = [
    "DataQualityReport",
    "JobBenefits",
    "JobLocation",
    "JobPosting",
    "JobSourceEnum",
    "PipelineExecutionMetadata",
    "UserProfile",
]


class JobSourceEnum(StrEnum):
    """Supported external job-data sources for CareerDEX."""

    LINKEDIN = "linkedin"
    INDEED = "indeed"
    GLASSDOOR = "glassdoor"
    COMPANY_CAREER_PAGES = "company_career_pages"
    LOCAL_JSON = "local_json"
    LOCAL_CSV = "local_csv"


class JobLocation(BaseModel):
    """Job location details."""

    country: str = Field(
        ...,
        min_length=2,
        max_length=2,
        description="ISO 3166-1 alpha-2 country code",
    )
    state: str | None = Field(None, max_length=50)
    city: str = Field(..., max_length=100)
    zipcode: str | None = Field(None, max_length=20)
    latitude: float | None = Field(None, ge=-90, le=90)
    longitude: float | None = Field(None, ge=-180, le=180)
    remote_eligible: bool = Field(False, description="Whether position supports remote work")


class JobBenefits(BaseModel):
    """Job compensation and benefits."""

    salary_min: float | None = Field(None, ge=0, description="Minimum salary in USD")
    salary_max: float | None = Field(None, ge=0, description="Maximum salary in USD")
    salary_currency: str = Field("USD", max_length=3)
    equity_offered: bool = Field(False)
    sign_on_bonus: float | None = Field(None, ge=0)
    bonus_percentage: float | None = Field(None, ge=0, le=100)
    benefits: list[str] = Field(
        default_factory=list,
        description="List of benefits (401k, health insurance, etc.)",
    )


class JobPosting(BaseModel):
    """Core job posting schema for CareerDEX (Silver layer)."""

    job_id: str = Field(..., description="Unique job identifier across all sources")
    source: JobSourceEnum = Field(..., description="Data source of job posting")
    source_job_id: str = Field(..., description="Original ID from source system")

    # Company info
    company_name: str = Field(..., min_length=1, max_length=255)
    company_industry: str | None = Field(None, max_length=100)
    company_size: str | None = Field(None, description="e.g., '1-50', '51-200', '200-1000'")

    # Position details
    job_title: str = Field(..., min_length=3, max_length=255)
    job_description: str = Field(..., min_length=10)
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    experience_level: str | None = Field(
        None, description="entry_level, mid_level, senior, executive"
    )
    years_experience_required: int | None = Field(None, ge=0)

    # Employment
    location: JobLocation = Field(...)
    employment_type: str = Field(..., description="full_time, part_time, contract, temporary")

    # Compensation
    benefits: JobBenefits | None = Field(default=None)

    # Metadata
    posted_date: datetime = Field(..., description="When job was posted on source")
    last_modified_date: datetime = Field(...)
    expiration_date: datetime | None = Field(None)

    # Tracking
    dex_ingestion_date: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
    dex_hash: str = Field(..., description="Content hash for deduplication")
    dex_dedup_id: str | None = Field(None, description="Deduplication group ID")
    quality_score: float = Field(
        default=0.0, ge=0, le=1.0, description="Job quality/relevance score"
    )


class UserProfile(BaseModel):
    """CareerDEX user profile schema."""

    user_id: str = Field(..., description="Unique user identifier")
    email: EmailStr = Field(...)
    first_name: str = Field(..., max_length=100)
    last_name: str = Field(..., max_length=100)

    # Professional info
    current_title: str | None = Field(None, max_length=255)
    current_company: str | None = Field(None, max_length=255)
    years_experience: int | None = Field(None, ge=0)
    skills: list[str] = Field(default_factory=list)

    # Education
    education: str | None = Field(None, description="Highest education level")
    preferred_locations: list[str] = Field(default_factory=list, description="City, country codes")

    # Preferences
    preferred_job_titles: list[str] = Field(default_factory=list)
    salary_expectations: dict[str, float] | None = Field(None)
    willing_to_relocate: bool = Field(False)

    # Engagement
    created_date: datetime = Field(...)
    last_activity_date: datetime = Field(...)
    profile_completion_percentage: float = Field(default=0.0, ge=0, le=100)


class PipelineExecutionMetadata(BaseModel):
    """Tracks pipeline execution for lineage and troubleshooting."""

    pipeline_name: str = Field(...)
    execution_id: str = Field(..., description="Unique execution identifier")
    execution_start_time: datetime = Field(...)
    execution_end_time: datetime | None = Field(None)
    status: str = Field(..., description="running, succeeded, failed, partial")
    source_count: int = Field(default=0, ge=0)
    processed_count: int = Field(default=0, ge=0)
    ingested_count: int = Field(default=0, ge=0)
    failed_count: int = Field(default=0, ge=0)
    error_message: str | None = Field(None)
    layer: str = Field(..., description="bronze, silver, or gold")


class DataQualityReport(BaseModel):
    """Data quality check results."""

    execution_id: str = Field(...)
    check_timestamp: datetime = Field(...)
    dataset_name: str = Field(...)
    total_records: int = Field(default=0, ge=0)
    passed_records: int = Field(default=0, ge=0)
    failed_records: int = Field(default=0, ge=0)
    quality_score: float = Field(default=0.0, ge=0, le=100)
    check_results: dict[str, Any] = Field(default_factory=dict)
    issues: list[str] = Field(default_factory=list)
