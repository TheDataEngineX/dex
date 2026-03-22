"""Tests for data quality gates."""

from __future__ import annotations

import duckdb
import pytest

from dataenginex.data.quality.gates import check_quality


@pytest.fixture()
def duckdb_conn():
    conn = duckdb.connect(":memory:")
    yield conn
    conn.close()


class TestQualityGates:
    def test_completeness_pass(self, duckdb_conn) -> None:
        duckdb_conn.execute("CREATE TABLE t AS SELECT 1 AS id, 'a' AS name UNION ALL SELECT 2, 'b'")
        result = check_quality(duckdb_conn, "t", completeness=0.9)
        assert result.passed is True

    def test_completeness_fail_with_nulls(self, duckdb_conn) -> None:
        duckdb_conn.execute(
            "CREATE TABLE t AS SELECT 1 AS id, 'a' AS name UNION ALL SELECT NULL, NULL"
        )
        result = check_quality(duckdb_conn, "t", completeness=0.9)
        assert result.passed is False
        assert result.completeness_score < 0.9

    def test_uniqueness_pass(self, duckdb_conn) -> None:
        duckdb_conn.execute("CREATE TABLE t AS SELECT 1 AS id UNION ALL SELECT 2")
        result = check_quality(duckdb_conn, "t", uniqueness=["id"])
        assert result.passed is True

    def test_uniqueness_fail_with_dupes(self, duckdb_conn) -> None:
        duckdb_conn.execute("CREATE TABLE t AS SELECT 1 AS id UNION ALL SELECT 1")
        result = check_quality(duckdb_conn, "t", uniqueness=["id"])
        assert result.passed is False

    def test_custom_sql_check(self, duckdb_conn) -> None:
        duckdb_conn.execute("CREATE TABLE t AS SELECT 10 AS value")
        sql = "SELECT count(*) FROM t WHERE value > 0"
        result = check_quality(duckdb_conn, "t", custom_sql=sql)
        assert result.passed is True

    def test_empty_table_passes_vacuously(self, duckdb_conn) -> None:
        duckdb_conn.execute("CREATE TABLE t (id INTEGER, name VARCHAR)")
        result = check_quality(duckdb_conn, "t", completeness=0.5)
        assert result.passed is True
