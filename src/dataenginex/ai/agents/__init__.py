"""Agent runtime registry.

Built-in agent uses tool-calling loop with LLM providers.
LangGraph available via ``[agents]`` extra.
"""

from __future__ import annotations

from dataenginex.core.interfaces import BaseAgentRuntime
from dataenginex.core.registry import BackendRegistry

agent_registry: BackendRegistry[BaseAgentRuntime] = BackendRegistry("agent")
