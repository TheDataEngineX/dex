"""
Persistent lineage — JSON-file-backed data lineage tracking.

Records every data movement (ingestion, transformation, enrichment) through
the medallion layers, persisting the graph to disk so it survives restarts.
"""

from __future__ import annotations

import json
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger()
__all__ = [
    "LineageEvent",
    "PersistentLineage",
]


@dataclass
class LineageEvent:
    """A single lineage event describing a data operation.

    Attributes:
        event_id: Auto-generated unique identifier (12-char hex).
        parent_id: ID of the upstream event that produced the input.
        operation: Type of operation (``"ingest"``, ``"transform"``, ``"enrich"``, ``"export"``).
        layer: Medallion layer (``"bronze"``, ``"silver"``, ``"gold"``).
        source: Where data came from.
        destination: Where data was written.
        input_count: Number of input records.
        output_count: Number of output records.
        error_count: Number of records that errored.
        quality_score: Quality score of the output (0.0–1.0).
        pipeline_name: Name of the owning pipeline.
        step_name: Name of the transform step.
        metadata: Free-form context dict.
        timestamp: When the event occurred.
    """

    event_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    parent_id: str | None = None

    # What happened
    operation: str = ""  # "ingest", "transform", "enrich", "export"
    layer: str = ""  # "bronze", "silver", "gold"
    source: str = ""
    destination: str = ""

    # Counts
    input_count: int = 0
    output_count: int = 0
    error_count: int = 0
    quality_score: float | None = None

    # Context
    pipeline_name: str = ""
    step_name: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(tz=UTC))

    def to_dict(self) -> dict[str, Any]:
        """Serialize the lineage event to a plain dictionary."""
        d = asdict(self)
        d["timestamp"] = self.timestamp.isoformat()
        return d


class PersistentLineage:
    """JSON-file-backed lineage store.

    Example::

        lineage = PersistentLineage("data/lineage.json")
        ev = lineage.record(
            operation="ingest",
            layer="bronze",
            source="linkedin",
            input_count=1250,
            output_count=1250,
        )
        # later
        lineage.record(
            operation="transform",
            layer="silver",
            parent_id=ev.event_id,
            input_count=1250,
            output_count=1200,
            quality_score=0.88,
        )
    """

    def __init__(self, persist_path: str | Path | None = None) -> None:
        self._events: list[LineageEvent] = []
        self._persist_path = Path(persist_path) if persist_path else None
        self._lock = threading.Lock()
        if self._persist_path and self._persist_path.exists():
            self._load()

    # -- public API ----------------------------------------------------------

    def record(self, **kwargs: Any) -> LineageEvent:
        """Create and store a new lineage event.

        Accepts the same keyword arguments as ``LineageEvent``.
        """
        with self._lock:
            event = LineageEvent(**kwargs)
            self._events.append(event)
            logger.info(
                "Lineage event %s: %s %s → %s (%d→%d)",
                event.event_id,
                event.operation,
                event.source,
                event.destination,
                event.input_count,
                event.output_count,
            )
            self._save()
        return event

    def get_event(self, event_id: str) -> LineageEvent | None:
        """Fetch a single event by ID."""
        for ev in self._events:
            if ev.event_id == event_id:
                return ev
        return None

    def get_children(self, parent_id: str) -> list[LineageEvent]:
        """Return events that have *parent_id* as their parent."""
        return [ev for ev in self._events if ev.parent_id == parent_id]

    def get_chain(self, event_id: str) -> list[LineageEvent]:
        """Walk up from *event_id* to the root and return the full chain."""
        chain: list[LineageEvent] = []
        current = self.get_event(event_id)
        while current:
            chain.append(current)
            current = self.get_event(current.parent_id) if current.parent_id else None
        chain.reverse()
        return chain

    def get_by_layer(self, layer: str) -> list[LineageEvent]:
        """Return all events for a given medallion layer."""
        return [ev for ev in self._events if ev.layer == layer]

    def get_by_pipeline(self, pipeline_name: str) -> list[LineageEvent]:
        """Return all events for a given pipeline."""
        return [ev for ev in self._events if ev.pipeline_name == pipeline_name]

    @property
    def all_events(self) -> list[LineageEvent]:
        """Return a shallow copy of all stored lineage events."""
        return list(self._events)

    def summary(self) -> dict[str, Any]:
        """Return high-level lineage statistics."""
        layers: dict[str, int] = {}
        operations: dict[str, int] = {}
        for ev in self._events:
            layers[ev.layer] = layers.get(ev.layer, 0) + 1
            operations[ev.operation] = operations.get(ev.operation, 0) + 1
        return {
            "total_events": len(self._events),
            "by_layer": layers,
            "by_operation": operations,
        }

    # -- persistence ---------------------------------------------------------

    def _save(self) -> None:
        if not self._persist_path:
            return
        self._persist_path.parent.mkdir(parents=True, exist_ok=True)
        data = [ev.to_dict() for ev in self._events]
        self._persist_path.write_text(json.dumps(data, indent=2, default=str))

    def _load(self) -> None:
        if not self._persist_path or not self._persist_path.exists():
            return
        try:
            raw = json.loads(self._persist_path.read_text())
            for item in raw:
                item.pop("timestamp", None)
                self._events.append(LineageEvent(**item))
            logger.info(
                "lineage events loaded",
                count=len(self._events),
                path=str(self._persist_path),
            )
        except (json.JSONDecodeError, TypeError, KeyError) as exc:
            logger.warning(
                "lineage file corrupted, starting fresh",
                path=str(self._persist_path),
                error=str(exc),
            )
            self._events = []
