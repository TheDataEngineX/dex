"""Tests for DuckDB SQL transforms."""

from __future__ import annotations

from collections.abc import Generator

import duckdb
import pytest

from dataenginex.data.transforms.sql import (
    CastTransform,
    DeduplicateTransform,
    DeriveTransform,
    FilterTransform,
    SQLTransform,
)
from tests.conformance.test_transform import TransformConformanceTests


@pytest.fixture()
def duckdb_conn() -> Generator[duckdb.DuckDBPyConnection]:
    conn = duckdb.connect(":memory:")
    yield conn
    conn.close()


class TestFilterTransform(TransformConformanceTests):
    @pytest.fixture()
    def transform(self) -> FilterTransform:
        return FilterTransform(condition="id > 0")

    def test_filter_removes_rows(self, duckdb_conn: duckdb.DuckDBPyConnection) -> None:
        duckdb_conn.execute(
            "CREATE TABLE src AS SELECT * FROM (VALUES (1, 'a'), (2, 'b'), (3, 'c')) AS t(id, name)"
        )
        t = FilterTransform(condition="id > 1")
        out = t.apply(duckdb_conn, "src")
        count = duckdb_conn.execute(f"SELECT count(*) FROM {out}").fetchone()[0]
        assert count == 2

    def test_validate_empty_condition(self) -> None:
        t = FilterTransform(condition="")
        assert len(t.validate()) > 0


class TestDeriveTransform(TransformConformanceTests):
    @pytest.fixture()
    def transform(self) -> DeriveTransform:
        return DeriveTransform(name="doubled", expression="id * 2")

    def test_derive_adds_column(self, duckdb_conn: duckdb.DuckDBPyConnection) -> None:
        duckdb_conn.execute("CREATE TABLE src AS SELECT 5 AS id")
        t = DeriveTransform(name="doubled", expression="id * 2")
        out = t.apply(duckdb_conn, "src")
        row = duckdb_conn.execute(f"SELECT doubled FROM {out}").fetchone()
        assert row[0] == 10


class TestCastTransform(TransformConformanceTests):
    @pytest.fixture()
    def transform(self) -> CastTransform:
        return CastTransform(columns={"id": "VARCHAR"})

    def test_cast_changes_type(self, duckdb_conn: duckdb.DuckDBPyConnection) -> None:
        duckdb_conn.execute("CREATE TABLE src AS SELECT 42 AS id")
        t = CastTransform(columns={"id": "VARCHAR"})
        out = t.apply(duckdb_conn, "src")
        dtype = duckdb_conn.execute(f"SELECT typeof(id) FROM {out}").fetchone()[0]
        assert dtype == "VARCHAR"


class TestDeduplicateTransform(TransformConformanceTests):
    @pytest.fixture()
    def transform(self) -> DeduplicateTransform:
        return DeduplicateTransform(key="id")

    def test_dedup_removes_duplicates(self, duckdb_conn: duckdb.DuckDBPyConnection) -> None:
        duckdb_conn.execute(
            "CREATE TABLE src AS SELECT * FROM (VALUES (1, 'a'), (1, 'b'), (2, 'c')) AS t(id, name)"
        )
        t = DeduplicateTransform(key="id")
        out = t.apply(duckdb_conn, "src")
        count = duckdb_conn.execute(f"SELECT count(*) FROM {out}").fetchone()[0]
        assert count == 2

    def test_dedup_with_multiple_keys(self, duckdb_conn: duckdb.DuckDBPyConnection) -> None:
        duckdb_conn.execute(
            "CREATE TABLE src AS SELECT * FROM (VALUES (1, 'a'), (1, 'a'), (1, 'b')) AS t(id, name)"
        )
        t = DeduplicateTransform(key=["id", "name"])
        out = t.apply(duckdb_conn, "src")
        count = duckdb_conn.execute(f"SELECT count(*) FROM {out}").fetchone()[0]
        assert count == 2


class TestSQLTransform(TransformConformanceTests):
    @pytest.fixture()
    def transform(self) -> SQLTransform:
        return SQLTransform(sql="SELECT * FROM _data")

    def test_sql_filters_with_where(self, duckdb_conn: duckdb.DuckDBPyConnection) -> None:
        duckdb_conn.execute(
            "CREATE TABLE src AS SELECT * FROM (VALUES (1, 'a'), (2, 'b'), (3, 'c')) AS t(id, name)"
        )
        t = SQLTransform(sql="SELECT * FROM _data WHERE id > 1")
        out = t.apply(duckdb_conn, "src")
        count = duckdb_conn.execute(f"SELECT count(*) FROM {out}").fetchone()[0]
        assert count == 2

    def test_sql_adds_column(self, duckdb_conn: duckdb.DuckDBPyConnection) -> None:
        duckdb_conn.execute("CREATE TABLE src AS SELECT 5 AS id")
        t = SQLTransform(sql="SELECT id, id * 2 AS doubled FROM _data")
        out = t.apply(duckdb_conn, "src")
        row = duckdb_conn.execute(f"SELECT doubled FROM {out}").fetchone()
        assert row[0] == 10

    def test_validate_empty_sql(self) -> None:
        t = SQLTransform(sql="   ")
        assert len(t.validate()) > 0

    def test_validate_valid_sql(self) -> None:
        t = SQLTransform(sql="SELECT * FROM _data")
        assert t.validate() == []
