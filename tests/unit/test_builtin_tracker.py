"""Tests for the built-in JSON-backed experiment tracker."""

from __future__ import annotations

import pytest

from dataenginex.ml.tracking.builtin import BuiltinTracker
from tests.conformance.test_tracker import TrackerConformanceTests


class TestBuiltinTracker(TrackerConformanceTests):
    @pytest.fixture()
    def tracker(self, tmp_path):
        return BuiltinTracker(storage_dir=str(tmp_path / "tracking"))

    def test_persistence(self, tmp_path) -> None:
        """Tracker state persists across instances."""
        storage = str(tmp_path / "persist-test")
        t1 = BuiltinTracker(storage_dir=storage)
        exp_id = t1.create_experiment("persist-exp")
        run_id = t1.start_run(exp_id)
        t1.log_metrics(run_id, {"acc": 0.95})
        t1.end_run(run_id)

        # New instance loads from disk
        t2 = BuiltinTracker(storage_dir=storage)
        runs = t2.list_runs(exp_id)
        assert len(runs) == 1
        assert runs[0]["status"] == "FINISHED"

    def test_log_metrics_with_steps(self, tmp_path) -> None:
        tracker = BuiltinTracker(storage_dir=str(tmp_path / "steps"))
        exp_id = tracker.create_experiment("step-test")
        run_id = tracker.start_run(exp_id)
        tracker.log_metrics(run_id, {"loss": 1.0}, step=0)
        tracker.log_metrics(run_id, {"loss": 0.5}, step=1)
        tracker.end_run(run_id)

        runs = tracker.list_runs(exp_id)
        assert len(runs[0]["metrics"]["loss"]) == 2

    def test_end_run_not_found(self, tmp_path) -> None:
        tracker = BuiltinTracker(storage_dir=str(tmp_path / "err"))
        with pytest.raises(KeyError):
            tracker.end_run("nonexistent")

    def test_log_params_not_found(self, tmp_path) -> None:
        tracker = BuiltinTracker(storage_dir=str(tmp_path / "err2"))
        with pytest.raises(KeyError):
            tracker.log_params("nonexistent", {"x": 1})

    def test_log_metrics_not_found(self, tmp_path) -> None:
        tracker = BuiltinTracker(storage_dir=str(tmp_path / "err3"))
        with pytest.raises(KeyError):
            tracker.log_metrics("nonexistent", {"x": 1.0})
