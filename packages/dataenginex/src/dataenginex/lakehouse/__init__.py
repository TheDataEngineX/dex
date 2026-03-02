"""Storage backends, data catalog, and partitioning.

Public API::

    from dataenginex.lakehouse import (
        # Storage backends
        StorageBackend,
        ParquetStorage, JsonStorage, S3Storage, GCSStorage,
        get_storage,
        # Catalog
        CatalogEntry, DataCatalog,
        # Partitioning
        PartitionStrategy, DatePartitioner, HashPartitioner,
    )
"""

from __future__ import annotations

from dataenginex.core.medallion_architecture import StorageBackend

from .catalog import CatalogEntry, DataCatalog
from .partitioning import DatePartitioner, HashPartitioner, PartitionStrategy
from .storage import GCSStorage, JsonStorage, ParquetStorage, S3Storage, get_storage

__all__ = [
    # Storage backends (ABC + implementations)
    "StorageBackend",
    "GCSStorage",
    "JsonStorage",
    "ParquetStorage",
    "S3Storage",
    "get_storage",
    # Catalog
    "CatalogEntry",
    "DataCatalog",
    # Partitioning
    "DatePartitioner",
    "HashPartitioner",
    "PartitionStrategy",
]
