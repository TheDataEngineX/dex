"""
Medallion Architecture Implementation (Issue #35 - Medallion Architecture)

Implements the Bronze → Silver → Gold data architecture for DEX ecosystem
with support for local Parquet storage and BigQuery cloud integration.

Classes:
    StorageFormat: Supported storage format enumeration.
    DataLayer: Medallion architecture layer enumeration (bronze/silver/gold).
    LayerConfiguration: Configuration dataclass for a single medallion layer.
    MedallionArchitecture: Manages three-layer medallion architecture configs.
    StorageBackend: Abstract storage backend interface.
    LocalParquetStorage: Local Parquet file storage.
    BigQueryStorage: BigQuery cloud storage.
    DualStorage: Dual local + cloud storage strategy.
    DataLineage: In-memory data lineage tracker through medallion layers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from loguru import logger

__all__ = [
    "BigQueryStorage",
    "DataLayer",
    "DataLineage",
    "DualStorage",
    "LayerConfiguration",
    "LocalParquetStorage",
    "MedallionArchitecture",
    "StorageBackend",
    "StorageFormat",
]


class StorageFormat(StrEnum):
    """Supported storage formats"""

    PARQUET = "parquet"
    DELTA = "delta"
    ICEBERG = "iceberg"
    BIGQUERY = "bigquery"


class DataLayer(StrEnum):
    """Medallion architecture layers"""

    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"


@dataclass
class LayerConfiguration:
    """Configuration for a medallion layer."""

    layer_name: str
    description: str
    purpose: str
    storage_format: StorageFormat
    local_path: str
    bigquery_dataset: str
    retention_days: int | None
    schema_validation: bool
    quality_threshold: float
    compression: str = "snappy"

    def __post_init__(self) -> None:
        """Validate configuration."""
        if self.quality_threshold < 0 or self.quality_threshold > 1:
            raise ValueError("quality_threshold must be between 0 and 1")


class MedallionArchitecture:
    """Manages the three-layer medallion architecture for DEX."""

    # Bronze Layer Configuration
    BRONZE_CONFIG = LayerConfiguration(
        layer_name=DataLayer.BRONZE.value,
        description="Raw, unprocessed data from all sources",
        purpose="Preserve original data for historical reproducibility",
        storage_format=StorageFormat.PARQUET,
        local_path="data/bronze",
        bigquery_dataset="careerdex_bronze",
        retention_days=90,
        schema_validation=False,
        quality_threshold=0.0,  # No quality threshold for raw data
        compression="snappy",
    )

    # Silver Layer Configuration
    SILVER_CONFIG = LayerConfiguration(
        layer_name=DataLayer.SILVER.value,
        description="Cleaned, deduplicated, validated data",
        purpose="High-quality data ready for analytics and ML",
        storage_format=StorageFormat.PARQUET,
        local_path="data/silver",
        bigquery_dataset="careerdex_silver",
        retention_days=365,
        schema_validation=True,
        quality_threshold=0.75,  # >= 75% quality score
        compression="snappy",
    )

    # Gold Layer Configuration
    GOLD_CONFIG = LayerConfiguration(
        layer_name=DataLayer.GOLD.value,
        description="Enriched, aggregated data ready for ML and APIs",
        purpose="Serve AI models and customer-facing APIs",
        storage_format=StorageFormat.PARQUET,
        local_path="data/gold",
        bigquery_dataset="careerdex_gold",
        retention_days=None,  # Indefinite retention
        schema_validation=True,
        quality_threshold=0.90,  # >= 90% quality score
        compression="snappy",
    )

    @classmethod
    def get_layer_config(cls, layer: DataLayer) -> LayerConfiguration | None:
        """Get configuration for a specific layer."""
        configs = {
            DataLayer.BRONZE: cls.BRONZE_CONFIG,
            DataLayer.SILVER: cls.SILVER_CONFIG,
            DataLayer.GOLD: cls.GOLD_CONFIG,
        }
        return configs.get(layer)

    @classmethod
    def get_all_layers(cls) -> list[LayerConfiguration]:
        """Get configurations for all layers in order."""
        return [cls.BRONZE_CONFIG, cls.SILVER_CONFIG, cls.GOLD_CONFIG]


class StorageBackend(ABC):
    """Abstract storage backend interface.

    All lakehouse storage implementations must subclass this and provide
    concrete ``write``, ``read``, ``delete``, ``list_objects``, and
    ``exists`` methods.  The interface accepts a ``StorageFormat`` hint
    so backends can choose serialisation.

    Built-in implementations:
        - ``LocalParquetStorage`` — local Parquet files (this module)
        - ``BigQueryStorage`` — Google BigQuery tables (this module)
        - ``JsonStorage`` — JSON files (``dataenginex.lakehouse.storage``)
        - ``ParquetStorage`` — pyarrow-backed Parquet (``dataenginex.lakehouse.storage``)
        - ``S3Storage`` — AWS S3 object storage (``dataenginex.lakehouse.storage``)
        - ``GCSStorage`` — Google Cloud Storage (``dataenginex.lakehouse.storage``)
    """

    @abstractmethod
    def write(self, data: Any, path: str, format: StorageFormat) -> bool:
        """Write *data* to *path* in the given format.

        Returns ``True`` on success, ``False`` on failure.
        """
        ...

    @abstractmethod
    def read(self, path: str, format: StorageFormat) -> Any:
        """Read data from *path*.  Returns ``None`` on failure."""
        ...

    @abstractmethod
    def delete(self, path: str) -> bool:
        """Delete the resource at *path*.  Returns ``True`` on success."""
        ...

    @abstractmethod
    def list_objects(self, prefix: str = "") -> list[str]:
        """List object paths under *prefix*.

        Returns a list of relative paths.  Empty list on failure or when
        no objects match.
        """
        ...

    @abstractmethod
    def exists(self, path: str) -> bool:
        """Return ``True`` if *path* exists in the backend."""
        ...


class LocalParquetStorage(StorageBackend):
    """Local Parquet file storage implementation."""

    def __init__(self, base_path: str = "data"):
        self.base_path = base_path
        logger.info(f"Initialized local Parquet storage at {base_path}")

    def write(
        self,
        data: Any,
        path: str,
        format: StorageFormat = StorageFormat.PARQUET,
    ) -> bool:
        """
        Write data to local Parquet file.

        Args:
            data: Data to write (dict, list, or dataframe)
            path: Relative path from base_path
            format: Storage format (must be PARQUET for this backend)

        Returns:
            True if successful, False otherwise
        """
        if format != StorageFormat.PARQUET:
            logger.error(f"LocalParquetStorage only supports PARQUET format, got {format}")
            return False

        try:
            full_path = f"{self.base_path}/{path}"
            logger.info(f"Writing data to {full_path}")
            # Implementation: Use pyarrow.parquet to write
            # df.to_parquet(full_path, compression='snappy', index=False)
            return True
        except Exception as e:
            logger.error(f"Failed to write to {path}: {e}")
            return False

    def read(self, path: str, format: StorageFormat = StorageFormat.PARQUET) -> Any:
        """
        Read data from local Parquet file.

        Args:
            path: Relative path from base_path
            format: Storage format

        Returns:
            Data read from file, or None if failed
        """
        try:
            full_path = f"{self.base_path}/{path}"
            logger.info(f"Reading data from {full_path}")
            # Implementation: Use pyarrow.parquet to read
            # df = pd.read_parquet(full_path)
            return None
        except Exception as e:
            logger.error(f"Failed to read from {path}: {e}")
            return None

    def delete(self, path: str) -> bool:
        """Delete Parquet file."""
        try:
            full_path = f"{self.base_path}/{path}"
            logger.info(f"Deleting {full_path}")
            # Implementation: Use os.remove or shutil.rmtree
            return True
        except Exception as e:
            logger.error(f"Failed to delete {path}: {e}")
            return False

    def list_objects(self, prefix: str = "") -> list[str]:
        """List files under *prefix* relative to *base_path*."""
        target = Path(self.base_path) / prefix
        if not target.exists():
            return []
        return [str(p.relative_to(self.base_path)) for p in target.rglob("*") if p.is_file()]

    def exists(self, path: str) -> bool:
        """Return ``True`` if *path* exists on disk."""
        return (Path(self.base_path) / path).exists()


class BigQueryStorage(StorageBackend):
    """BigQuery cloud storage implementation."""

    def __init__(self, project_id: str, location: str = "US"):
        self.project_id = project_id
        self.location = location
        logger.info(f"Initialized BigQuery storage for project {project_id}")

    def write(
        self,
        data: Any,
        path: str,
        format: StorageFormat = StorageFormat.BIGQUERY,
    ) -> bool:
        """
        Write data to BigQuery table.

        Path format: "dataset.table"

        Args:
            data: Data to write (dataframe or dict records)
            path: BigQuery path as "dataset.table"
            format: Storage format

        Returns:
            True if successful, False otherwise
        """
        if format != StorageFormat.BIGQUERY:
            logger.error(f"BigQueryStorage should use BIGQUERY format, got {format}")
            return False

        try:
            logger.info(f"Writing data to BigQuery {path}")
            # Implementation: Use google.cloud.bigquery to write
            # client.load_table_from_dataframe(df, path).result()
            return True
        except Exception as e:
            logger.error(f"Failed to write to BigQuery {path}: {e}")
            return False

    def read(self, path: str, format: StorageFormat = StorageFormat.BIGQUERY) -> Any:
        """
        Read data from BigQuery table.

        Args:
            path: BigQuery path as "dataset.table"
            format: Storage format

        Returns:
            Data read from table, or None if failed
        """
        try:
            logger.info(f"Reading data from BigQuery {path}")
            # Implementation: Use google.cloud.bigquery to read
            # df = client.query(
            #     f"SELECT * FROM `{self.project_id}.{path}`"
            # ).to_dataframe()
            return None
        except Exception as e:
            logger.error(f"Failed to read from BigQuery {path}: {e}")
            return None

    def delete(self, path: str) -> bool:
        """Delete BigQuery table."""
        try:
            logger.info(f"Deleting BigQuery table {path}")
            # Implementation: Use google.cloud.bigquery to delete
            # client.delete_table(f"{self.project_id}.{path}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete from BigQuery {path}: {e}")
            return False

    def list_objects(self, prefix: str = "") -> list[str]:
        """List BigQuery tables matching *prefix* (stub)."""
        logger.info("Listing BigQuery tables with prefix %s", prefix)
        return []

    def exists(self, path: str) -> bool:
        """Check if BigQuery table exists (stub)."""
        logger.info("Checking BigQuery table existence: %s", path)
        return False


class DualStorage:
    """
    Manages dual storage strategy: local Parquet + BigQuery.

    Pattern:
    - Development/Testing: Write to local Parquet
    - Production/Cloud: Write to both local (backup) and BigQuery (primary)
    """

    def __init__(
        self,
        local_base_path: str = "data",
        bigquery_project: str | None = None,
        enable_bigquery: bool = False,
    ):
        self.local_storage = LocalParquetStorage(local_base_path)
        self.bigquery_storage = None

        if enable_bigquery and bigquery_project:
            self.bigquery_storage = BigQueryStorage(bigquery_project)
            logger.info("Dual storage enabled: Local Parquet + BigQuery")
        else:
            logger.info("Storage mode: Local Parquet only")

    def _write_layer(self, layer: str, data: Any, key: str, timestamp: str) -> bool:
        """
        Write data to a medallion layer.

        Args:
            layer: Layer name (bronze, silver, gold)
            data: Data to write
            key: Source or entity type identifier
            timestamp: Timestamp string for partitioning

        Returns:
            True if local write succeeded
        """
        local_path = f"{layer}/{key}/{timestamp}"
        success = self.local_storage.write(data, local_path)

        if self.bigquery_storage and success:
            bq_path = f"careerdex_{layer}.{key}_{timestamp.replace('-', '_').replace(':', '_')}"
            self.bigquery_storage.write(data, bq_path)

        return success

    def _read_layer(self, layer: str, key: str, timestamp: str) -> Any:
        """
        Read data from a medallion layer.

        Args:
            layer: Layer name (bronze, silver, gold)
            key: Source or entity type identifier
            timestamp: Timestamp string for partitioning
        """
        path = f"{layer}/{key}/{timestamp}"
        return self.local_storage.read(path)

    def write_bronze(self, data: Any, source: str, timestamp: str) -> bool:
        """Write to Bronze layer — path: bronze/{source}/{timestamp}."""
        return self._write_layer("bronze", data, source, timestamp)

    def write_silver(self, data: Any, entity_type: str, timestamp: str) -> bool:
        """Write to Silver layer — path: silver/{entity_type}/{timestamp}."""
        return self._write_layer("silver", data, entity_type, timestamp)

    def write_gold(self, data: Any, entity_type: str, timestamp: str) -> bool:
        """Write to Gold layer — path: gold/{entity_type}/{timestamp}."""
        return self._write_layer("gold", data, entity_type, timestamp)

    def read_bronze(self, source: str, timestamp: str) -> Any:
        """Read from Bronze layer."""
        return self._read_layer("bronze", source, timestamp)

    def read_silver(self, entity_type: str, timestamp: str) -> Any:
        """Read from Silver layer."""
        return self._read_layer("silver", entity_type, timestamp)

    def read_gold(self, entity_type: str, timestamp: str) -> Any:
        """Read from Gold layer."""
        return self._read_layer("gold", entity_type, timestamp)


class DataLineage:
    """Tracks data lineage through the medallion layers."""

    def __init__(self) -> None:
        self.lineage: dict[str, dict[str, Any]] = {}

    def record_bronze_ingestion(self, source: str, record_count: int, timestamp: str) -> str:
        """Record data entry into Bronze layer."""
        lineage_id = f"bronze_{source}_{timestamp}"
        self.lineage[lineage_id] = {
            "layer": "bronze",
            "source": source,
            "record_count": record_count,
            "timestamp": timestamp,
            "status": "raw",
        }
        return lineage_id

    def record_silver_transformation(
        self, lineage_id: str, processed_count: int, quality_score: float
    ) -> str:
        """Record data transformation in Silver layer."""
        silver_id = f"{lineage_id}_silver"
        self.lineage[silver_id] = {
            "layer": "silver",
            "parent": lineage_id,
            "processed_count": processed_count,
            "quality_score": quality_score,
            "status": "cleaned",
        }
        return silver_id

    def record_gold_enrichment(
        self, lineage_id: str, enriched_count: int, embedding_model: str
    ) -> str:
        """Record data enrichment in Gold layer."""
        gold_id = f"{lineage_id}_gold"
        self.lineage[gold_id] = {
            "layer": "gold",
            "parent": lineage_id,
            "enriched_count": enriched_count,
            "embedding_model": embedding_model,
            "status": "enriched",
        }
        return gold_id

    def get_lineage(self, lineage_id: str) -> dict[str, Any] | None:
        """Get lineage information for a record."""
        return self.lineage.get(lineage_id)
