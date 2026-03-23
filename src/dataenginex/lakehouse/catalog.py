"""
Data catalog — registry of lakehouse datasets with metadata.

``DataCatalog`` keeps track of every dataset written to the lakehouse,
recording its layer, format, location, schema snapshot, and record counts
so that downstream consumers can discover available data.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger()
__all__ = [
    "CatalogEntry",
    "DataCatalog",
]


@dataclass
class CatalogEntry:
    """Metadata about a single dataset in the lakehouse.

    Attributes:
        name: Unique dataset name.
        layer: Medallion layer (``"bronze"``, ``"silver"``, ``"gold"``).
        format: Storage format (``"parquet"``, ``"json"``, ``"delta"``).
        location: File path or table reference.
        record_count: Approximate number of records.
        schema_fields: List of column/field names.
        description: Human-readable dataset description.
        owner: Team or user responsible for the dataset.
        tags: Arbitrary labels for discovery.
        created_at: When the dataset was first registered.
        updated_at: When the entry was last updated.
        metadata: Free-form context dict.
        version: Auto-incremented version counter.
    """

    name: str
    layer: str  # "bronze", "silver", "gold"
    format: str  # "parquet", "json", "delta"
    location: str  # file path or table ref
    record_count: int = 0
    schema_fields: list[str] = field(default_factory=list)
    description: str = ""
    owner: str = ""
    tags: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
    metadata: dict[str, Any] = field(default_factory=dict)
    version: int = 1

    def to_dict(self) -> dict[str, Any]:
        """Serialize the catalog entry to a plain dictionary."""
        d = asdict(self)
        d["created_at"] = self.created_at.isoformat()
        d["updated_at"] = self.updated_at.isoformat()
        return d


class DataCatalog:
    """In-process data catalog backed by an optional JSON file.

    Parameters
    ----------
    persist_path:
        When set, catalog entries are persisted to this JSON file.
    """

    def __init__(self, persist_path: str | Path | None = None) -> None:
        self._entries: dict[str, CatalogEntry] = {}
        self._persist_path = Path(persist_path) if persist_path else None
        if self._persist_path and self._persist_path.exists():
            self._load()

    # -- public API ----------------------------------------------------------

    def register(self, entry: CatalogEntry) -> CatalogEntry:
        """Register or update a dataset entry."""
        existing = self._entries.get(entry.name)
        if existing:
            entry.version = existing.version + 1
            entry.created_at = existing.created_at
        entry.updated_at = datetime.now(tz=UTC)
        self._entries[entry.name] = entry
        logger.info(
            "Catalog registered: %s (layer=%s, v%d)",
            entry.name,
            entry.layer,
            entry.version,
        )
        self._save()
        return entry

    def get(self, name: str) -> CatalogEntry | None:
        """Retrieve an entry by name."""
        return self._entries.get(name)

    def search(
        self,
        *,
        layer: str | None = None,
        tags: list[str] | None = None,
        owner: str | None = None,
        name_contains: str | None = None,
    ) -> list[CatalogEntry]:
        """Search entries by criteria."""
        results = list(self._entries.values())
        if layer:
            results = [e for e in results if e.layer == layer]
        if tags:
            tag_set = set(tags)
            results = [e for e in results if tag_set.issubset(set(e.tags))]
        if owner:
            results = [e for e in results if e.owner == owner]
        if name_contains:
            results = [e for e in results if name_contains.lower() in e.name.lower()]
        return results

    def list_all(self) -> list[CatalogEntry]:
        """Return all catalog entries."""
        return list(self._entries.values())

    def delete(self, name: str) -> bool:
        """Remove an entry by name."""
        if name in self._entries:
            del self._entries[name]
            self._save()
            return True
        return False

    def summary(self) -> dict[str, Any]:
        """High-level catalog statistics."""
        layers: dict[str, int] = {}
        formats: dict[str, int] = {}
        for e in self._entries.values():
            layers[e.layer] = layers.get(e.layer, 0) + 1
            formats[e.format] = formats.get(e.format, 0) + 1
        return {
            "total_datasets": len(self._entries),
            "by_layer": layers,
            "by_format": formats,
        }

    # -- persistence ---------------------------------------------------------

    def _save(self) -> None:
        if not self._persist_path:
            return
        self._persist_path.parent.mkdir(parents=True, exist_ok=True)
        data = [e.to_dict() for e in self._entries.values()]
        self._persist_path.write_text(json.dumps(data, indent=2, default=str))

    def _load(self) -> None:
        if not self._persist_path or not self._persist_path.exists():
            return
        raw = json.loads(self._persist_path.read_text())
        for item in raw:
            item.pop("created_at", None)
            item.pop("updated_at", None)
            entry = CatalogEntry(**item)
            self._entries[entry.name] = entry
        logger.info(
            "catalog entries loaded", count=len(self._entries), path=str(self._persist_path)
        )
