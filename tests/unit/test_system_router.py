"""Tests for the system router — /api/v1/system."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from dataenginex.api.routers.system import router


@pytest.fixture()
def app() -> FastAPI:
    app = FastAPI()
    app.state.tracker = MagicMock()
    app.state.feature_store = MagicMock()
    app.state.serving_engine = MagicMock()
    app.state.llm = MagicMock()
    app.state.agents = {"test-agent": MagicMock()}
    app.state.pipeline_runner = MagicMock()
    app.include_router(router, prefix="/api/v1")
    return app


@pytest.fixture()
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


class TestComponentHealth:
    def test_list_components(self, client: TestClient) -> None:
        resp = client.get("/api/v1/system/components")
        assert resp.status_code == 200
        data = resp.json()
        assert "components" in data
        names = [c["name"] for c in data["components"]]
        assert "tracker" in names
        assert "feature_store" in names
        assert "llm" in names

    def test_llm_unavailable_shows_degraded(self) -> None:
        app = FastAPI()
        app.state.tracker = MagicMock()
        app.state.feature_store = MagicMock()
        app.state.serving_engine = MagicMock()
        app.state.llm = None
        app.state.agents = {}
        app.state.pipeline_runner = MagicMock()
        app.include_router(router, prefix="/api/v1")
        client = TestClient(app)

        resp = client.get("/api/v1/system/components")
        data = resp.json()
        llm = next(c for c in data["components"] if c["name"] == "llm")
        assert llm["status"] == "unavailable"


class TestLogs:
    def test_get_logs(self, client: TestClient) -> None:
        resp = client.get("/api/v1/system/logs")
        assert resp.status_code == 200
        data = resp.json()
        assert "logs" in data
