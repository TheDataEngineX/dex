"""Conformance tests for BaseFeatureStore implementations."""

from __future__ import annotations

from typing import Any

import pytest


class FeatureStoreConformanceTests:
    """All BaseFeatureStore implementations must pass these tests.

    Subclass and provide a ``feature_store`` fixture.
    """

    @pytest.fixture()
    def feature_store(self) -> Any:
        raise NotImplementedError

    def test_save_and_get_features(self, feature_store: Any) -> None:
        data = [
            {"user_id": "u1", "age": 25, "score": 0.9},
            {"user_id": "u2", "age": 30, "score": 0.8},
        ]
        feature_store.save_features("users", data, entity_key="user_id")
        result = feature_store.get_features("users", ["u1"])
        assert len(result) == 1
        assert result[0]["user_id"] == "u1"

    def test_list_feature_groups(self, feature_store: Any) -> None:
        data = [{"id": "1", "val": 42}]
        feature_store.save_features("group_a", data, entity_key="id")
        groups = feature_store.list_feature_groups()
        assert "group_a" in groups

    def test_get_features_missing_group(self, feature_store: Any) -> None:
        with pytest.raises(KeyError):
            feature_store.get_features("nonexistent", ["1"])

    def test_save_empty_data(self, feature_store: Any) -> None:
        feature_store.save_features("empty_group", [], entity_key="id")
        # Empty save should not create group
