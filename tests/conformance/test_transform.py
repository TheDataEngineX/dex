"""Conformance tests for BaseTransform implementations."""
from __future__ import annotations

from typing import Any

import duckdb


class TransformConformanceTests:
    """All BaseTransform implementations must pass these."""

    def test_transform_returns_table_name(
        self, transform: Any, duckdb_conn: duckdb.DuckDBPyConnection,
    ) -> None:
        """Transform must return the name of the output table."""
        duckdb_conn.execute("CREATE TABLE input AS SELECT 1 as id, 'alice' as name")
        result = transform.apply(duckdb_conn, "input")
        assert isinstance(result, str)
        count = duckdb_conn.execute(f"SELECT count(*) FROM {result}").fetchone()[0]
        assert count >= 0
