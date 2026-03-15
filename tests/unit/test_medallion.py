"""Tests for medallion architecture components."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from dataenginex.core.medallion_architecture import (
    BigQueryStorage,
    DataLayer,
    DataLineage,
    DualStorage,
    LayerConfiguration,
    LocalParquetStorage,
    MedallionArchitecture,
    StorageFormat,
)

pa = pytest.importorskip("pyarrow", reason="pyarrow required for storage tests")

# ---------------------------------------------------------------------------
# LayerConfiguration
# ---------------------------------------------------------------------------


class TestLayerConfiguration:
    def test_valid_construction(self) -> None:
        cfg = LayerConfiguration(
            layer_name="bronze",
            description="raw data",
            purpose="preserve",
            storage_format=StorageFormat.PARQUET,
            local_path="data/bronze",
            bigquery_dataset="ds_bronze",
            retention_days=30,
            schema_validation=False,
            quality_threshold=0.0,
        )
        assert cfg.layer_name == "bronze"
        assert cfg.compression == "snappy"

    def test_invalid_quality_threshold_high(self) -> None:
        with pytest.raises(ValueError, match="quality_threshold"):
            LayerConfiguration(
                layer_name="gold",
                description="d",
                purpose="p",
                storage_format=StorageFormat.PARQUET,
                local_path="data/gold",
                bigquery_dataset="ds_gold",
                retention_days=None,
                schema_validation=True,
                quality_threshold=1.5,
            )

    def test_invalid_quality_threshold_negative(self) -> None:
        with pytest.raises(ValueError, match="quality_threshold"):
            LayerConfiguration(
                layer_name="gold",
                description="d",
                purpose="p",
                storage_format=StorageFormat.PARQUET,
                local_path="data/gold",
                bigquery_dataset="ds_gold",
                retention_days=None,
                schema_validation=True,
                quality_threshold=-0.1,
            )


# ---------------------------------------------------------------------------
# MedallionArchitecture
# ---------------------------------------------------------------------------


class TestMedallionArchitecture:
    def test_get_bronze_config(self) -> None:
        cfg = MedallionArchitecture.get_layer_config(DataLayer.BRONZE)
        assert cfg is not None
        assert cfg.layer_name == "bronze"
        assert cfg.quality_threshold == 0.0

    def test_get_silver_config(self) -> None:
        cfg = MedallionArchitecture.get_layer_config(DataLayer.SILVER)
        assert cfg is not None
        assert cfg.quality_threshold == 0.75

    def test_get_gold_config(self) -> None:
        cfg = MedallionArchitecture.get_layer_config(DataLayer.GOLD)
        assert cfg is not None
        assert cfg.quality_threshold == 0.90

    def test_get_all_layers_returns_three(self) -> None:
        layers = MedallionArchitecture.get_all_layers()
        assert len(layers) == 3
        assert [layer.layer_name for layer in layers] == ["bronze", "silver", "gold"]


# ---------------------------------------------------------------------------
# LocalParquetStorage
# ---------------------------------------------------------------------------


class TestLocalParquetStorage:
    def test_write_and_read_roundtrip(self, tmp_path: object) -> None:
        storage = LocalParquetStorage(str(tmp_path))
        data = [{"a": 1, "b": "x"}, {"a": 2, "b": "y"}]
        assert storage.write(data, "test/data.parquet") is True
        result = storage.read("test/data.parquet")
        assert result is not None
        assert len(result) == 2
        assert result[0]["a"] == 1

    def test_write_wrong_format_raises(self) -> None:
        storage = LocalParquetStorage("data")
        with pytest.raises(ValueError, match="PARQUET"):
            storage.write([{"a": 1}], "test/path", StorageFormat.BIGQUERY)

    def test_read_missing_returns_none(self, tmp_path: object) -> None:
        storage = LocalParquetStorage(str(tmp_path))
        result = storage.read("nonexistent/path.parquet")
        assert result is None

    def test_delete_existing_file(self, tmp_path: object) -> None:
        storage = LocalParquetStorage(str(tmp_path))
        storage.write([{"a": 1}], "todelete.parquet")
        assert storage.delete("todelete.parquet") is True
        assert storage.read("todelete.parquet") is None

    def test_delete_nonexistent_returns_false(self, tmp_path: object) -> None:
        storage = LocalParquetStorage(str(tmp_path))
        assert storage.delete("no_such_file.parquet") is False


# ---------------------------------------------------------------------------
# BigQueryStorage
# ---------------------------------------------------------------------------


class TestBigQueryStorage:
    def test_write_delegates_to_client(self) -> None:
        mock_client = MagicMock()
        mock_client.load_table_from_json.return_value = MagicMock()
        storage = BigQueryStorage("my-project", client=mock_client)
        result = storage.write({"a": 1}, "ds.table")
        assert result is True
        mock_client.load_table_from_json.assert_called_once()

    def test_read_delegates_to_client(self) -> None:
        mock_client = MagicMock()
        mock_client.list_rows.return_value = []
        storage = BigQueryStorage("my-project", client=mock_client)
        result = storage.read("ds.table")
        assert result == []

    def test_delete_delegates_to_client(self) -> None:
        mock_client = MagicMock()
        storage = BigQueryStorage("my-project", client=mock_client)
        result = storage.delete("ds.table")
        assert result is True
        mock_client.delete_table.assert_called_once()

    def test_list_objects_delegates_to_client(self) -> None:
        mock_table = MagicMock()
        mock_table.table_id = "my_table"
        mock_client = MagicMock()
        mock_client.list_tables.return_value = [mock_table]
        storage = BigQueryStorage("my-project", client=mock_client)
        result = storage.list_objects()
        assert result == ["my_table"]

    def test_exists_delegates_to_client(self) -> None:
        mock_client = MagicMock()
        storage = BigQueryStorage("my-project", client=mock_client)
        assert storage.exists("ds.table") is True


# ---------------------------------------------------------------------------
# DualStorage
# ---------------------------------------------------------------------------


class TestDualStorage:
    def test_local_only_write_bronze(self, tmp_path: object) -> None:
        ds = DualStorage(local_base_path=str(tmp_path))
        assert ds.write_bronze([{"x": 1}], "linkedin", "2025-01-01") is True

    def test_local_only_write_silver(self, tmp_path: object) -> None:
        ds = DualStorage(local_base_path=str(tmp_path))
        assert ds.write_silver([{"x": 1}], "jobs", "2025-01-01") is True

    def test_local_only_write_gold(self, tmp_path: object) -> None:
        ds = DualStorage(local_base_path=str(tmp_path))
        assert ds.write_gold([{"x": 1}], "jobs", "2025-01-01") is True

    def test_local_only_read_layers(self, tmp_path: object) -> None:
        ds = DualStorage(local_base_path=str(tmp_path))
        assert ds.read_bronze("src", "ts") is None
        assert ds.read_silver("ent", "ts") is None
        assert ds.read_gold("ent", "ts") is None

    def test_bigquery_mode_creates_storage(self) -> None:
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(
                "dataenginex.lakehouse.storage.bq_client.Client",
                MagicMock(),
            )
            ds = DualStorage(
                local_base_path="data",
                bigquery_project="my-project",
                enable_bigquery=True,
            )
            assert ds.bigquery_storage is not None


# ---------------------------------------------------------------------------
# DataLineage
# ---------------------------------------------------------------------------


class TestDataLineage:
    def test_record_bronze(self) -> None:
        dl = DataLineage()
        lid = dl.record_bronze_ingestion("linkedin", 100, "2025-01-01")
        assert lid.startswith("bronze_")
        info = dl.get_lineage(lid)
        assert info is not None
        assert info["record_count"] == 100

    def test_record_silver(self) -> None:
        dl = DataLineage()
        b_id = dl.record_bronze_ingestion("indeed", 50, "2025-01-01")
        s_id = dl.record_silver_transformation(b_id, 45, 0.82)
        info = dl.get_lineage(s_id)
        assert info is not None
        assert info["quality_score"] == 0.82
        assert info["parent"] == b_id

    def test_record_gold(self) -> None:
        dl = DataLineage()
        b_id = dl.record_bronze_ingestion("indeed", 50, "2025-01-01")
        g_id = dl.record_gold_enrichment(b_id, 40, "all-MiniLM-L6-v2")
        info = dl.get_lineage(g_id)
        assert info is not None
        assert info["embedding_model"] == "all-MiniLM-L6-v2"

    def test_get_missing_lineage(self) -> None:
        dl = DataLineage()
        assert dl.get_lineage("nonexistent") is None
