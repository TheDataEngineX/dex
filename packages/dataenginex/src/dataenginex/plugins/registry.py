"""Plugin registry — ABC, discovery, and lifecycle management."""

from __future__ import annotations

import abc
from importlib.metadata import entry_points
from typing import Any

from loguru import logger

__all__ = [
    "DataEngineXPlugin",
    "PluginRegistry",
    "discover",
]


class DataEngineXPlugin(abc.ABC):
    """Interface that every DataEngineX plugin must implement.

    Attributes:
        name: Short identifier (e.g. ``"careerdex"``).
        version: SemVer string (e.g. ``"0.5.0"``).
    """

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Unique plugin name."""

    @property
    @abc.abstractmethod
    def version(self) -> str:
        """Plugin version string."""

    @abc.abstractmethod
    def health_check(self) -> dict[str, Any]:
        """Return health status.

        Returns:
            Dict with at least ``{"status": "healthy"|"degraded"|"unhealthy"}``.
        """

    def get_metrics(self) -> dict[str, Any]:
        """Return plugin-specific metrics.

        Override this to expose custom Prometheus-compatible metrics.
        Default returns an empty dict.
        """
        return {}

    def register_routes(self, app: Any) -> None:
        """Mount plugin-specific routes onto the FastAPI ``app``.

        Override this if the plugin exposes HTTP endpoints.
        Default is a no-op.
        """
        return  # noqa: B027  — intentionally optional, not abstract


# ======================================================================
# Discovery
# ======================================================================

_ENTRY_POINT_GROUP = "dataenginex.plugins"


def discover() -> list[DataEngineXPlugin]:
    """Discover and instantiate all installed DataEngineX plugins.

    Scans ``entry_points(group="dataenginex.plugins")`` and calls each
    entry point to get a plugin class, then instantiates it.

    Returns:
        List of plugin instances.  Broken plugins are logged and skipped.
    """
    plugins: list[DataEngineXPlugin] = []
    eps = entry_points(group=_ENTRY_POINT_GROUP)

    for ep in eps:
        try:
            plugin_cls = ep.load()
            instance = plugin_cls()
            if not isinstance(instance, DataEngineXPlugin):
                logger.warning(
                    "entry point %s does not implement DataEngineXPlugin — skipped",
                    ep.name,
                )
                continue
            plugins.append(instance)
            logger.info("discovered plugin name=%s version=%s", instance.name, instance.version)
        except Exception as exc:
            logger.error("failed to load plugin %s: %s", ep.name, exc)

    return plugins


# ======================================================================
# Registry
# ======================================================================


class PluginRegistry:
    """Manages discovered plugins and provides lookup + health aggregation.

    Usage::

        registry = PluginRegistry()
        for p in discover():
            registry.register(p)

        registry.get("careerdex")          # single lookup
        registry.all()                     # all registered plugins
        registry.health_check_all()        # aggregated health
    """

    def __init__(self) -> None:
        self._plugins: dict[str, DataEngineXPlugin] = {}

    def register(self, plugin: DataEngineXPlugin) -> None:
        """Register a plugin instance.

        Raises:
            ValueError: If a plugin with the same name is already registered.
        """
        if plugin.name in self._plugins:
            msg = f"plugin already registered: {plugin.name}"
            raise ValueError(msg)
        self._plugins[plugin.name] = plugin
        logger.info("registered plugin name=%s version=%s", plugin.name, plugin.version)

    def get(self, name: str) -> DataEngineXPlugin | None:
        """Look up a plugin by name.  Returns ``None`` if not found."""
        return self._plugins.get(name)

    def all(self) -> list[DataEngineXPlugin]:
        """Return all registered plugins in registration order."""
        return list(self._plugins.values())

    def health_check_all(self) -> dict[str, dict[str, Any]]:
        """Run health checks across all registered plugins.

        Returns:
            ``{name: health_dict}`` for each plugin.
        """
        results: dict[str, dict[str, Any]] = {}
        for name, plugin in self._plugins.items():
            try:
                results[name] = plugin.health_check()
            except Exception as exc:
                logger.error("health check failed for plugin %s: %s", name, exc)
                results[name] = {"status": "unhealthy", "error": str(exc)}
        return results

    @property
    def count(self) -> int:
        """Number of registered plugins."""
        return len(self._plugins)
