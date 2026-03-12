"""Tests for data quality validators."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from dataenginex.core.validators import (
    DataQualityChecks,
    ValidationReport,
)

from careerdex.core.validators import (
    CareerDEXQualityChecks,
    DataHash,
    QualityScorer,
    SchemaValidator,
)

# ---------------------------------------------------------------------------
# SchemaValidator
# ---------------------------------------------------------------------------


def _valid_job_data() -> dict[str, Any]:
    now = datetime.now(tz=UTC).isoformat()
    return {
        "job_id": "test_123",
        "source": "linkedin",
        "source_job_id": "src_123",
        "company_name": "Acme Corp",
        "job_title": "Software Engineer",
        "job_description": "Build amazing software systems at scale",
        "location": {"country": "US", "city": "New York"},
        "employment_type": "full_time",
        "posted_date": now,
        "last_modified_date": now,
        "dex_hash": "abc123hash",
    }


class TestSchemaValidator:
    def test_valid_job_posting(self) -> None:
        valid, errors = SchemaValidator.validate_job_posting(_valid_job_data())
        assert valid is True
        assert errors == []

    def test_invalid_job_posting_missing_field(self) -> None:
        data = _valid_job_data()
        del data["job_title"]
        valid, errors = SchemaValidator.validate_job_posting(data)
        assert valid is False
        assert len(errors) == 1

    def test_valid_user_profile(self) -> None:
        now = datetime.now(tz=UTC).isoformat()
        data = {
            "user_id": "u_1",
            "email": "test@example.com",
            "first_name": "Jane",
            "last_name": "Doe",
            "created_date": now,
            "last_activity_date": now,
        }
        valid, errors = SchemaValidator.validate_user_profile(data)
        assert valid is True
        assert errors == []

    def test_invalid_user_profile(self) -> None:
        valid, errors = SchemaValidator.validate_user_profile({})
        assert valid is False
        assert len(errors) == 1


# ---------------------------------------------------------------------------
# DataQualityChecks
# ---------------------------------------------------------------------------


class TestDataQualityChecks:
    def test_completeness_all_present(self) -> None:
        record = {"a": 1, "b": 2, "c": 3}
        ok, missing = DataQualityChecks.check_completeness(record, {"a", "b"})
        assert ok is True
        assert missing == []

    def test_completeness_missing_field(self) -> None:
        record = {"a": 1}
        ok, missing = DataQualityChecks.check_completeness(record, {"a", "b"})
        assert ok is False
        assert "b" in missing

    def test_completeness_none_value(self) -> None:
        record = {"a": None}
        ok, missing = DataQualityChecks.check_completeness(record, {"a"})
        assert ok is False
        assert "a" in missing

    def test_accuracy_salary_valid(self) -> None:
        ok, issues = CareerDEXQualityChecks.check_accuracy_salary(50000.0, 100000.0)
        assert ok is True
        assert issues == []

    def test_accuracy_salary_min_gt_max(self) -> None:
        ok, issues = CareerDEXQualityChecks.check_accuracy_salary(100000.0, 50000.0)
        assert ok is False
        assert any("min" in i.lower() or ">" in i for i in issues)

    def test_accuracy_salary_above_threshold(self) -> None:
        ok, issues = CareerDEXQualityChecks.check_accuracy_salary(50000.0, 600000.0)
        assert ok is False
        assert any("threshold" in i.lower() for i in issues)

    def test_accuracy_salary_below_threshold(self) -> None:
        ok, issues = CareerDEXQualityChecks.check_accuracy_salary(10000.0, 50000.0)
        assert ok is False
        assert any("below" in i.lower() for i in issues)

    def test_consistency_dates_valid(self) -> None:
        now = datetime.now(tz=UTC)
        posted = now - timedelta(days=10)
        modified = now - timedelta(days=5)
        ok, issues = DataQualityChecks.check_consistency_dates(posted, modified)
        assert ok is True
        assert issues == []

    def test_consistency_dates_posted_after_modified(self) -> None:
        now = datetime.now(tz=UTC)
        posted = now
        modified = now - timedelta(days=5)
        ok, issues = DataQualityChecks.check_consistency_dates(posted, modified)
        assert ok is False
        assert any("after" in i.lower() for i in issues)

    def test_consistency_dates_expired_before_posted(self) -> None:
        now = datetime.now(tz=UTC)
        posted = now - timedelta(days=10)
        modified = now - timedelta(days=5)
        expiry = posted - timedelta(days=1)
        ok, issues = DataQualityChecks.check_consistency_dates(
            posted,
            modified,
            expiry,
        )
        assert ok is False
        assert any("before" in i.lower() for i in issues)

    def test_consistency_dates_future_posted(self) -> None:
        future = datetime.now(tz=UTC) + timedelta(days=5)
        ok, issues = DataQualityChecks.check_consistency_dates(future, future)
        assert ok is False
        assert any("future" in i.lower() for i in issues)

    def test_uniqueness_unique(self) -> None:
        ok, msg = CareerDEXQualityChecks.check_uniqueness_job_id("j1", {"j2", "j3"})
        assert ok is True
        assert msg == ""

    def test_uniqueness_duplicate(self) -> None:
        ok, msg = CareerDEXQualityChecks.check_uniqueness_job_id("j1", {"j1", "j2"})
        assert ok is False
        assert "Duplicate" in msg

    def test_validity_location_valid(self) -> None:
        ok, issues = CareerDEXQualityChecks.check_validity_location("US", "Seattle")
        assert ok is True
        assert issues == []

    def test_validity_location_bad_country(self) -> None:
        ok, issues = CareerDEXQualityChecks.check_validity_location("USA", "Seattle")
        assert ok is False
        assert any("Country" in i for i in issues)

    def test_validity_location_short_city(self) -> None:
        ok, issues = CareerDEXQualityChecks.check_validity_location("US", "")
        assert ok is False

    def test_validity_location_bad_coords(self) -> None:
        ok, issues = CareerDEXQualityChecks.check_validity_location(
            "US",
            "Seattle",
            latitude=100.0,
            longitude=200.0,
        )
        assert ok is False
        assert len(issues) == 2


# ---------------------------------------------------------------------------
# DataHash
# ---------------------------------------------------------------------------


class TestDataHash:
    def test_job_hash_deterministic(self) -> None:
        h1 = DataHash.generate_job_hash("1", "linkedin", "Acme", "SWE")
        h2 = DataHash.generate_job_hash("1", "linkedin", "Acme", "SWE")
        assert h1 == h2

    def test_job_hash_differs_for_different_input(self) -> None:
        h1 = DataHash.generate_job_hash("1", "linkedin", "Acme", "SWE")
        h2 = DataHash.generate_job_hash("2", "linkedin", "Acme", "SWE")
        assert h1 != h2

    def test_user_hash_deterministic(self) -> None:
        h1 = DataHash.generate_user_hash("a@b.com", "Jane", "Doe")
        h2 = DataHash.generate_user_hash("a@b.com", "Jane", "Doe")
        assert h1 == h2

    def test_user_hash_case_insensitive_name(self) -> None:
        h1 = DataHash.generate_user_hash("a@b.com", "Jane", "Doe")
        h2 = DataHash.generate_user_hash("a@b.com", "jane", "doe")
        assert h1 == h2


# ---------------------------------------------------------------------------
# QualityScorer
# ---------------------------------------------------------------------------


class TestQualityScorer:
    def test_empty_record_scores_zero(self) -> None:
        assert QualityScorer.score_job_posting({}) == 0.0

    def test_full_record_scores_high(self) -> None:
        record: dict[str, Any] = {
            "benefits": {"salary_min": 80000, "salary_max": 120000, "benefits": ["health"]},
            "location": {"city": "Seattle"},
            "required_skills": ["Python"],
            "job_description": "A" * 201,
            "posted_date": "2025-01-01",
            "last_modified_date": "2025-01-02",
            "company_name": "Acme Corp",
            "employment_type": "full-time",
        }
        score = QualityScorer.score_job_posting(record)
        assert score >= 0.85

    def test_partial_record(self) -> None:
        record: dict[str, Any] = {
            "company_name": "Acme Corp",
            "required_skills": ["Python"],
        }
        score = QualityScorer.score_job_posting(record)
        assert 0.0 < score < 1.0

    def test_user_profile_empty(self) -> None:
        assert QualityScorer.score_user_profile({}) == 0.0

    def test_user_profile_full(self) -> None:
        record: dict[str, Any] = {
            "email": "a@b.com",
            "first_name": "Jane",
            "last_name": "Doe",
            "current_title": "Engineer",
            "skills": ["Python"],
            "years_experience": 5,
            "preferred_job_titles": ["SWE"],
            "profile_completion_percentage": 80,
        }
        score = QualityScorer.score_user_profile(record)
        assert score == 1.0


# ---------------------------------------------------------------------------
# ValidationReport
# ---------------------------------------------------------------------------


class TestValidationReport:
    def test_add_error(self) -> None:
        r = ValidationReport()
        r.add_error("job1", "schema", "bad field")
        assert r.invalid_records == 1
        assert len(r.errors) == 1

    def test_add_warning(self) -> None:
        r = ValidationReport()
        r.add_warning("job1", "quality", "low score")
        assert len(r.warnings) == 1

    def test_mark_valid(self) -> None:
        r = ValidationReport()
        r.mark_valid()
        assert r.valid_records == 1

    def test_finalize_empty(self) -> None:
        report = ValidationReport().finalize()
        assert report["total_records"] == 0
        assert report["validity_percentage"] == 0

    def test_finalize_mixed(self) -> None:
        r = ValidationReport()
        r.mark_valid()
        r.mark_valid()
        r.add_error("j3", "schema", "bad")
        report = r.finalize()
        assert report["total_records"] == 3
        assert report["valid_records"] == 2
        assert report["invalid_records"] == 1
        assert 60 < report["validity_percentage"] < 70
