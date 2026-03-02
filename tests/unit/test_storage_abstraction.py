"""Tests for storage abstraction — list_objects, exists, get_storage factory."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from dataenginex.lakehouse.storage import JsonStorage, get_storage

# ---------------------------------------------------------------------------
# JsonStorage.list_objects / .exists
# ---------------------------------------------------------------------------


class TestJsonStorageListObjects:
    """Verify JsonStorage.list_objects returns relative paths without extension."""

    def test_empty_directory(self, tmp_path: Path) -> None:
        store = JsonStorage(base_path=str(tmp_path))
        assert store.list_objects() == []

    def test_lists_json_files(self, tmp_path: Path) -> None:
        (tmp_path / "a.json").write_text(json.dumps({"x": 1}))
        (tmp_path / "b.json").write_text(json.dumps({"x": 2}))
        store = JsonStorage(base_path=str(tmp_path))
        result = sorted(store.list_objects())
        assert result == ["a", "b"]

    def test_lists_nested_files(self, tmp_path: Path) -> None:
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "nested.json").write_text(json.dumps({"x": 1}))
        store = JsonStorage(base_path=str(tmp_path))
        result = store.list_objects()
        assert "sub/nested" in result

    def test_with_prefix(self, tmp_path: Path) -> None:
        sub = tmp_path / "layer"
        sub.mkdir()
        (sub / "data.json").write_text(json.dumps({"x": 1}))
        (tmp_path / "other.json").write_text(json.dumps({"y": 2}))
        store = JsonStorage(base_path=str(tmp_path))
        result = store.list_objects(prefix="layer")
        assert result == ["layer/data"]

    def test_nonexistent_prefix(self, tmp_path: Path) -> None:
        store = JsonStorage(base_path=str(tmp_path))
        assert store.list_objects(prefix="does_not_exist") == []


class TestJsonStorageExists:
    """Verify JsonStorage.exists checks for .json file presence."""

    def test_exists_true(self, tmp_path: Path) -> None:
        (tmp_path / "record.json").write_text(json.dumps({"k": "v"}))
        store = JsonStorage(base_path=str(tmp_path))
        assert store.exists("record") is True

    def test_exists_false(self, tmp_path: Path) -> None:
        store = JsonStorage(base_path=str(tmp_path))
        assert store.exists("missing") is False


# ---------------------------------------------------------------------------
# get_storage factory
# ---------------------------------------------------------------------------


class TestGetStorage:
    """Verify URI-based storage backend creation."""

    def test_file_scheme(self, tmp_path: Path) -> None:
        store = get_storage(f"file://{tmp_path}")
        assert isinstance(store, JsonStorage)

    def test_no_scheme(self, tmp_path: Path) -> None:
        store = get_storage(str(tmp_path))
        assert isinstance(store, JsonStorage)

    def test_unsupported_scheme(self) -> None:
        with pytest.raises(ValueError, match="Unsupported storage URI scheme"):
            get_storage("ftp://example.com/data")

    def test_s3_scheme(self) -> None:
        """S3Storage is created (even without credentials)."""
        from dataenginex.lakehouse.storage import S3Storage

        store = get_storage("s3://my-bucket/prefix", endpoint_url="http://localhost:1")
        assert isinstance(store, S3Storage)

    def test_gs_scheme(self) -> None:
        """GCSStorage is created (even without credentials)."""
        from dataenginex.lakehouse.storage import GCSStorage

        store = get_storage("gs://my-bucket/prefix", api_endpoint="http://localhost:1")
        assert isinstance(store, GCSStorage)
