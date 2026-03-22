"""Conformance tests for BaseTracker implementations."""

from __future__ import annotations

from typing import Any

import pytest


class TrackerConformanceTests:
    """All BaseTracker implementations must pass these tests.

    Subclass and provide a ``tracker`` fixture.
    """

    @pytest.fixture()
    def tracker(self) -> Any:
        raise NotImplementedError

    def test_create_experiment(self, tracker: Any) -> None:
        exp_id = tracker.create_experiment("test-exp")
        assert isinstance(exp_id, str)
        assert len(exp_id) > 0

    def test_create_experiment_idempotent(self, tracker: Any) -> None:
        id1 = tracker.create_experiment("same-name")
        id2 = tracker.create_experiment("same-name")
        assert id1 == id2

    def test_start_and_end_run(self, tracker: Any) -> None:
        exp_id = tracker.create_experiment("run-test")
        run_id = tracker.start_run(exp_id)
        assert isinstance(run_id, str)
        tracker.end_run(run_id, status="FINISHED")

    def test_log_params(self, tracker: Any) -> None:
        exp_id = tracker.create_experiment("param-test")
        run_id = tracker.start_run(exp_id)
        tracker.log_params(run_id, {"lr": 0.01, "epochs": 10})
        tracker.end_run(run_id)

    def test_log_metrics(self, tracker: Any) -> None:
        exp_id = tracker.create_experiment("metric-test")
        run_id = tracker.start_run(exp_id)
        tracker.log_metrics(run_id, {"loss": 0.5, "accuracy": 0.85})
        tracker.end_run(run_id)

    def test_list_runs(self, tracker: Any) -> None:
        exp_id = tracker.create_experiment("list-test")
        tracker.start_run(exp_id, run_name="run-1")
        tracker.start_run(exp_id, run_name="run-2")
        runs = tracker.list_runs(exp_id)
        assert len(runs) >= 2

    def test_start_run_invalid_experiment(self, tracker: Any) -> None:
        with pytest.raises(KeyError):
            tracker.start_run("nonexistent")
