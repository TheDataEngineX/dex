"""Integration tests — data lineage tracking and pipeline + lineage interaction."""

from __future__ import annotations

import json
from pathlib import Path

from dataenginex.warehouse.lineage import LineageEvent, PersistentLineage

# ---------------------------------------------------------------------------
# PersistentLineage — basic operations
# ---------------------------------------------------------------------------


class TestPersistentLineageBasic:
    def test_record_creates_event(self) -> None:
        lineage = PersistentLineage()
        ev = lineage.record(operation="ingest", layer="bronze", source="csv", input_count=100)
        assert isinstance(ev, LineageEvent)
        assert ev.operation == "ingest"
        assert ev.layer == "bronze"

    def test_event_id_is_unique(self) -> None:
        lineage = PersistentLineage()
        ids = {lineage.record(operation="ingest").event_id for _ in range(10)}
        assert len(ids) == 10  # all unique

    def test_get_event_returns_correct_event(self) -> None:
        lineage = PersistentLineage()
        ev = lineage.record(operation="transform", layer="silver", source="bronze/pipe")
        retrieved = lineage.get_event(ev.event_id)
        assert retrieved is not None
        assert retrieved.event_id == ev.event_id
        assert retrieved.operation == "transform"

    def test_get_event_unknown_id_returns_none(self) -> None:
        lineage = PersistentLineage()
        assert lineage.get_event("nonexistent_id") is None

    def test_all_events_returns_copy(self) -> None:
        lineage = PersistentLineage()
        lineage.record(operation="ingest")
        lineage.record(operation="transform")
        events = lineage.all_events
        assert len(events) == 2
        # Mutating the list should not affect the store
        events.clear()
        assert len(lineage.all_events) == 2


# ---------------------------------------------------------------------------
# PersistentLineage — parent-child chains
# ---------------------------------------------------------------------------


class TestPersistentLineageChain:
    def test_parent_child_relationship(self) -> None:
        lineage = PersistentLineage()
        parent = lineage.record(
            operation="ingest", layer="bronze", source="csv", destination="bronze/jobs"
        )
        child = lineage.record(
            operation="transform",
            layer="silver",
            source="bronze/jobs",
            destination="silver/jobs",
            parent_id=parent.event_id,
        )
        assert child.parent_id == parent.event_id

    def test_get_children_returns_correct_events(self) -> None:
        lineage = PersistentLineage()
        root = lineage.record(operation="ingest", layer="bronze")
        c1 = lineage.record(operation="transform", layer="silver", parent_id=root.event_id)
        c2 = lineage.record(operation="transform", layer="silver", parent_id=root.event_id)
        lineage.record(operation="ingest", layer="bronze")  # unrelated

        children = lineage.get_children(root.event_id)
        assert len(children) == 2
        child_ids = {e.event_id for e in children}
        assert c1.event_id in child_ids
        assert c2.event_id in child_ids

    def test_get_chain_traverses_to_root(self) -> None:
        lineage = PersistentLineage()
        ev1 = lineage.record(operation="ingest", layer="bronze")
        ev2 = lineage.record(operation="transform", layer="silver", parent_id=ev1.event_id)
        ev3 = lineage.record(operation="enrich", layer="gold", parent_id=ev2.event_id)

        chain = lineage.get_chain(ev3.event_id)
        assert len(chain) == 3
        assert chain[0].event_id == ev1.event_id
        assert chain[1].event_id == ev2.event_id
        assert chain[2].event_id == ev3.event_id

    def test_get_chain_single_event_returns_one_item(self) -> None:
        lineage = PersistentLineage()
        ev = lineage.record(operation="ingest", layer="bronze")
        chain = lineage.get_chain(ev.event_id)
        assert len(chain) == 1
        assert chain[0].event_id == ev.event_id

    def test_get_chain_unknown_event_returns_empty(self) -> None:
        lineage = PersistentLineage()
        chain = lineage.get_chain("bad_id")
        assert chain == []


# ---------------------------------------------------------------------------
# PersistentLineage — filtering
# ---------------------------------------------------------------------------


class TestPersistentLineageFiltering:
    def test_get_by_layer_bronze(self) -> None:
        lineage = PersistentLineage()
        lineage.record(operation="ingest", layer="bronze")
        lineage.record(operation="ingest", layer="bronze")
        lineage.record(operation="transform", layer="silver")

        bronze_events = lineage.get_by_layer("bronze")
        assert len(bronze_events) == 2
        assert all(e.layer == "bronze" for e in bronze_events)

    def test_get_by_layer_returns_empty_for_unknown_layer(self) -> None:
        lineage = PersistentLineage()
        lineage.record(operation="ingest", layer="bronze")
        assert lineage.get_by_layer("platinum") == []

    def test_get_by_pipeline_filters_correctly(self) -> None:
        lineage = PersistentLineage()
        lineage.record(operation="ingest", layer="bronze", pipeline_name="ingest-users")
        lineage.record(operation="transform", layer="silver", pipeline_name="ingest-users")
        lineage.record(operation="ingest", layer="bronze", pipeline_name="ingest-events")

        users_events = lineage.get_by_pipeline("ingest-users")
        assert len(users_events) == 2
        assert all(e.pipeline_name == "ingest-users" for e in users_events)

    def test_get_by_pipeline_returns_empty_for_unknown(self) -> None:
        lineage = PersistentLineage()
        assert lineage.get_by_pipeline("nonexistent") == []


# ---------------------------------------------------------------------------
# PersistentLineage — summary statistics
# ---------------------------------------------------------------------------


class TestPersistentLineageSummary:
    def test_summary_total_events_count(self) -> None:
        lineage = PersistentLineage()
        for _ in range(5):
            lineage.record(operation="ingest", layer="bronze")
        summary = lineage.summary()
        assert summary["total_events"] == 5

    def test_summary_by_layer(self) -> None:
        lineage = PersistentLineage()
        lineage.record(operation="ingest", layer="bronze")
        lineage.record(operation="ingest", layer="bronze")
        lineage.record(operation="transform", layer="silver")
        lineage.record(operation="enrich", layer="gold")

        summary = lineage.summary()
        assert summary["by_layer"]["bronze"] == 2
        assert summary["by_layer"]["silver"] == 1
        assert summary["by_layer"]["gold"] == 1

    def test_summary_by_operation(self) -> None:
        lineage = PersistentLineage()
        lineage.record(operation="ingest", layer="bronze")
        lineage.record(operation="ingest", layer="bronze")
        lineage.record(operation="transform", layer="silver")

        summary = lineage.summary()
        assert summary["by_operation"]["ingest"] == 2
        assert summary["by_operation"]["transform"] == 1

    def test_summary_empty_lineage(self) -> None:
        lineage = PersistentLineage()
        summary = lineage.summary()
        assert summary["total_events"] == 0
        assert summary["by_layer"] == {}
        assert summary["by_operation"] == {}


# ---------------------------------------------------------------------------
# PersistentLineage — persistence (disk round-trip)
# ---------------------------------------------------------------------------


class TestPersistentLineagePersistence:
    def test_events_written_to_disk(self, tmp_path: Path) -> None:
        path = tmp_path / "lineage.json"
        lineage = PersistentLineage(persist_path=path)
        lineage.record(operation="ingest", layer="bronze", source="csv", input_count=50)
        assert path.exists()
        data = json.loads(path.read_text())
        assert len(data) == 1
        assert data[0]["operation"] == "ingest"

    def test_events_reloaded_from_disk(self, tmp_path: Path) -> None:
        path = tmp_path / "lineage.json"

        lineage1 = PersistentLineage(persist_path=path)
        ev = lineage1.record(operation="transform", layer="silver", source="bronze/jobs")

        lineage2 = PersistentLineage(persist_path=path)
        retrieved = lineage2.get_event(ev.event_id)
        assert retrieved is not None
        assert retrieved.operation == "transform"

    def test_multiple_events_persisted_and_reloaded(self, tmp_path: Path) -> None:
        path = tmp_path / "lineage.json"

        lineage1 = PersistentLineage(persist_path=path)
        for i in range(5):
            lineage1.record(
                operation="ingest",
                layer="bronze",
                source=f"source_{i}",
                input_count=i * 10,
            )

        lineage2 = PersistentLineage(persist_path=path)
        assert len(lineage2.all_events) == 5

    def test_corrupted_file_starts_fresh(self, tmp_path: Path) -> None:
        path = tmp_path / "lineage.json"
        path.write_text("not valid json {{{{")

        # Should not raise — just logs warning and starts fresh
        lineage = PersistentLineage(persist_path=path)
        assert len(lineage.all_events) == 0

    def test_in_memory_lineage_no_persistence(self) -> None:
        lineage = PersistentLineage(persist_path=None)
        lineage.record(operation="ingest", layer="bronze")
        # Just verify it works — no file should be written
        assert len(lineage.all_events) == 1

    def test_chain_persisted_and_reloaded(self, tmp_path: Path) -> None:
        path = tmp_path / "lineage.json"

        lineage1 = PersistentLineage(persist_path=path)
        root = lineage1.record(operation="ingest", layer="bronze")
        child = lineage1.record(operation="transform", layer="silver", parent_id=root.event_id)

        lineage2 = PersistentLineage(persist_path=path)
        chain = lineage2.get_chain(child.event_id)
        assert len(chain) == 2
        assert chain[0].event_id == root.event_id


# ---------------------------------------------------------------------------
# PipelineRunner + Lineage integration
# ---------------------------------------------------------------------------


class TestPipelineRunnerWithLineage:
    def test_pipeline_records_lineage_events(self, tmp_path: Path) -> None:
        """Running a pipeline should create lineage events for extract and load."""
        import csv

        from dataenginex.config.schema import (
            DataConfig,
            DexConfig,
            PipelineConfig,
            ProjectConfig,
            SourceConfig,
        )
        from dataenginex.data.pipeline.runner import PipelineRunner

        # Create a tiny CSV
        csv_path = tmp_path / "data.csv"
        with csv_path.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["id", "name", "value"])
            writer.writeheader()
            for i in range(5):
                writer.writerow({"id": str(i), "name": f"item-{i}", "value": i * 10})

        config = DexConfig(
            project=ProjectConfig(name="lineage-test"),
            data=DataConfig(
                sources={
                    "items": SourceConfig(
                        type="csv",
                        connection={"path": str(tmp_path), "default_file": "data.csv"},
                    )
                },
                pipelines={"load-items": PipelineConfig(source="items")},
            ),
        )

        lineage_path = tmp_path / "lineage.json"
        lineage = PersistentLineage(persist_path=lineage_path)
        runner = PipelineRunner(config, data_dir=tmp_path / "lakehouse", lineage=lineage)
        result = runner.run("load-items")

        assert result.success is True

        # Lineage events should have been written
        events = lineage.all_events
        assert len(events) >= 2  # at least extract + load

        operations = {e.operation for e in events}
        assert "ingest" in operations
        assert "load" in operations

    def test_pipeline_lineage_survives_runner_restart(self, tmp_path: Path) -> None:
        """Lineage written by the runner should be readable by a fresh PersistentLineage."""
        import csv

        from dataenginex.config.schema import (
            DataConfig,
            DexConfig,
            PipelineConfig,
            ProjectConfig,
            SourceConfig,
        )
        from dataenginex.data.pipeline.runner import PipelineRunner

        csv_path = tmp_path / "items.csv"
        with csv_path.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["id", "qty"])
            writer.writeheader()
            writer.writerow({"id": "1", "qty": 10})
            writer.writerow({"id": "2", "qty": 20})

        config = DexConfig(
            project=ProjectConfig(name="persist-lineage-test"),
            data=DataConfig(
                sources={
                    "items": SourceConfig(
                        type="csv",
                        connection={"path": str(tmp_path), "default_file": "items.csv"},
                    )
                },
                pipelines={"pipe": PipelineConfig(source="items")},
            ),
        )

        lineage_path = tmp_path / "lineage.json"
        lineage = PersistentLineage(persist_path=lineage_path)
        runner = PipelineRunner(config, data_dir=tmp_path / "lakehouse", lineage=lineage)
        runner.run("pipe")

        # Read lineage from disk via a fresh instance
        fresh_lineage = PersistentLineage(persist_path=lineage_path)
        events = fresh_lineage.get_by_pipeline("pipe")
        assert len(events) >= 1

    def test_pipeline_lineage_by_layer(self, tmp_path: Path) -> None:
        """Load step should create a lineage event for the silver layer."""
        import csv

        from dataenginex.config.schema import (
            DataConfig,
            DexConfig,
            PipelineConfig,
            ProjectConfig,
            SourceConfig,
        )
        from dataenginex.data.pipeline.runner import PipelineRunner

        csv_path = tmp_path / "x.csv"
        with csv_path.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["id"])
            writer.writeheader()
            writer.writerow({"id": "1"})

        config = DexConfig(
            project=ProjectConfig(name="layer-lineage-test"),
            data=DataConfig(
                sources={
                    "x": SourceConfig(
                        type="csv",
                        connection={"path": str(tmp_path), "default_file": "x.csv"},
                    )
                },
                pipelines={"p": PipelineConfig(source="x")},
            ),
        )

        lineage = PersistentLineage()
        runner = PipelineRunner(config, data_dir=tmp_path / "lakehouse", lineage=lineage)
        runner.run("p")

        silver_events = lineage.get_by_layer("silver")
        assert len(silver_events) >= 1
