"""Tests for the DataEngineX plugin system (discovery + registry)."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from dataenginex.plugins import DataEngineXPlugin, PluginRegistry, discover

# ======================================================================
# Concrete test plugin
# ======================================================================


class _MockPlugin(DataEngineXPlugin):
    """Minimal plugin for testing."""

    @property
    def name(self) -> str:
        return "mock-plugin"

    @property
    def version(self) -> str:
        return "0.1.0"

    def health_check(self) -> dict[str, Any]:
        return {"status": "healthy"}

    def get_metrics(self) -> dict[str, Any]:
        return {"requests": 42}


class _UnhealthyPlugin(DataEngineXPlugin):
    @property
    def name(self) -> str:
        return "unhealthy-plugin"

    @property
    def version(self) -> str:
        return "0.0.1"

    def health_check(self) -> dict[str, Any]:
        msg = "database down"
        raise ConnectionError(msg)


# ======================================================================
# Registry tests
# ======================================================================


class TestPluginRegistry:
    """Test PluginRegistry registration, lookup, and health aggregation."""

    def test_register_and_get(self) -> None:
        registry = PluginRegistry()
        plugin = _MockPlugin()
        registry.register(plugin)
        assert registry.get("mock-plugin") is plugin
        assert registry.count == 1

    def test_register_duplicate_raises(self) -> None:
        registry = PluginRegistry()
        registry.register(_MockPlugin())
        with pytest.raises(ValueError, match="already registered"):
            registry.register(_MockPlugin())

    def test_get_missing_returns_none(self) -> None:
        registry = PluginRegistry()
        assert registry.get("nonexistent") is None

    def test_all_returns_registered_plugins(self) -> None:
        registry = PluginRegistry()
        p1 = _MockPlugin()
        registry.register(p1)
        plugins = registry.all()
        assert len(plugins) == 1
        assert plugins[0] is p1

    def test_health_check_all_healthy(self) -> None:
        registry = PluginRegistry()
        registry.register(_MockPlugin())
        results = registry.health_check_all()
        assert results["mock-plugin"]["status"] == "healthy"

    def test_health_check_all_catches_errors(self) -> None:
        registry = PluginRegistry()
        registry.register(_UnhealthyPlugin())
        results = registry.health_check_all()
        assert results["unhealthy-plugin"]["status"] == "unhealthy"
        assert "database down" in results["unhealthy-plugin"]["error"]

    def test_empty_registry(self) -> None:
        registry = PluginRegistry()
        assert registry.count == 0
        assert registry.all() == []
        assert registry.health_check_all() == {}

    def test_get_metrics(self) -> None:
        plugin = _MockPlugin()
        assert plugin.get_metrics() == {"requests": 42}

    def test_default_get_metrics(self) -> None:
        """Ensure the ABC default get_metrics returns empty dict."""

        class _Minimal(DataEngineXPlugin):
            @property
            def name(self) -> str:
                return "minimal"

            @property
            def version(self) -> str:
                return "0.0.0"

            def health_check(self) -> dict[str, Any]:
                return {"status": "healthy"}

        plugin = _Minimal()
        assert plugin.get_metrics() == {}

    def test_default_register_routes_is_noop(self) -> None:
        plugin = _MockPlugin()
        app = MagicMock()
        plugin.register_routes(app)  # should not raise


# ======================================================================
# Discovery tests
# ======================================================================


class TestPluginDiscovery:
    """Test entry_points-based plugin discovery."""

    def test_discover_returns_plugins(self) -> None:
        mock_ep = MagicMock()
        mock_ep.name = "mock"
        mock_ep.load.return_value = _MockPlugin

        with patch(
            "dataenginex.plugins.registry.entry_points",
            return_value=[mock_ep],
        ):
            plugins = discover()

        assert len(plugins) == 1
        assert plugins[0].name == "mock-plugin"
        assert plugins[0].version == "0.1.0"

    def test_discover_skips_non_plugin(self) -> None:
        mock_ep = MagicMock()
        mock_ep.name = "bad"
        mock_ep.load.return_value = dict  # not a DataEngineXPlugin

        with patch(
            "dataenginex.plugins.registry.entry_points",
            return_value=[mock_ep],
        ):
            plugins = discover()

        assert len(plugins) == 0

    def test_discover_skips_broken_entry_point(self) -> None:
        mock_ep = MagicMock()
        mock_ep.name = "broken"
        mock_ep.load.side_effect = ImportError("module not found")

        with patch(
            "dataenginex.plugins.registry.entry_points",
            return_value=[mock_ep],
        ):
            plugins = discover()

        assert len(plugins) == 0

    def test_discover_no_plugins_installed(self) -> None:
        with patch(
            "dataenginex.plugins.registry.entry_points",
            return_value=[],
        ):
            plugins = discover()

        assert plugins == []

    def test_discover_multiple_plugins(self) -> None:
        class _OtherPlugin(DataEngineXPlugin):
            @property
            def name(self) -> str:
                return "other"

            @property
            def version(self) -> str:
                return "1.0.0"

            def health_check(self) -> dict[str, Any]:
                return {"status": "healthy"}

        ep1 = MagicMock()
        ep1.name = "mock"
        ep1.load.return_value = _MockPlugin

        ep2 = MagicMock()
        ep2.name = "other"
        ep2.load.return_value = _OtherPlugin

        with patch(
            "dataenginex.plugins.registry.entry_points",
            return_value=[ep1, ep2],
        ):
            plugins = discover()

        assert len(plugins) == 2
        names = {p.name for p in plugins}
        assert names == {"mock-plugin", "other"}
