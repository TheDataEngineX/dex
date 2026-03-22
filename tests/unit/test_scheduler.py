"""Tests for the built-in cron scheduler."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from dataenginex.orchestration.builtin import BuiltinScheduler


class TestBuiltinScheduler:
    def test_add_schedule(self) -> None:
        sched = BuiltinScheduler()
        sched.schedule("pipeline-a", "*/5 * * * *")
        assert "pipeline-a" in sched.schedules

    def test_next_run_time(self) -> None:
        sched = BuiltinScheduler()
        sched.schedule("pipeline-a", "*/5 * * * *")
        next_time = sched.next_run("pipeline-a")
        assert next_time > datetime(2000, 1, 1, tzinfo=UTC)

    def test_due_pipelines(self) -> None:
        sched = BuiltinScheduler()
        sched.schedule("pipeline-a", "*/1 * * * *")
        # Force last_run to be far in the past
        sched.schedules["pipeline-a"].last_run = datetime(2020, 1, 1, tzinfo=UTC)
        due = sched.get_due()
        assert "pipeline-a" in due

    def test_mark_complete(self) -> None:
        sched = BuiltinScheduler()
        sched.schedule("pipeline-a", "*/1 * * * *")
        sched.schedules["pipeline-a"].last_run = datetime(2020, 1, 1, tzinfo=UTC)
        sched.mark_complete("pipeline-a")
        assert sched.schedules["pipeline-a"].last_run > datetime(2020, 1, 1, tzinfo=UTC)

    def test_trigger_returns_run_id(self) -> None:
        sched = BuiltinScheduler()
        run_id = sched.trigger("my-pipeline")
        assert len(run_id) > 0
        status = sched.status(run_id)
        assert status["pipeline"] == "my-pipeline"
        assert status["status"] == "triggered"

    def test_cancel_run(self) -> None:
        sched = BuiltinScheduler()
        run_id = sched.trigger("my-pipeline")
        sched.cancel(run_id)
        assert sched.status(run_id)["status"] == "cancelled"

    def test_invalid_cron_raises(self) -> None:
        sched = BuiltinScheduler()
        with pytest.raises(ValueError, match="Invalid cron"):
            sched.schedule("bad", "not a cron")
