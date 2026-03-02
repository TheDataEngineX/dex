"""
Data Quality Gate & Store (Issue #33 — Data Quality Framework)

Provides ``QualityGate`` for enforcing quality thresholds at medallion layer
boundaries and ``QualityStore`` for accumulating quality metrics over time.

Classes:
    QualityDimension: Enumeration of quality dimension names.
    QualityResult: Immutable result of a single quality evaluation.
    QualityStore: In-memory store accumulating per-layer quality metrics.
    QualityGate: Orchestrates quality checks at medallion layer transitions.

Usage::

    from dataenginex.core.quality import QualityGate, QualityStore

    store = QualityStore()
    gate = QualityGate(store=store)

    # Evaluate a batch of records against the silver-layer threshold
    result = gate.evaluate(records, layer=DataLayer.SILVER)
    if result.passed:
        # promote to silver
        ...
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from loguru import logger

from dataenginex.core.medallion_architecture import DataLayer, MedallionArchitecture
from dataenginex.core.validators import DataQualityChecks, QualityScorer
from dataenginex.data.profiler import DataProfiler, ProfileReport

__all__ = [
    "QualityDimension",
    "QualityGate",
    "QualityResult",
    "QualityStore",
]


class QualityDimension(StrEnum):
    """Named quality dimensions tracked by the quality framework."""

    COMPLETENESS = "completeness"
    ACCURACY = "accuracy"
    CONSISTENCY = "consistency"
    TIMELINESS = "timeliness"
    UNIQUENESS = "uniqueness"


@dataclass(frozen=True)
class QualityResult:
    """Immutable result of evaluating a batch through a ``QualityGate``.

    Attributes:
        passed: Whether the batch met the layer's quality threshold.
        layer: Target medallion layer that was evaluated.
        quality_score: Overall quality score (0.0–1.0).
        threshold: Layer threshold the batch was compared against.
        record_count: Number of records in the batch.
        valid_count: Number of records that passed schema validation.
        dimensions: Per-dimension scores.
        profile: Optional ``ProfileReport`` produced during evaluation.
        evaluated_at: Timestamp of the evaluation.
    """

    passed: bool
    layer: str
    quality_score: float
    threshold: float
    record_count: int
    valid_count: int
    dimensions: dict[str, float]
    profile: ProfileReport | None = None
    evaluated_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))

    def to_dict(self) -> dict[str, Any]:
        """Serialise the result to a plain dictionary."""
        return {
            "passed": self.passed,
            "layer": self.layer,
            "quality_score": round(self.quality_score, 4),
            "threshold": self.threshold,
            "record_count": self.record_count,
            "valid_count": self.valid_count,
            "dimensions": {k: round(v, 4) for k, v in self.dimensions.items()},
            "evaluated_at": self.evaluated_at.isoformat(),
        }


class QualityStore:
    """In-memory store that accumulates quality metrics per medallion layer.

    Each call to :meth:`record` appends a snapshot.  :meth:`summary` returns
    the latest-known scores across all layers, suitable for the
    ``/api/v1/data/quality`` endpoint.
    """

    def __init__(self) -> None:
        self._history: dict[str, list[QualityResult]] = {
            DataLayer.BRONZE: [],
            DataLayer.SILVER: [],
            DataLayer.GOLD: [],
        }

    def record(self, result: QualityResult) -> None:
        """Persist a quality result for its layer."""
        layer = result.layer
        if layer not in self._history:
            self._history[layer] = []
        self._history[layer].append(result)
        logger.info(
            "Quality result recorded",
            layer=layer,
            score=round(result.quality_score, 4),
            passed=result.passed,
        )

    def latest(self, layer: str) -> QualityResult | None:
        """Return the most recent result for *layer*, or ``None``."""
        results = self._history.get(layer, [])
        return results[-1] if results else None

    def summary(self) -> dict[str, Any]:
        """Return a quality summary across all layers.

        The shape matches the ``/api/v1/data/quality`` response contract.
        """
        layer_scores: dict[str, float] = {}
        all_dimensions: dict[str, list[float]] = {}

        for layer_name in (DataLayer.BRONZE, DataLayer.SILVER, DataLayer.GOLD):
            latest = self.latest(layer_name)
            if latest is None:
                layer_scores[layer_name] = 0.0
                continue
            layer_scores[layer_name] = round(latest.quality_score, 4)
            for dim, val in latest.dimensions.items():
                all_dimensions.setdefault(dim, []).append(val)

        # Average each dimension across layers that have data
        avg_dimensions: dict[str, float] = {}
        for dim, vals in all_dimensions.items():
            avg_dimensions[dim] = round(sum(vals) / len(vals), 4) if vals else 0.0

        # Ensure all standard dimensions are present
        for dim in QualityDimension:
            avg_dimensions.setdefault(dim.value, 0.0)

        overall = round(sum(layer_scores.values()) / len(layer_scores), 4) if layer_scores else 0.0

        return {
            "overall_score": overall,
            "dimensions": avg_dimensions,
            "layer_scores": layer_scores,
        }

    def history(self, layer: str, limit: int = 10) -> list[dict[str, Any]]:
        """Return the last *limit* results for *layer* as dicts."""
        results = self._history.get(layer, [])
        return [r.to_dict() for r in results[-limit:]]


class QualityGate:
    """Orchestrates quality checks at medallion layer transitions.

    Combines ``DataProfiler``, ``DataQualityChecks``, and ``QualityScorer``
    to produce a single pass/fail ``QualityResult`` for a batch of records.

    Args:
        store: Optional ``QualityStore`` to persist results automatically.
        profiler: Optional ``DataProfiler`` instance (created if omitted).
    """

    def __init__(
        self,
        store: QualityStore | None = None,
        profiler: DataProfiler | None = None,
    ) -> None:
        self._store = store
        self._profiler = profiler or DataProfiler()

    @property
    def store(self) -> QualityStore | None:
        """Return the attached quality store, if any."""
        return self._store

    def evaluate(
        self,
        records: list[dict[str, Any]],
        layer: DataLayer,
        *,
        required_fields: set[str] | None = None,
        dataset_name: str = "batch",
    ) -> QualityResult:
        """Evaluate a batch of records against a layer's quality threshold.

        Steps performed:
        1. Profile the dataset (``DataProfiler``).
        2. Check completeness for each record (``DataQualityChecks``).
        3. Score each record (``QualityScorer``).
        4. Check uniqueness across the batch.
        5. Compute per-dimension averages and overall score.
        6. Compare overall score to the layer's ``quality_threshold``.

        Args:
            records: List of record dicts to evaluate.
            layer: Target ``DataLayer`` (bronze / silver / gold).
            required_fields: Field names required for completeness check.
                Falls back to ``{"job_id", "source", "company_name", "job_title"}``.
            dataset_name: Name passed to the profiler.

        Returns:
            A ``QualityResult`` indicating pass/fail and detailed scores.
        """
        config = MedallionArchitecture.get_layer_config(layer)
        threshold = config.quality_threshold if config else 0.0

        if not records:
            result = QualityResult(
                passed=True,
                layer=layer.value,
                quality_score=0.0,
                threshold=threshold,
                record_count=0,
                valid_count=0,
                dimensions={d.value: 0.0 for d in QualityDimension},
            )
            if self._store:
                self._store.record(result)
            return result

        # 1. Profile
        profile = self._profiler.profile(records, dataset_name)

        # 2. Required-field defaults
        if required_fields is None:
            required_fields = {"job_id", "source", "company_name", "job_title"}

        # 3. Per-record evaluation
        completeness_scores: list[float] = []
        quality_scores: list[float] = []
        valid_count = 0
        seen_ids: set[str] = set()
        unique_count = 0

        for rec in records:
            # Completeness
            ok, _missing = DataQualityChecks.check_completeness(rec, required_fields)
            completeness_scores.append(1.0 if ok else 0.0)
            if ok:
                valid_count += 1

            # Quality score
            quality_scores.append(QualityScorer.score_job_posting(rec))

            # Uniqueness
            rid = str(rec.get("job_id", id(rec)))
            is_unique, _ = DataQualityChecks.check_uniqueness_job_id(rid, seen_ids)
            if is_unique:
                unique_count += 1
                seen_ids.add(rid)

        total = len(records)
        dim_completeness = sum(completeness_scores) / total
        dim_accuracy = sum(quality_scores) / total
        dim_uniqueness = unique_count / total
        dim_consistency = profile.completeness  # proxy via null-rate
        dim_timeliness = 1.0  # placeholder — requires timestamp analysis

        dimensions = {
            QualityDimension.COMPLETENESS.value: dim_completeness,
            QualityDimension.ACCURACY.value: dim_accuracy,
            QualityDimension.CONSISTENCY.value: dim_consistency,
            QualityDimension.UNIQUENESS.value: dim_uniqueness,
            QualityDimension.TIMELINESS.value: dim_timeliness,
        }

        overall = sum(dimensions.values()) / len(dimensions)
        passed = overall >= threshold

        result = QualityResult(
            passed=passed,
            layer=layer.value,
            quality_score=overall,
            threshold=threshold,
            record_count=total,
            valid_count=valid_count,
            dimensions=dimensions,
            profile=profile,
        )

        if self._store:
            self._store.record(result)

        logger.info(
            "Quality gate evaluated",
            layer=layer.value,
            score=round(overall, 4),
            threshold=threshold,
            passed=passed,
            records=total,
        )

        return result
