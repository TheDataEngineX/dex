"""Tests for the AI router — /api/v1/ai."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from dataenginex.api.routers.ai import router
from dataenginex.config.schema import AgentConfig, AiConfig, DexConfig, ProjectConfig


@pytest.fixture()
def app() -> FastAPI:
    config = DexConfig(
        project=ProjectConfig(name="test-ai"),
        ai=AiConfig(
            agents={
                "data-analyst": AgentConfig(
                    runtime="builtin",
                    system_prompt="You analyze data.",
                    tools=["query_sql"],
                    max_iterations=5,
                ),
            },
        ),
    )
    app = FastAPI()
    app.state.config = config

    # Mock agents
    mock_agent = AsyncMock()
    mock_agent.run.return_value = {
        "response": "The answer is 42",
        "iterations": 2,
        "tool_calls": 1,
    }
    app.state.agents = {"data-analyst": mock_agent}
    app.state.llm = MagicMock()

    app.include_router(router, prefix="/api/v1")
    return app


@pytest.fixture()
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


class TestAgentEndpoints:
    def test_list_agents(self, client: TestClient) -> None:
        resp = client.get("/api/v1/ai/agents")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1

    def test_get_agent(self, client: TestClient) -> None:
        resp = client.get("/api/v1/ai/agents/data-analyst")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "data-analyst"
        assert data["runtime"] == "builtin"

    def test_get_agent_not_found(self, client: TestClient) -> None:
        resp = client.get("/api/v1/ai/agents/nonexistent")
        assert resp.status_code == 404

    def test_agent_chat(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/ai/agents/data-analyst/chat",
            json={"message": "What is 6 * 7?"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["agent"] == "data-analyst"
        assert data["response"] == "The answer is 42"
        assert data["iterations"] == 2
        assert data["tool_calls"] == 1

    def test_agent_chat_not_found(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/ai/agents/nonexistent/chat",
            json={"message": "Hello"},
        )
        assert resp.status_code == 404


class TestToolEndpoints:
    def test_list_tools(self, client: TestClient) -> None:
        resp = client.get("/api/v1/ai/tools")
        assert resp.status_code == 200
        data = resp.json()
        assert "tools" in data
        assert "count" in data
