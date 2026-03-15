"""Tests for dataenginex.data — connectors, profiler, schema registry."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from dataenginex.data.connectors import (
    ConnectorStatus,
    FetchResult,
    FileConnector,
    RestConnector,
)
from dataenginex.data.profiler import DataProfiler
from dataenginex.data.registry import SchemaRegistry, SchemaVersion

# ============================================================================
# Connectors
# ============================================================================


class TestFetchResult:
    def test_success_property(self) -> None:
        r = FetchResult(records=[{"a": 1}], record_count=1, source="test")
        assert r.success is True

    def test_failure_property(self) -> None:
        r = FetchResult(records=[], record_count=0, source="test", errors=["boom"])
        assert r.success is False


class TestFileConnector:
    @pytest.fixture()
    def json_file(self, tmp_path: Path) -> Path:
        p = tmp_path / "data.json"
        p.write_text(json.dumps([{"id": 1, "name": "a"}, {"id": 2, "name": "b"}]))
        return p

    @pytest.fixture()
    def jsonl_file(self, tmp_path: Path) -> Path:
        p = tmp_path / "data.jsonl"
        p.write_text('{"id":1}\n{"id":2}\n')
        return p

    @pytest.fixture()
    def csv_file(self, tmp_path: Path) -> Path:
        p = tmp_path / "data.csv"
        p.write_text("id,name\n1,alice\n2,bob\n")
        return p

    async def test_json_fetch(self, json_file: Path) -> None:
        async with FileConnector("test", json_file, "json") as conn:
            result = await conn.fetch()
            assert result.success
            assert result.record_count == 2
            assert result.records[0]["id"] == 1

    async def test_jsonl_fetch(self, jsonl_file: Path) -> None:
        async with FileConnector("test", jsonl_file, "jsonl") as conn:
            result = await conn.fetch()
            assert result.record_count == 2

    async def test_csv_fetch(self, csv_file: Path) -> None:
        async with FileConnector("test", csv_file, "csv") as conn:
            result = await conn.fetch()
            assert result.record_count == 2
            assert result.records[0]["name"] == "alice"

    async def test_limit_offset(self, json_file: Path) -> None:
        async with FileConnector("test", json_file, "json") as conn:
            result = await conn.fetch(limit=1, offset=1)
            assert result.record_count == 1
            assert result.records[0]["id"] == 2

    async def test_filters(self, json_file: Path) -> None:
        async with FileConnector("test", json_file, "json") as conn:
            result = await conn.fetch(filters={"name": "a"})
            assert result.record_count == 1

    async def test_missing_file(self, tmp_path: Path) -> None:
        conn = FileConnector("test", tmp_path / "nope.json", "json")
        ok = await conn.connect()
        assert ok is False
        assert conn.status == ConnectorStatus.ERROR

    def test_unsupported_format(self) -> None:
        with pytest.raises(ValueError, match="Unsupported"):
            FileConnector("test", "x.xml", "xml")

    async def test_close_clears(self, json_file: Path) -> None:
        conn = FileConnector("test", json_file, "json")
        await conn.connect()
        await conn.fetch()
        await conn.close()
        assert conn.status == ConnectorStatus.CLOSED


class TestRestConnector:
    async def test_connect_creates_client(self) -> None:
        conn = RestConnector("test", "https://example.com")
        ok = await conn.connect()
        assert ok
        assert conn.status == ConnectorStatus.CONNECTED
        await conn.close()
        assert conn.status == ConnectorStatus.CLOSED

    async def test_fetch_not_connected(self) -> None:
        conn = RestConnector("test", "https://example.com")
        result = await conn.fetch()
        assert not result.success
        assert "not connected" in result.errors[0]


# ============================================================================
# Profiler
# ============================================================================


class TestDataProfiler:
    def test_empty_records(self) -> None:
        report = DataProfiler().profile([], "empty")
        assert report.record_count == 0
        assert report.column_count == 0

    def test_numeric_column(self) -> None:
        records = [{"val": i} for i in range(10)]
        report = DataProfiler().profile(records, "nums")
        assert report.record_count == 10
        col = report.columns[0]
        assert col.dtype == "numeric"
        assert col.min_value == 0
        assert col.max_value == 9
        assert col.null_count == 0

    def test_string_column(self) -> None:
        records = [{"name": "alice"}, {"name": "bob"}, {"name": None}]
        report = DataProfiler().profile(records, "names")
        col = report.columns[0]
        assert col.dtype == "string"
        assert col.null_count == 1
        assert col.min_length is not None

    def test_mixed_column(self) -> None:
        records: list[dict[str, Any]] = [{"x": 1}, {"x": "two"}, {"x": True}]
        report = DataProfiler().profile(records, "mix")
        col = report.columns[0]
        assert col.dtype == "mixed"

    def test_completeness(self) -> None:
        records = [{"a": 1, "b": None}, {"a": 2, "b": None}]
        report = DataProfiler().profile(records, "nulls")
        assert report.completeness < 1.0

    def test_to_dict(self) -> None:
        records = [{"x": 1}]
        report = DataProfiler().profile(records, "d")
        d = report.to_dict()
        assert "columns" in d
        assert d["dataset_name"] == "d"


# ============================================================================
# Schema registry
# ============================================================================


class TestSchemaRegistry:
    def test_register_and_get_latest(self) -> None:
        reg = SchemaRegistry()
        v1 = SchemaVersion(name="jobs", version="1.0.0", fields={"id": "str"})
        reg.register(v1)
        latest = reg.get_latest("jobs")
        assert latest is not None
        assert latest.version == "1.0.0"

    def test_duplicate_version_rejected(self) -> None:
        reg = SchemaRegistry()
        v1 = SchemaVersion(name="jobs", version="1.0.0", fields={"id": "str"})
        reg.register(v1)
        with pytest.raises(ValueError, match="already registered"):
            reg.register(v1)

    def test_get_version(self) -> None:
        reg = SchemaRegistry()
        reg.register(SchemaVersion(name="jobs", version="1.0.0", fields={"id": "str"}))
        reg.register(
            SchemaVersion(
                name="jobs",
                version="2.0.0",
                fields={"id": "str", "title": "str"},
            )
        )
        v = reg.get_version("jobs", "1.0.0")
        assert v is not None
        assert v.version == "1.0.0"

    def test_list_schemas_and_versions(self) -> None:
        reg = SchemaRegistry()
        reg.register(SchemaVersion(name="A", version="1.0.0", fields={}))
        reg.register(SchemaVersion(name="A", version="2.0.0", fields={}))
        reg.register(SchemaVersion(name="B", version="1.0.0", fields={}))
        assert sorted(reg.list_schemas()) == ["A", "B"]
        assert reg.list_versions("A") == ["1.0.0", "2.0.0"]

    def test_validate_record(self) -> None:
        reg = SchemaRegistry()
        reg.register(
            SchemaVersion(
                name="jobs",
                version="1.0.0",
                fields={"id": "str", "title": "str"},
                required_fields=["id", "title"],
            )
        )
        ok, errors = reg.validate("jobs", {"id": "1", "title": "Dev"})
        assert ok
        ok2, errors2 = reg.validate("jobs", {"id": "1"})
        assert not ok2
        assert len(errors2) == 1

    def test_persistence(self, tmp_path: Path) -> None:
        path = tmp_path / "schemas.json"
        reg = SchemaRegistry(persist_path=path)
        reg.register(SchemaVersion(name="X", version="1.0.0", fields={"a": "int"}))
        # Reload
        reg2 = SchemaRegistry(persist_path=path)
        assert reg2.get_latest("X") is not None
