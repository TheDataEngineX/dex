"""Conformance tests for BaseConnector implementations.

Every connector backend must pass these tests.
Subclass this and provide a `connector` fixture.
"""

from __future__ import annotations

from typing import Any


class ConnectorConformanceTests:
    """All BaseConnector implementations must pass these."""

    def test_connect_disconnect(self, connector: Any) -> None:
        connector.connect()
        connector.disconnect()

    def test_health_check_after_connect(self, connector: Any) -> None:
        connector.connect()
        assert connector.health_check() is True
        connector.disconnect()

    def test_write_then_read(self, connector: Any) -> None:
        connector.connect()
        connector.write(
            [{"id": 1, "name": "alice"}, {"id": 2, "name": "bob"}],
            table="test_table",
        )
        result = connector.read(table="test_table")
        assert len(result) == 2
        connector.disconnect()

    def test_read_empty_table(self, connector: Any) -> None:
        connector.connect()
        result = connector.read(table="nonexistent_empty", default=[])
        assert result == []
        connector.disconnect()
