"""Model serving engine registry.

Built-in serving engine wraps the existing ModelServer.
BentoML available via ``[bentoml]`` extra.
"""

from __future__ import annotations

from dataenginex.core.interfaces import BaseServingEngine
from dataenginex.core.registry import BackendRegistry

serving_registry: BackendRegistry[BaseServingEngine] = BackendRegistry("serving")
