"""Tests for dataenginex.core.quality — QualityGate, QualityStore, QualityResult."""

from __future__ import annotations

from typing import Any

from dataenginex.core.medallion_architecture import DataLayer
from dataenginex.core.quality import (
    QualityDimension,
    QualityGate,
    QualityResult,
    QualityStore,
)

from careerdex.core.validators import QualityScorer

# Default CareerDEX required fields — used to replicate old hardcoded defaults
_JOB_REQUIRED_FIELDS = {"job_id", "source", "company_name", "job_title"}


def _careerdex_gate(
    store: QualityStore | None = None,
) -> QualityGate:
    """Return a QualityGate configured for CareerDEX job records."""
    return QualityGate(
        store=store,
        scorer=QualityScorer.score_job_posting,
        required_fields=_JOB_REQUIRED_FIELDS,
        uniqueness_key="job_id",
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _job_record(**overrides: Any) -> dict[str, Any]:
    """Return a minimal valid job record, with optional overrides."""
    base: dict[str, Any] = {
        "job_id": "j_1",
        "source": "linkedin",
        "company_name": "Acme Corp",
        "job_title": "Software Engineer",
        "job_description": "A" * 250,
        "employment_type": "full_time",
        "location": {"city": "Seattle"},
        "required_skills": ["Python"],
        "benefits": {"salary_min": 80000, "salary_max": 140000, "benefits": ["health"]},
        "posted_date": "2025-01-01",
        "last_modified_date": "2025-01-02",
    }
    base.update(overrides)
    return base


def _batch(count: int = 5) -> list[dict[str, Any]]:
    return [_job_record(job_id=f"j_{i}") for i in range(count)]


# ---------------------------------------------------------------------------
# QualityResult
# ---------------------------------------------------------------------------


class TestQualityResult:
    def test_to_dict_contains_keys(self) -> None:
        result = QualityResult(
            passed=True,
            layer="silver",
            quality_score=0.85,
            threshold=0.75,
            record_count=10,
            valid_count=9,
            dimensions={"completeness": 0.9, "accuracy": 0.8},
        )
        d = result.to_dict()
        assert d["passed"] is True
        assert d["layer"] == "silver"
        assert d["quality_score"] == 0.85
        assert "evaluated_at" in d

    def test_frozen_dataclass(self) -> None:
        result = QualityResult(
            passed=True,
            layer="bronze",
            quality_score=0.5,
            threshold=0.0,
            record_count=1,
            valid_count=1,
            dimensions={},
        )
        # frozen — should raise on assignment
        try:
            result.passed = False  # type: ignore[misc]
            assert False, "Should have raised"  # noqa: B011
        except AttributeError:
            pass


# ---------------------------------------------------------------------------
# QualityStore
# ---------------------------------------------------------------------------


class TestQualityStore:
    def test_empty_summary(self) -> None:
        store = QualityStore()
        summary = store.summary()
        assert summary["overall_score"] == 0.0
        assert summary["layer_scores"]["bronze"] == 0.0
        assert "completeness" in summary["dimensions"]

    def test_record_and_latest(self) -> None:
        store = QualityStore()
        r = QualityResult(
            passed=True,
            layer="silver",
            quality_score=0.8,
            threshold=0.75,
            record_count=5,
            valid_count=5,
            dimensions={"completeness": 0.9},
        )
        store.record(r)
        latest = store.latest("silver")
        assert latest is not None
        assert latest.quality_score == 0.8

    def test_latest_returns_none_for_empty(self) -> None:
        store = QualityStore()
        assert store.latest("gold") is None

    def test_summary_with_data(self) -> None:
        store = QualityStore()
        store.record(
            QualityResult(
                passed=True,
                layer="bronze",
                quality_score=0.5,
                threshold=0.0,
                record_count=10,
                valid_count=10,
                dimensions={"completeness": 0.8, "accuracy": 0.6},
            )
        )
        store.record(
            QualityResult(
                passed=True,
                layer="silver",
                quality_score=0.9,
                threshold=0.75,
                record_count=10,
                valid_count=9,
                dimensions={"completeness": 0.95, "accuracy": 0.85},
            )
        )
        s = store.summary()
        assert s["layer_scores"]["bronze"] == 0.5
        assert s["layer_scores"]["silver"] == 0.9
        assert s["overall_score"] > 0.0

    def test_history(self) -> None:
        store = QualityStore()
        for i in range(3):
            store.record(
                QualityResult(
                    passed=True,
                    layer="gold",
                    quality_score=0.8 + i * 0.05,
                    threshold=0.9,
                    record_count=1,
                    valid_count=1,
                    dimensions={},
                )
            )
        hist = store.history("gold", limit=2)
        assert len(hist) == 2


# ---------------------------------------------------------------------------
# QualityGate
# ---------------------------------------------------------------------------


class TestQualityGate:
    def test_evaluate_empty_batch(self) -> None:
        gate = QualityGate()
        result = gate.evaluate([], layer=DataLayer.BRONZE)
        assert result.passed is True
        assert result.record_count == 0

    def test_evaluate_bronze_always_passes(self) -> None:
        """Bronze has threshold 0.0 — any data passes."""
        gate = _careerdex_gate()
        records = [{"job_id": "1", "source": "x", "company_name": "A", "job_title": "B"}]
        result = gate.evaluate(records, layer=DataLayer.BRONZE)
        assert result.passed is True
        assert result.threshold == 0.0

    def test_evaluate_silver_with_good_data(self) -> None:
        gate = _careerdex_gate()
        records = _batch(10)
        result = gate.evaluate(records, layer=DataLayer.SILVER)
        assert result.record_count == 10
        assert result.quality_score > 0.0
        assert result.dimensions["completeness"] > 0.0

    def test_evaluate_gold_with_sparse_data(self) -> None:
        """Gold requires ≥ 0.9 — sparse records should fail."""
        gate = _careerdex_gate()
        records = [{"job_id": str(i)} for i in range(5)]
        result = gate.evaluate(records, layer=DataLayer.GOLD)
        assert result.passed is False
        assert result.threshold == 0.9

    def test_evaluate_stores_result(self) -> None:
        store = QualityStore()
        gate = _careerdex_gate(store=store)
        gate.evaluate(_batch(3), layer=DataLayer.SILVER)
        assert store.latest("silver") is not None

    def test_evaluate_custom_required_fields(self) -> None:
        gate = QualityGate()
        records = [{"a": 1, "b": 2}]
        result = gate.evaluate(
            records,
            layer=DataLayer.BRONZE,
            required_fields={"a", "b"},
        )
        assert result.dimensions["completeness"] == 1.0

    def test_evaluate_uniqueness_with_duplicates(self) -> None:
        gate = _careerdex_gate()
        records = [
            _job_record(job_id="dup"),
            _job_record(job_id="dup"),
            _job_record(job_id="unique"),
        ]
        result = gate.evaluate(records, layer=DataLayer.SILVER)
        # Only 2 out of 3 are unique
        assert result.dimensions["uniqueness"] < 1.0

    def test_quality_dimensions_present(self) -> None:
        gate = _careerdex_gate()
        result = gate.evaluate(_batch(2), layer=DataLayer.BRONZE)
        for dim in QualityDimension:
            assert dim.value in result.dimensions

    def test_profile_attached(self) -> None:
        gate = _careerdex_gate()
        result = gate.evaluate(_batch(5), layer=DataLayer.SILVER)
        assert result.profile is not None
        assert result.profile.record_count == 5

    def test_store_property(self) -> None:
        store = QualityStore()
        gate = _careerdex_gate(store=store)
        assert gate.store is store

    def test_gate_without_store(self) -> None:
        gate = _careerdex_gate()
        assert gate.store is None
        # Should not raise even without a store
        result = gate.evaluate(_batch(1), layer=DataLayer.BRONZE)
        assert result.passed is True
