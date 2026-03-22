"""Transform registry and public API."""

from __future__ import annotations

from dataenginex.core.interfaces import BaseTransform
from dataenginex.core.registry import BackendRegistry

transform_registry: BackendRegistry[BaseTransform] = BackendRegistry("transform")

__all__ = ["BaseTransform", "transform_registry"]
