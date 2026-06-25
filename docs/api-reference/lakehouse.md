# dataenginex.lakehouse

Storage backends, data catalog, and partitioning strategies for lakehouse-style architectures.

## Quick import

```python
from dataenginex.lakehouse import (
    LocalParquetStorage,
    StorageFormat,
    DataCatalog,
    PartitionStrategy,
)
```

______________________________________________________________________

## Storage

`dataenginex.lakehouse.storage`

Pluggable storage backends for reading and writing datasets across local, S3, GCS, and Delta Lake targets. `LocalParquetStorage` ships by default; cloud backends require `dataenginex[cloud]`.

::: dataenginex.lakehouse.storage

**Key classes:** `LocalParquetStorage`, `StorageFormat`

```python
from dataenginex.lakehouse.storage import LocalParquetStorage, StorageFormat

storage = LocalParquetStorage(
    base_path="data/gold",
    format=StorageFormat.PARQUET,
    compression="snappy",
)
storage.write(df, partition_by=["year", "month"])
df_back = storage.read("events", filters=[("year", "=", 2024)])
```

______________________________________________________________________

## Catalog

`dataenginex.lakehouse.catalog`

Dataset catalog — registers, discovers, and resolves named datasets to their storage locations. Persisted to DuckDB.

::: dataenginex.lakehouse.catalog

**Key class:** `DataCatalog`

```python
from dataenginex.lakehouse.catalog import DataCatalog

catalog = DataCatalog(db_path=".dex/store.duckdb")
catalog.register("events_gold", path="data/gold/events", format="parquet")
entry = catalog.get("events_gold")
print(entry.path, entry.row_count)
```

______________________________________________________________________

## Partitioning

`dataenginex.lakehouse.partitioning`

Partition strategy definitions (Hive-style, date-based, hash) and helpers for computing partition keys from DataFrames.

::: dataenginex.lakehouse.partitioning

**Key classes:** `PartitionStrategy`, `HivePartitioner`, `DatePartitioner`

```python
from dataenginex.lakehouse.partitioning import HivePartitioner

partitioner = HivePartitioner(columns=["year", "month", "day"])
partitioned = partitioner.partition(df, base_path="data/silver/events")
```
