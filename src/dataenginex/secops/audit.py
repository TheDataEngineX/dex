"""SecOps audit logging — structured log of PII detection and masking operations.

Every time PII is detected or masked, an ``AuditEvent`` is emitted via
loguru (structured key-value format) and appended to the in-memory
``AuditLogger`` for programmatic access.

This is NOT a replacement for a production audit trail (e.g. SIEM).
It is a lightweight in-process layer that makes PII handling observable
and testable without external infrastructure.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from loguru import logger

__all__ = [
    "AuditEvent",
    "AuditLogger",
    "AuditOperation",
]


class AuditOperation(StrEnum):
    """Type of SecOps operation being logged."""

    PII_SCAN = "pii_scan"
    PII_MASK = "pii_mask"
    PII_ACCESS = "pii_access"


@dataclass(frozen=True)
class AuditEvent:
    """A single audit log entry.

    Attributes:
        operation: Type of operation performed.
        dataset_name: Logical name of the dataset processed.
        pii_fields: Field names identified or masked.
        record_count: Number of records processed.
        actor: System component or user that triggered the operation.
        metadata: Extra context (strategy used, confidence scores, etc.).
        occurred_at: Timestamp of the event.
    """

    operation: AuditOperation
    dataset_name: str
    pii_fields: list[str]
    record_count: int
    actor: str = "system"
    metadata: dict[str, Any] = field(default_factory=dict)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))

    def to_dict(self) -> dict[str, Any]:
        """Serialise the event to a plain dictionary."""
        return {
            "operation": self.operation.value,
            "dataset_name": self.dataset_name,
            "pii_fields": self.pii_fields,
            "record_count": self.record_count,
            "actor": self.actor,
            "metadata": self.metadata,
            "occurred_at": self.occurred_at.isoformat(),
        }


class AuditLogger:
    """In-memory audit log for SecOps operations.

    Emits structured loguru events on every write and maintains an
    in-memory history for testing and local inspection.

    Parameters
    ----------
    max_history:
        Maximum number of events to retain in memory (FIFO eviction).
    """

    def __init__(self, max_history: int = 1000) -> None:
        self._events: list[AuditEvent] = []
        self._max = max_history

    def log(self, event: AuditEvent) -> None:
        """Record an audit event (in-memory + loguru)."""
        if len(self._events) >= self._max:
            self._events.pop(0)
        self._events.append(event)

        logger.info(
            "secops audit event",
            operation=event.operation.value,
            dataset=event.dataset_name,
            pii_fields=event.pii_fields,
            record_count=event.record_count,
            actor=event.actor,
            **{k: v for k, v in event.metadata.items() if isinstance(v, (str, int, float, bool))},
        )

    def log_scan(
        self,
        dataset_name: str,
        pii_fields: list[str],
        record_count: int,
        actor: str = "system",
        metadata: dict[str, Any] | None = None,
    ) -> AuditEvent:
        """Convenience method to log a PII scan operation."""
        event = AuditEvent(
            operation=AuditOperation.PII_SCAN,
            dataset_name=dataset_name,
            pii_fields=pii_fields,
            record_count=record_count,
            actor=actor,
            metadata=metadata or {},
        )
        self.log(event)
        return event

    def log_mask(
        self,
        dataset_name: str,
        pii_fields: list[str],
        record_count: int,
        strategy: str,
        actor: str = "system",
    ) -> AuditEvent:
        """Convenience method to log a PII masking operation."""
        event = AuditEvent(
            operation=AuditOperation.PII_MASK,
            dataset_name=dataset_name,
            pii_fields=pii_fields,
            record_count=record_count,
            actor=actor,
            metadata={"strategy": strategy},
        )
        self.log(event)
        return event

    @property
    def events(self) -> list[AuditEvent]:
        """Return all retained audit events (oldest first)."""
        return list(self._events)

    def events_for(self, dataset_name: str) -> list[AuditEvent]:
        """Return all events for a specific dataset."""
        return [e for e in self._events if e.dataset_name == dataset_name]

    def clear(self) -> None:
        """Clear the in-memory history."""
        self._events.clear()
