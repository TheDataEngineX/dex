"""Connector registry and public API."""
from __future__ import annotations

from dataenginex.core.interfaces import BaseConnector
from dataenginex.core.registry import BackendRegistry

# New registry-based connector system
connector_registry: BackendRegistry[BaseConnector] = BackendRegistry("connector")

# Re-export legacy connector classes for backward compatibility
from dataenginex.data.connectors.legacy import (  # noqa: E402
    ConnectorStatus,
    DataConnector,
    FetchResult,
    FileConnector,
    RestConnector,
)

__all__ = [
    # New
    "BaseConnector",
    "connector_registry",
    # Legacy
    "ConnectorStatus",
    "DataConnector",
    "FetchResult",
    "FileConnector",
    "RestConnector",
]
