"""Tests for the API factory and routers."""

from __future__ import annotations

from unittest.mock import patch

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
    with TestClient(app) as c:
        yield c


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
        assert "pipeline" in data
        assert data["pipeline"] == "ingest"
        result = data.get("result") or data
        assert "success" in result

    def test_run_pipeline_not_found(self, client) -> None:
        resp = client.post("/api/v1/pipelines/nonexistent/run")
        assert resp.status_code == 404


class TestPipelineExecution:
    def test_run_pipeline_returns_result(self, client) -> None:
        """POST /api/v1/pipelines/{name}/run returns PipelineResult fields."""
        resp = client.post("/api/v1/pipelines/ingest/run")
        assert resp.status_code == 200
        data = resp.json()
        assert "pipeline" in data
        result = data.get("result") or data
        assert "success" in result
        assert "rows_input" in result
        assert "rows_output" in result
        assert "steps_completed" in result


class TestAppFactory:
    def test_create_app_defaults(self) -> None:
        app = create_app()
        assert app.title == "dataenginex"

    def test_create_app_with_config(self) -> None:
        config = DexConfig(project=ProjectConfig(name="custom", version="2.0.0"))
        app = create_app(config)
        assert app.title == "custom"
        assert app.version == "2.0.0"


class TestLifespan:
    def test_pipeline_runner_initialized(self, client) -> None:
        """After app startup, pipeline_runner should be on app.state."""
        assert hasattr(client.app.state, "pipeline_runner")
        assert client.app.state.pipeline_runner is not None

    def test_tracker_initialized(self, client) -> None:
        assert hasattr(client.app.state, "tracker")
        assert client.app.state.tracker is not None

    def test_feature_store_initialized(self, client) -> None:
        assert hasattr(client.app.state, "feature_store")

    def test_serving_engine_initialized(self, client) -> None:
        assert hasattr(client.app.state, "serving_engine")
        assert client.app.state.serving_engine is not None

    def test_agents_dict_initialized(self, client) -> None:
        assert hasattr(client.app.state, "agents")
        assert isinstance(client.app.state.agents, dict)

    def test_llm_graceful_degradation(self) -> None:
        """LLM failure should not prevent app startup."""
        config = DexConfig(project=ProjectConfig(name="test-degraded"))
        with patch(
            "dataenginex.api.factory.get_llm_provider",
            side_effect=Exception("Ollama not running"),
        ):
            app = create_app(config)
            with TestClient(app) as tc:
                assert tc.app.state.llm is None

    def test_lineage_initialized(self, client) -> None:
        assert hasattr(client.app.state, "lineage")


class TestMiddleware:
    def test_request_logging_middleware(self, client) -> None:
        """Request logging middleware adds X-Request-ID header."""
        resp = client.get("/")
        assert "x-request-id" in resp.headers

    def test_metrics_middleware_tracks_requests(self, client) -> None:
        """Metrics middleware should track HTTP requests."""
        client.get("/")
        resp = client.get("/metrics")
        assert resp.status_code == 200
        assert b"http_requests_total" in resp.content
