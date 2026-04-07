"""Audit logging — track every agent action for compliance and debugging."""

from __future__ import annotations

from pydantic import BaseModel


class AuditEntry(BaseModel):
    """A single audit log entry."""

    agent_name: str
    action: str
    input: str
    output: str
    timestamp: float
    reasoning: str = ""


class AuditLog:
    """In-memory audit log for agent actions."""

    def __init__(self) -> None:
        self._entries: list[AuditEntry] = []

    def log(self, entry: AuditEntry) -> None:
        """Record an audit entry."""
        self._entries.append(entry)

    def get_entries(self, agent_name: str | None = None, limit: int = 100) -> list[AuditEntry]:
        """Get audit entries, optionally filtered by agent name."""
        if agent_name is None:
            return self._entries[-limit:]
        filtered = [e for e in self._entries if e.agent_name == agent_name]
        return filtered[-limit:]
