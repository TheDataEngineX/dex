"""Tests for the data router — /api/v1/data."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from dataenginex.api.routers.data import router
from dataenginex.config.schema import (
    DataConfig,
    DexConfig,
    PipelineConfig,
    ProjectConfig,
    SourceConfig,
)


@pytest.fixture()
def app() -> FastAPI:
    config = DexConfig(
        project=ProjectConfig(name="test-data"),
        data=DataConfig(
            sources={"movies": SourceConfig(type="csv", path="movies.csv")},
            pipelines={"ingest": PipelineConfig(source="movies")},
        ),
    )
    app = FastAPI()
    app.state.config = config

    # Mock lineage
    mock_lineage = MagicMock()
    mock_lineage.all_events = []
    mock_lineage.get_event.return_value = None
    app.state.lineage = mock_lineage

    app.include_router(router, prefix="/api/v1")
    return app


@pytest.fixture()
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


class TestSourcesEndpoints:
    def test_list_sources(self, client: TestClient) -> None:
        resp = client.get("/api/v1/data/sources")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1
        assert data["sources"][0]["name"] == "movies"

    def test_get_source(self, client: TestClient) -> None:
        resp = client.get("/api/v1/data/sources/movies")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "movies"
        assert data["type"] == "csv"

    def test_get_source_not_found(self, client: TestClient) -> None:
        resp = client.get("/api/v1/data/sources/nonexistent")
        assert resp.status_code == 404


class TestLineageEndpoints:
    def test_list_lineage(self, client: TestClient) -> None:
        resp = client.get("/api/v1/data/lineage")
        assert resp.status_code == 200
        data = resp.json()
        assert "events" in data

    def test_get_lineage_event_not_found(self, client: TestClient) -> None:
        resp = client.get("/api/v1/data/lineage/nonexistent")
        assert resp.status_code == 404


class TestWarehouseEndpoints:
    def test_list_layers(self, client: TestClient) -> None:
        resp = client.get("/api/v1/data/warehouse/layers")
        assert resp.status_code == 200
        data = resp.json()
        assert "layers" in data
        layer_names = [layer["name"] for layer in data["layers"]]
        assert "bronze" in layer_names


class TestQualityEndpoints:
    def test_quality_summary(self, client: TestClient) -> None:
        resp = client.get("/api/v1/data/quality/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert "pipelines" in data


class TestSQLQueryEndpoint:
    def test_simple_select(self, client: TestClient) -> None:
        resp = client.post("/api/v1/data/query", json={"sql": "SELECT 1 AS n"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["columns"] == ["n"]
        assert data["rows"] == [{"n": 1}]
        assert data["count"] == 1

    def test_invalid_sql_returns_400(self, client: TestClient) -> None:
        resp = client.post("/api/v1/data/query", json={"sql": "SELECT * FROM no_such_table"})
        assert resp.status_code == 400

    def test_limit_respected(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/data/query",
            json={"sql": "SELECT unnest([1,2,3,4,5]) AS n", "limit": 3},
        )
        assert resp.status_code == 200
        assert resp.json()["count"] == 3
