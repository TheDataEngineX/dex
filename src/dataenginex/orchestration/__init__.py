"""Orchestration registry and public API."""
from __future__ import annotations

from dataenginex.core.interfaces import BaseOrchestrator
from dataenginex.core.registry import BackendRegistry

orchestrator_registry: BackendRegistry[BaseOrchestrator] = BackendRegistry("orchestrator")

__all__ = ["BaseOrchestrator", "orchestrator_registry"]
