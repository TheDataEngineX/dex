"""Experiment tracking registry.

Built-in tracker uses JSON storage. MLflow available via ``[mlflow]`` extra.
"""

from __future__ import annotations

from dataenginex.core.interfaces import BaseTracker
from dataenginex.core.registry import BackendRegistry

tracker_registry: BackendRegistry[BaseTracker] = BackendRegistry("tracker")
