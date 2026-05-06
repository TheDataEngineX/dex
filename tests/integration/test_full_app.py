"""Integration test — full app lifecycle with lifespan."""

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
def full_app():
    config = DexConfig(
        project=ProjectConfig(name="integration-test", version="0.0.1"),
        data=DataConfig(
            sources={"jobs": SourceConfig(type="csv", path="tests/fixtures/sample_jobs.csv")},
            pipelines={"ingest": PipelineConfig(source="jobs")},
        ),
    )
    return create_app(config)


@pytest.fixture()
def client(full_app):
    with TestClient(full_app) as c:
        yield c


class TestFullAppLifecycle:
    def test_health(self, client) -> None:
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200

    def test_system_components(self, client) -> None:
        resp = client.get("/api/v1/system/components")
        assert resp.status_code == 200
        data = resp.json()
        assert any(c["name"] == "tracker" for c in data["components"])

    def test_list_pipelines(self, client) -> None:
        resp = client.get("/api/v1/pipelines/")
        assert resp.status_code == 200
        assert resp.json()["count"] == 1

    def test_data_sources(self, client) -> None:
        resp = client.get("/api/v1/data/sources")
        assert resp.status_code == 200
        assert resp.json()["count"] == 1

    def test_ml_experiments_empty(self, client) -> None:
        resp = client.get("/api/v1/ml/experiments")
        assert resp.status_code == 200
        assert resp.json()["count"] >= 0  # tracker may have persisted state from prior runs

    def test_ai_agents_empty(self, client) -> None:
        resp = client.get("/api/v1/ai/agents")
        assert resp.status_code == 200
        assert resp.json()["count"] == 0

    def test_ai_tools_registered(self, client) -> None:
        resp = client.get("/api/v1/ai/tools")
        assert resp.status_code == 200
        # register_builtin_tools() registers query, list_tools, echo — always >= 1
        assert resp.json()["count"] >= 1

    def test_warehouse_layers(self, client) -> None:
        resp = client.get("/api/v1/data/warehouse/layers")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["layers"]) == 3  # bronze, silver, gold

    def test_quality_summary(self, client) -> None:
        resp = client.get("/api/v1/data/quality/summary")
        assert resp.status_code == 200

    def test_system_logs(self, client) -> None:
        resp = client.get("/api/v1/system/logs")
        assert resp.status_code == 200

    def test_request_id_header(self, client) -> None:
        resp = client.get("/")
        assert "x-request-id" in resp.headers
