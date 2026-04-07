"""Tests for PipelineRunHistory."""

from __future__ import annotations

from pathlib import Path

import pytest

from dataenginex.data.pipeline.run_history import PipelineRunHistory
from dataenginex.data.pipeline.runner import PipelineResult


def test_record_creates_entry(tmp_path: Path) -> None:
    history = PipelineRunHistory(tmp_path / "runs.json")
    result = PipelineResult(
        pipeline="test", success=True, rows_input=100, rows_output=95, steps_completed=3
    )
    rec = history.record(result, duration_ms=42.5)
    assert rec.pipeline_name == "test"
    assert rec.success is True
    assert rec.rows_input == 100
    assert rec.rows_output == 95
    assert rec.duration_ms == pytest.approx(42.5)


def test_get_runs_filters_by_pipeline(tmp_path: Path) -> None:
    history = PipelineRunHistory(tmp_path / "runs.json")
    r1 = PipelineResult(pipeline="a", success=True)
    r2 = PipelineResult(pipeline="b", success=True)
    history.record(r1, duration_ms=10)
    history.record(r2, duration_ms=20)
    assert len(history.get_runs("a")) == 1
    assert len(history.get_runs("b")) == 1


def test_persistence_survives_reload(tmp_path: Path) -> None:
    path = tmp_path / "runs.json"
    h1 = PipelineRunHistory(path)
    h1.record(PipelineResult(pipeline="x", success=True), duration_ms=5)
    h2 = PipelineRunHistory(path)  # reload from disk
    assert len(h2.all_runs) == 1
    assert h2.all_runs[0].pipeline_name == "x"


def test_all_runs_returns_newest_first(tmp_path: Path) -> None:
    history = PipelineRunHistory(tmp_path / "runs.json")
    history.record(PipelineResult(pipeline="first", success=True), duration_ms=1)
    history.record(PipelineResult(pipeline="second", success=True), duration_ms=2)
    runs = history.all_runs
    assert runs[0].pipeline_name == "second"


def test_corrupted_json_starts_fresh(tmp_path: Path) -> None:
    path = tmp_path / "runs.json"
    path.write_text("NOT VALID JSON")
    history = PipelineRunHistory(path)
    assert len(history.all_runs) == 0
