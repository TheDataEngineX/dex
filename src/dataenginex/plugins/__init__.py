"""DataEngineX plugin system — discovery, registration, and lifecycle.

Plugins register via ``entry_points(group="dataenginex.plugins")`` in their
``pyproject.toml``.  At runtime, call :func:`discover` to find and instantiate
all installed plugins.

Example ``pyproject.toml``::

    [project.entry-points."dataenginex.plugins"]
    myplugin = "mypackage.plugin:MyPlugin"

Usage::

    from dataenginex.plugins import discover, PluginRegistry

    registry = PluginRegistry()
    for plugin in discover():
        registry.register(plugin)
"""

from __future__ import annotations

from dataenginex.plugins.registry import DataEngineXPlugin, PluginRegistry, discover

__all__ = [
    "DataEngineXPlugin",
    "PluginRegistry",
    "discover",
]
