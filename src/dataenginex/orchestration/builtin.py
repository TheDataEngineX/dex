"""Built-in cron scheduler — croniter-based.

Simple scheduler for single-node deployments. Stores last-run timestamps
in memory. For production: use [dagster] or [airflow] extras.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import structlog
from croniter import croniter  # type: ignore[import-untyped]

from dataenginex.core.interfaces import BaseOrchestrator
from dataenginex.orchestration import orchestrator_registry

logger = structlog.get_logger()


@dataclass
class ScheduleEntry:
    """A single schedule definition."""

    pipeline: str
    cron: str
    last_run: datetime = field(default_factory=lambda: datetime(2000, 1, 1, tzinfo=UTC))


@orchestrator_registry.decorator("builtin", is_default=True)
class BuiltinScheduler(BaseOrchestrator):
    """Cron-based scheduler using croniter.

    Implements BaseOrchestrator interface. Designed for `dex run --schedule`
    mode where the main loop polls every minute.
    """

    def __init__(self) -> None:
        self.schedules: dict[str, ScheduleEntry] = {}
        self._runs: dict[str, dict[str, Any]] = {}

    # --- BaseOrchestrator interface ---

    def schedule(self, pipeline_name: str, cron: str) -> None:
        """Schedule a pipeline with a cron expression."""
        if not croniter.is_valid(cron):
            msg = f"Invalid cron expression: {cron}"
            raise ValueError(msg)
        self.schedules[pipeline_name] = ScheduleEntry(pipeline=pipeline_name, cron=cron)
        logger.info("schedule added", pipeline=pipeline_name, cron=cron)

    def trigger(self, pipeline_name: str) -> str:
        """Trigger an immediate run, return run ID."""
        run_id = str(uuid.uuid4())[:8]
        self._runs[run_id] = {
            "pipeline": pipeline_name,
            "status": "triggered",
            "triggered_at": datetime.now(tz=UTC).isoformat(),
        }
        logger.info("pipeline triggered", pipeline=pipeline_name, run_id=run_id)
        return run_id

    def status(self, run_id: str) -> dict[str, Any]:
        """Get status of a run."""
        if run_id not in self._runs:
            msg = f"Run '{run_id}' not found"
            raise KeyError(msg)
        return self._runs[run_id]

    def cancel(self, run_id: str) -> None:
        """Cancel a running pipeline."""
        if run_id in self._runs:
            self._runs[run_id]["status"] = "cancelled"
            logger.info("run cancelled", run_id=run_id)

    # --- Scheduler-specific methods ---

    def next_run(self, pipeline_name: str) -> datetime:
        """Get the next run time for a pipeline."""
        entry = self.schedules[pipeline_name]
        cron = croniter(entry.cron, entry.last_run)
        raw_next: datetime = cron.get_next(datetime)
        if raw_next.tzinfo is None:
            raw_next = raw_next.replace(tzinfo=UTC)
        return raw_next

    def get_due(self) -> list[str]:
        """Return list of pipelines that are due to run."""
        now = datetime.now(tz=UTC)
        due = []
        for name in self.schedules:
            next_time = self.next_run(name)
            if next_time <= now:
                due.append(name)
        return due

    def mark_complete(self, pipeline_name: str) -> None:
        """Mark a pipeline as completed (updates last_run)."""
        self.schedules[pipeline_name].last_run = datetime.now(tz=UTC)
