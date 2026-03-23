"""Built-in DuckDB-backed feature store.

Stores feature groups as DuckDB tables in a persistent database.
For production: use Feast via ``[feast]`` extra.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb
import structlog

from dataenginex.core.interfaces import BaseFeatureStore
from dataenginex.ml.features import feature_store_registry

logger = structlog.get_logger()


@feature_store_registry.decorator("builtin", is_default=True)
class BuiltinFeatureStore(BaseFeatureStore):
    """DuckDB-backed feature store.

    Args:
        database: Path to DuckDB file. Defaults to ``.dex/features.duckdb``.
    """

    def __init__(self, database: str = ".dex/features.duckdb", **kwargs: Any) -> None:
        db_path = Path(database)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = duckdb.connect(str(db_path))
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS _feature_groups (
                name VARCHAR PRIMARY KEY,
                entity_key VARCHAR,
                created_at TIMESTAMP DEFAULT current_timestamp
            )
        """)
        logger.debug("feature store ready", database=str(db_path))

    def save_features(
        self,
        feature_group: str,
        data: Any,
        entity_key: str,
    ) -> None:
        """Persist features for a feature group."""
        import pyarrow as pa

        if isinstance(data, list):
            if len(data) == 0:
                return
            tbl = pa.Table.from_pylist(data)
        elif isinstance(data, pa.Table):
            tbl = data
        else:
            msg = f"Unsupported data type: {type(data)}"
            raise TypeError(msg)

        # Register or update feature group metadata
        self._conn.execute(
            "INSERT OR REPLACE INTO _feature_groups (name, entity_key) VALUES (?, ?)",
            [feature_group, entity_key],
        )
        # Store features as a table (overwrite)
        self._conn.execute(
            f"CREATE OR REPLACE TABLE {feature_group} AS SELECT * FROM tbl"  # noqa: S608
        )
        logger.info(
            "features saved",
            feature_group=feature_group,
            entity_key=entity_key,
            rows=len(tbl),
        )

    def get_features(
        self,
        feature_group: str,
        entity_ids: list[str],
    ) -> Any:
        """Retrieve features by entity IDs."""
        # Get entity key column name
        row = self._conn.execute(
            "SELECT entity_key FROM _feature_groups WHERE name = ?",
            [feature_group],
        ).fetchone()
        if row is None:
            msg = f"Feature group '{feature_group}' not found"
            raise KeyError(msg)
        entity_key = row[0]

        # Build IN clause
        placeholders = ", ".join(["?"] * len(entity_ids))
        result = self._conn.execute(
            f"SELECT * FROM {feature_group} "  # noqa: S608
            f"WHERE CAST({entity_key} AS VARCHAR) IN ({placeholders})",
            entity_ids,
        )
        columns = [desc[0] for desc in result.description]
        return [dict(zip(columns, r, strict=True)) for r in result.fetchall()]

    def list_feature_groups(self) -> list[str]:
        """List all registered feature groups."""
        rows = self._conn.execute("SELECT name FROM _feature_groups ORDER BY name").fetchall()
        return [r[0] for r in rows]

    def close(self) -> None:
        """Close the DuckDB connection."""
        self._conn.close()
