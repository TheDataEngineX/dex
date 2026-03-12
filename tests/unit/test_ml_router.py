"""Tests for ML model serving router endpoints."""

from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from dataenginex.ml.registry import ModelArtifact, ModelRegistry, ModelStage
from dataenginex.ml.serving import ModelServer
from fastapi import FastAPI
from fastapi.testclient import TestClient

from careerdex.api.routers.ml import ml_router, set_model_server

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def registry() -> ModelRegistry:
    """Create a ModelRegistry with a test model."""
    reg = ModelRegistry()
    reg.register(
        ModelArtifact(
            name="test-model",
            version="1.0.0",
            stage=ModelStage.PRODUCTION,
            metrics={"accuracy": 0.95},
            parameters={"n_estimators": 100},
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
    )
    return reg


@pytest.fixture()
def model_server(registry: ModelRegistry) -> ModelServer:
    """Create a ModelServer backed by the test registry with a mock model loaded."""
    server = ModelServer(registry=registry)
    mock_model = MagicMock()
    mock_model.predict.return_value = [0.42]
    server.load_model("test-model", "1.0.0", mock_model)
    return server


@pytest.fixture()
def client(model_server: ModelServer, registry: ModelRegistry) -> TestClient:
    """Create a FastAPI test client with the ML router."""
    app = FastAPI()
    app.include_router(ml_router)
    set_model_server(model_server, registry)
    return TestClient(app)


@pytest.fixture()
def unconfigured_client() -> Generator[TestClient, None, None]:
    """Create a client without a configured model server."""
    from careerdex.api.routers import ml as ml_module

    # Temporarily clear the server
    original_server = ml_module._model_server
    original_registry = ml_module._model_registry
    ml_module._model_server = None
    ml_module._model_registry = None

    app = FastAPI()
    app.include_router(ml_router)
    client = TestClient(app)
    yield client

    # Restore
    ml_module._model_server = original_server
    ml_module._model_registry = original_registry


# ---------------------------------------------------------------------------
# POST /api/v1/predict
# ---------------------------------------------------------------------------


class TestPredictEndpoint:
    """Tests for POST /api/v1/predict."""

    def test_predict_success(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/predict",
            json={
                "model_name": "test-model",
                "features": [{"feature_a": 1.0, "feature_b": 2.0}],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["model_name"] == "test-model"
        assert "predictions" in data
        assert "latency_ms" in data
        assert "served_at" in data

    def test_predict_with_version(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/predict",
            json={
                "model_name": "test-model",
                "version": "1.0.0",
                "features": [{"x": 42}],
            },
        )
        assert resp.status_code == 200
        assert resp.json()["version"] == "1.0.0"

    def test_predict_model_not_found(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/predict",
            json={
                "model_name": "nonexistent",
                "features": [{"x": 1}],
            },
        )
        assert resp.status_code in (404, 500)

    def test_predict_server_not_configured(self, unconfigured_client: TestClient) -> None:
        resp = unconfigured_client.post(
            "/api/v1/predict",
            json={
                "model_name": "any",
                "features": [{"x": 1}],
            },
        )
        assert resp.status_code == 503
        assert "not configured" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# GET /api/v1/models
# ---------------------------------------------------------------------------


class TestListModelsEndpoint:
    """Tests for GET /api/v1/models."""

    def test_list_models(self, client: TestClient) -> None:
        resp = client.get("/api/v1/models")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert any(m["name"] == "test-model" for m in data["models"])

    def test_list_models_not_configured(self, unconfigured_client: TestClient) -> None:
        resp = unconfigured_client.get("/api/v1/models")
        assert resp.status_code == 503


# ---------------------------------------------------------------------------
# GET /api/v1/models/{name}
# ---------------------------------------------------------------------------


class TestGetModelMetadataEndpoint:
    """Tests for GET /api/v1/models/{name}."""

    def test_get_model_metadata(self, client: TestClient) -> None:
        resp = client.get("/api/v1/models/test-model")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "test-model"
        assert data["version"] == "1.0.0"
        assert data["stage"] == "production"
        assert data["metrics"]["accuracy"] == 0.95

    def test_get_model_not_found(self, client: TestClient) -> None:
        resp = client.get("/api/v1/models/nonexistent")
        assert resp.status_code == 404

    def test_get_model_not_configured(self, unconfigured_client: TestClient) -> None:
        resp = unconfigured_client.get("/api/v1/models/any")
        assert resp.status_code == 503
