"""SecOps audit logging — structured log of PII detection and masking operations.

Every time PII is detected or masked, an ``AuditEvent`` is emitted via
structlog (structured key-value format) and persisted via the configured
backend (default: DuckDB in-memory; pass a file path for persistence).

This is NOT a replacement for a production audit trail (e.g. SIEM).
It is a lightweight in-process layer that makes PII handling observable
and testable without external infrastructure.

Note: ``AuditLogger`` is not thread-safe. The underlying DuckDB connection
has no locking — consistent with the previous in-memory behaviour.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

import duckdb
import structlog

logger = structlog.get_logger()

__all__ = [
    "AuditEvent",
    "AuditLogger",
    "AuditOperation",
]

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS audit_events (
    rowid        INTEGER PRIMARY KEY,
    operation    TEXT NOT NULL,
    dataset_name TEXT NOT NULL,
    pii_fields   TEXT NOT NULL,
    record_count INTEGER NOT NULL,
    actor        TEXT NOT NULL,
    metadata     TEXT NOT NULL,
    occurred_at  TEXT NOT NULL
)
"""

_INSERT = """
INSERT INTO audit_events
    (rowid, operation, dataset_name, pii_fields, record_count, actor, metadata, occurred_at)
VALUES (?, ?, ?, ?, ?, ?, ?, ?)
"""

_EVICT = """
DELETE FROM audit_events
WHERE rowid NOT IN (
    SELECT rowid FROM audit_events ORDER BY rowid DESC LIMIT ?
)
"""


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


class _DuckDBAuditBackend:
    """DuckDB-backed audit store (in-memory or file-based)."""

    def __init__(self, db_path: str, max_history: int) -> None:
        self._conn = duckdb.connect(db_path)
        self._max = max_history
        self._conn.execute(_CREATE_TABLE)
        # Sequence counter — survives across sessions via MAX(rowid).
        row = self._conn.execute("SELECT COALESCE(MAX(rowid), 0) FROM audit_events").fetchone()
        self._seq: int = int(row[0]) if row else 0

    def append(self, event: AuditEvent) -> None:
        self._seq += 1
        self._conn.execute(
            _INSERT,
            [
                self._seq,
                event.operation.value,
                event.dataset_name,
                json.dumps(event.pii_fields),
                event.record_count,
                event.actor,
                json.dumps(event.metadata),
                event.occurred_at.isoformat(),
            ],
        )
        self._conn.execute(_EVICT, [self._max])

    def all(self) -> list[AuditEvent]:
        rows = self._conn.execute(
            "SELECT operation, dataset_name, pii_fields, record_count, "
            "actor, metadata, occurred_at "
            "FROM audit_events ORDER BY rowid ASC"
        ).fetchall()
        return [self._row_to_event(r) for r in rows]

    def filter_by_dataset(self, dataset_name: str) -> list[AuditEvent]:
        rows = self._conn.execute(
            "SELECT operation, dataset_name, pii_fields, record_count, "
            "actor, metadata, occurred_at "
            "FROM audit_events WHERE dataset_name = ? ORDER BY rowid ASC",
            [dataset_name],
        ).fetchall()
        return [self._row_to_event(r) for r in rows]

    def clear(self) -> None:
        self._conn.execute("DELETE FROM audit_events")

    def close(self) -> None:
        self._conn.close()

    @staticmethod
    def _row_to_event(row: tuple[Any, ...]) -> AuditEvent:
        pii_fields: list[str] = [str(x) for x in json.loads(row[2])]
        meta: dict[str, Any] = json.loads(row[5])
        return AuditEvent(
            operation=AuditOperation(row[0]),
            dataset_name=row[1],
            pii_fields=pii_fields,
            record_count=int(row[3]),
            actor=row[4],
            metadata=meta,
            occurred_at=datetime.fromisoformat(row[6]),
        )


class AuditLogger:
    """Audit log for SecOps operations backed by DuckDB.

    Emits structured structlog events on every write and persists events
    in a DuckDB database (in-memory by default, file-backed when *db_path*
    is a filesystem path).

    Parameters
    ----------
    max_history:
        Maximum number of events to retain (FIFO eviction by insertion order).
    db_path:
        DuckDB database path. Defaults to ``":memory:"`` (no persistence).
        Pass a file path (e.g. ``"/var/lib/dex/audit.db"``) for persistence
        across restarts.
    """

    def __init__(self, max_history: int = 1000, db_path: str = ":memory:") -> None:
        self._backend = _DuckDBAuditBackend(db_path, max_history)

    def log(self, event: AuditEvent) -> None:
        """Record an audit event (backend + structlog)."""
        self._backend.append(event)
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
        return self._backend.all()

    def events_for(self, dataset_name: str) -> list[AuditEvent]:
        """Return all events for a specific dataset."""
        return self._backend.filter_by_dataset(dataset_name)

    def clear(self) -> None:
        """Clear all retained events."""
        self._backend.clear()

    def close(self) -> None:
        """Release the DuckDB connection. Important for file-backed databases."""
        self._backend.close()
