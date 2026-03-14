"""Tests for dataenginex.warehouse — transforms and lineage."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from dataenginex.warehouse.lineage import PersistentLineage
from dataenginex.warehouse.transforms import (
    AddTimestampTransform,
    CastTypesTransform,
    DropNullsTransform,
    FilterTransform,
    RenameFieldsTransform,
    TransformPipeline,
    TransformResult,
)

# ============================================================================
# Transforms
# ============================================================================


class TestRenameFieldsTransform:
    def test_renames(self) -> None:
        t = RenameFieldsTransform({"old": "new"})
        result = t.apply({"old": 1, "keep": 2})
        assert result == {"new": 1, "keep": 2}

    def test_missing_key(self) -> None:
        t = RenameFieldsTransform({"nothere": "new"})
        result = t.apply({"a": 1})
        assert result == {"a": 1}


class TestDropNullsTransform:
    def test_keeps_complete_records(self) -> None:
        t = DropNullsTransform(["a", "b"])
        assert t.apply({"a": 1, "b": 2}) is not None

    def test_drops_null_records(self) -> None:
        t = DropNullsTransform(["a"])
        assert t.apply({"a": None}) is None

    def test_drops_missing_records(self) -> None:
        t = DropNullsTransform(["a"])
        assert t.apply({"b": 1}) is None


class TestCastTypesTransform:
    def test_cast_int(self) -> None:
        t = CastTypesTransform({"val": "int"})
        assert t.apply({"val": "42"})["val"] == 42

    def test_cast_float(self) -> None:
        t = CastTypesTransform({"val": "float"})
        assert t.apply({"val": "3.14"})["val"] == pytest.approx(3.14)

    def test_cast_bool(self) -> None:
        t = CastTypesTransform({"val": "bool"})
        assert t.apply({"val": 1})["val"] is True

    def test_bad_cast_no_crash(self) -> None:
        t = CastTypesTransform({"val": "int"})
        result = t.apply({"val": "not_a_number"})
        assert result["val"] == "not_a_number"  # unchanged


class TestAddTimestampTransform:
    def test_adds_field(self) -> None:
        t = AddTimestampTransform("ts")
        result = t.apply({"a": 1})
        assert "ts" in result


class TestFilterTransform:
    def test_keeps_matching(self) -> None:
        t = FilterTransform("pos", lambda r: r.get("v", 0) > 0)
        assert t.apply({"v": 5}) is not None

    def test_drops_non_matching(self) -> None:
        t = FilterTransform("pos", lambda r: r.get("v", 0) > 0)
        assert t.apply({"v": -1}) is None


class TestTransformPipeline:
    def test_pipeline_runs(self) -> None:
        p = TransformPipeline("test")
        p.add(DropNullsTransform(["id"]))
        p.add(CastTypesTransform({"id": "int"}))

        records: list[dict[str, Any]] = [
            {"id": "1", "name": "a"},
            {"id": None, "name": "b"},
            {"id": "3", "name": "c"},
        ]
        result = p.run(records)
        assert result.input_count == 3
        assert result.output_count == 2
        assert result.dropped_count == 1
        assert result.records[0]["id"] == 1
        assert len(result.step_metrics) == 2

    def test_empty_pipeline(self) -> None:
        p = TransformPipeline("empty")
        result = p.run([{"a": 1}])
        assert result.output_count == 1

    def test_success_rate(self) -> None:
        result = TransformResult(input_count=10, output_count=8)
        assert result.success_rate == pytest.approx(0.8)


# ============================================================================
# Lineage
# ============================================================================


class TestPersistentLineage:
    def test_record_and_get(self) -> None:
        lin = PersistentLineage()
        ev = lin.record(operation="ingest", layer="bronze", source="linkedin", input_count=100)
        assert ev.operation == "ingest"
        got = lin.get_event(ev.event_id)
        assert got is not None
        assert got.event_id == ev.event_id

    def test_chain(self) -> None:
        lin = PersistentLineage()
        e1 = lin.record(operation="ingest", layer="bronze")
        e2 = lin.record(operation="transform", layer="silver", parent_id=e1.event_id)
        e3 = lin.record(operation="enrich", layer="gold", parent_id=e2.event_id)
        chain = lin.get_chain(e3.event_id)
        assert len(chain) == 3
        assert chain[0].event_id == e1.event_id

    def test_get_by_layer(self) -> None:
        lin = PersistentLineage()
        lin.record(operation="ingest", layer="bronze")
        lin.record(operation="transform", layer="silver")
        assert len(lin.get_by_layer("bronze")) == 1

    def test_summary(self) -> None:
        lin = PersistentLineage()
        lin.record(operation="ingest", layer="bronze")
        lin.record(operation="ingest", layer="bronze")
        s = lin.summary()
        assert s["total_events"] == 2
        assert s["by_layer"]["bronze"] == 2

    def test_persistence(self, tmp_path: Path) -> None:
        path = tmp_path / "lineage.json"
        lin = PersistentLineage(path)
        lin.record(operation="ingest", layer="bronze", source="test")
        # Reload
        lin2 = PersistentLineage(path)
        assert len(lin2.all_events) == 1
