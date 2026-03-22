"""DuckDB connector tests — conformance + DuckDB-specific tests."""

from __future__ import annotations

import pytest

from dataenginex.data.connectors.duckdb import DuckDBConnector
from tests.conformance.test_connector import ConnectorConformanceTests


class TestDuckDBConnector(ConnectorConformanceTests):
    @pytest.fixture()
    def connector(self, tmp_path):  # type: ignore[override]
        return DuckDBConnector(database=str(tmp_path / "test.duckdb"))

    def test_in_memory_mode(self) -> None:
        conn = DuckDBConnector(database=":memory:")
        conn.connect()
        assert conn.health_check() is True
        conn.disconnect()

    def test_execute_raw_sql(self, tmp_path) -> None:
        conn = DuckDBConnector(database=str(tmp_path / "test.duckdb"))
        conn.connect()
        conn.write([{"x": 1}, {"x": 2}], table="nums")
        result = conn.execute("SELECT sum(x) as total FROM nums")
        assert result[0]["total"] == 3
        conn.disconnect()

    def test_read_not_connected_raises(self) -> None:
        conn = DuckDBConnector()
        with pytest.raises(RuntimeError, match="Not connected"):
            conn.read(table="anything")

    def test_write_empty_list_noop(self, tmp_path) -> None:
        conn = DuckDBConnector(database=str(tmp_path / "test.duckdb"))
        conn.connect()
        conn.write([], table="empty")
        conn.disconnect()
