"""Tests for the ML router — /api/v1/ml."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from dataenginex.api.routers.ml import router


@pytest.fixture()
def app() -> FastAPI:
    app = FastAPI()

    # Mock tracker
    mock_tracker = MagicMock()
    mock_tracker.list_experiments.return_value = [
        {"id": "abc123", "name": "exp-1"},
    ]
    mock_tracker.create_experiment.return_value = "abc123"
    mock_tracker.list_runs.return_value = []
    app.state.tracker = mock_tracker

    # Mock model registry — matches ModelRegistry interface (list_models, list_versions)
    mock_registry = MagicMock()
    mock_registry.list_models.return_value = []
    mock_registry.list_versions.return_value = []
    app.state.model_registry = mock_registry

    # Mock serving engine
    mock_serving = MagicMock()
    mock_serving.list_models.return_value = []
    app.state.serving_engine = mock_serving

    # Mock feature store
    mock_fs = MagicMock()
    mock_fs.list_feature_groups.return_value = ["user_features"]
    mock_fs.get_features.return_value = []
    app.state.feature_store = mock_fs

    # Config needed for drift endpoint
    from dataenginex.config.schema import (
        DataConfig,
        DexConfig,
        PipelineConfig,
        ProjectConfig,
        SourceConfig,
    )

    app.state.config = DexConfig(
        project=ProjectConfig(name="test-ml"),
        data=DataConfig(
            sources={"movies": SourceConfig(type="csv", path="movies.csv")},
            pipelines={"ingest": PipelineConfig(source="movies")},
        ),
    )

    app.include_router(router, prefix="/api/v1")
    return app


@pytest.fixture()
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


class TestExperiments:
    def test_list_experiments(self, client: TestClient) -> None:
        resp = client.get("/api/v1/ml/experiments")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1

    def test_create_experiment(self, client: TestClient) -> None:
        resp = client.post("/api/v1/ml/experiments/new-exp")
        assert resp.status_code == 200


class TestModels:
    def test_list_models(self, client: TestClient) -> None:
        resp = client.get("/api/v1/ml/models")
        assert resp.status_code == 200
        data = resp.json()
        assert "models" in data

    def test_get_model_not_found(self, client: TestClient, app: FastAPI) -> None:
        app.state.model_registry.get_latest.return_value = None
        resp = client.get("/api/v1/ml/models/nonexistent")
        assert resp.status_code == 404


class TestFeatures:
    def test_list_feature_groups(self, client: TestClient) -> None:
        resp = client.get("/api/v1/ml/features")
        assert resp.status_code == 200
        data = resp.json()
        assert "groups" in data


class TestPredictions:
    def test_predict(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/ml/predictions",
            json={"model_name": "test", "features": {"x": 1.0}},
        )
        assert resp.status_code == 200


class TestDrift:
    def test_drift_found_pipeline(self, client: TestClient) -> None:
        resp = client.get("/api/v1/ml/drift/ingest")
        assert resp.status_code == 200
        data = resp.json()
        assert data["pipeline"] == "ingest"
        assert data["status"] == "no_baseline"

    def test_drift_pipeline_not_found(self, client: TestClient) -> None:
        resp = client.get("/api/v1/ml/drift/unknown")
        assert resp.status_code == 404
