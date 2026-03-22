"""Tests for the API factory and routers."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from dataenginex.api.factory import create_app
from dataenginex.config.schema import (
    DataConfig,
    DexConfig,
    PipelineConfig,
    ProjectConfig,
    SourceConfig,
)


@pytest.fixture()
def app():
    config = DexConfig(
        project=ProjectConfig(name="test-app", version="0.1.0"),
        data=DataConfig(
            sources={"movies": SourceConfig(type="csv", path="movies.csv")},
            pipelines={
                "ingest": PipelineConfig(source="movies"),
                "transform": PipelineConfig(source="movies", depends_on=["ingest"]),
            },
        ),
    )
    return create_app(config)


@pytest.fixture()
def client(app):
    return TestClient(app)


class TestRootRouter:
    def test_root(self, client) -> None:
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["service"] == "dataenginex"
        assert data["status"] == "running"

    def test_metrics(self, client) -> None:
        resp = client.get("/metrics")
        assert resp.status_code == 200


class TestHealthRouter:
    def test_health(self, client) -> None:
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data


class TestPipelinesRouter:
    def test_list_pipelines(self, client) -> None:
        resp = client.get("/api/v1/pipelines/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 2
        assert "ingest" in data["pipelines"]

    def test_get_pipeline(self, client) -> None:
        resp = client.get("/api/v1/pipelines/ingest")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "ingest"
        assert data["source"] == "movies"

    def test_get_pipeline_not_found(self, client) -> None:
        resp = client.get("/api/v1/pipelines/nonexistent")
        assert resp.status_code == 404

    def test_run_pipeline(self, client) -> None:
        resp = client.post("/api/v1/pipelines/ingest/run")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "triggered"

    def test_run_pipeline_not_found(self, client) -> None:
        resp = client.post("/api/v1/pipelines/nonexistent/run")
        assert resp.status_code == 404


class TestAppFactory:
    def test_create_app_defaults(self) -> None:
        app = create_app()
        assert app.title == "dataenginex"

    def test_create_app_with_config(self) -> None:
        config = DexConfig(project=ProjectConfig(name="custom", version="2.0.0"))
        app = create_app(config)
        assert app.title == "custom"
        assert app.version == "2.0.0"
