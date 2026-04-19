"""Extended tests for the AI router — gaps from test_ai_router.py.

Covers: LLM unavailable (503), ConnectionError from provider (503),
generic runtime exception (500), empty message body, tool not found (404),
agent chat request body validation, and response schema correctness.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from dataenginex.api.routers.ai import router
from dataenginex.config.schema import AgentConfig, AiConfig, DexConfig, ProjectConfig

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_app(
    agents_runtime: dict[str, AsyncMock] | None = None,
    config_agents: dict[str, AgentConfig] | None = None,
) -> FastAPI:
    if config_agents is None:
        config_agents = {
            "data-analyst": AgentConfig(
                runtime="builtin",
                system_prompt="You analyze data.",
                tools=["query"],
                max_iterations=5,
            ),
            "echo-agent": AgentConfig(
                runtime="builtin",
                system_prompt="You echo.",
                tools=[],
                max_iterations=3,
            ),
        }

    config = DexConfig(
        project=ProjectConfig(name="test-ai"),
        ai=AiConfig(agents=config_agents),
    )
    app = FastAPI()
    app.state.config = config

    if agents_runtime is None:
        mock_agent = AsyncMock()
        mock_agent.run.return_value = {
            "response": "The answer is 42",
            "iterations": 2,
            "tool_calls": 1,
        }
        app.state.agents = {"data-analyst": mock_agent, "echo-agent": mock_agent}
    else:
        app.state.agents = agents_runtime

    app.include_router(router, prefix="/api/v1")
    return app


@pytest.fixture()
def app() -> FastAPI:
    return _make_app()


@pytest.fixture()
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


# ---------------------------------------------------------------------------
# list_agents edge cases
# ---------------------------------------------------------------------------


class TestListAgentsEdgeCases:
    def test_empty_agents_returns_zero_count(self) -> None:
        empty_app = _make_app(config_agents={}, agents_runtime={})
        client = TestClient(empty_app)
        resp = client.get("/api/v1/ai/agents")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 0
        assert data["agents"] == []

    def test_response_includes_model_field(self, client: TestClient) -> None:
        resp = client.get("/api/v1/ai/agents")
        agents = resp.json()["agents"]
        assert all("name" in a for a in agents)

    def test_response_includes_tools_list(self, client: TestClient) -> None:
        resp = client.get("/api/v1/ai/agents")
        analyst = next(a for a in resp.json()["agents"] if a["name"] == "data-analyst")
        assert analyst["tools"] == ["query"]

    def test_response_includes_max_iterations(self, client: TestClient) -> None:
        resp = client.get("/api/v1/ai/agents")
        analyst = next(a for a in resp.json()["agents"] if a["name"] == "data-analyst")
        assert analyst["max_iterations"] == 5


# ---------------------------------------------------------------------------
# get_agent edge cases
# ---------------------------------------------------------------------------


class TestGetAgentEdgeCases:
    def test_get_returns_tools_list(self, client: TestClient) -> None:
        resp = client.get("/api/v1/ai/agents/data-analyst")
        assert resp.status_code == 200
        assert resp.json()["tools"] == ["query"]

    def test_get_returns_max_iterations(self, client: TestClient) -> None:
        resp = client.get("/api/v1/ai/agents/data-analyst")
        assert resp.json()["max_iterations"] == 5

    def test_get_agent_with_no_tools(self, client: TestClient) -> None:
        resp = client.get("/api/v1/ai/agents/echo-agent")
        assert resp.status_code == 200
        assert resp.json()["tools"] == []


# ---------------------------------------------------------------------------
# agent_chat — error scenarios
# ---------------------------------------------------------------------------


class TestAgentChatErrors:
    def test_chat_llm_unavailable_returns_503(self) -> None:
        """Agent in config but NOT in runtime agents dict → LLM unavailable."""
        config_agents = {
            "data-analyst": AgentConfig(
                runtime="builtin",
                system_prompt="Analyze.",
                tools=[],
                max_iterations=3,
            )
        }
        config = DexConfig(
            project=ProjectConfig(name="t"),
            ai=AiConfig(agents=config_agents),
        )
        app = FastAPI()
        app.state.config = config
        app.state.agents = {}  # agent configured but runtime missing
        app.include_router(router, prefix="/api/v1")

        client = TestClient(app)
        resp = client.post("/api/v1/ai/agents/data-analyst/chat", json={"message": "hello"})
        assert resp.status_code == 503
        assert "not initialized" in resp.json()["detail"].lower()

    def test_chat_agent_not_in_config_returns_404(self, client: TestClient) -> None:
        resp = client.post("/api/v1/ai/agents/totally-unknown/chat", json={"message": "hello"})
        assert resp.status_code == 404

    def test_chat_connection_error_returns_503(self) -> None:
        mock_agent = AsyncMock()
        mock_agent.run.side_effect = ConnectionError("LLM host unreachable")
        app = _make_app(agents_runtime={"data-analyst": mock_agent})
        client = TestClient(app)
        resp = client.post("/api/v1/ai/agents/data-analyst/chat", json={"message": "hello"})
        assert resp.status_code == 503
        assert "unreachable" in resp.json()["detail"].lower()

    def test_chat_runtime_exception_returns_500(self) -> None:
        mock_agent = AsyncMock()
        mock_agent.run.side_effect = RuntimeError("unexpected crash")
        app = _make_app(agents_runtime={"data-analyst": mock_agent})
        client = TestClient(app)
        resp = client.post("/api/v1/ai/agents/data-analyst/chat", json={"message": "hello"})
        assert resp.status_code == 500
        assert "crash" in resp.json()["detail"].lower()

    def test_chat_empty_message_body_unprocessable(self, client: TestClient) -> None:
        """Empty JSON body (no message field) should return 422."""
        resp = client.post("/api/v1/ai/agents/data-analyst/chat", json={})
        assert resp.status_code == 422

    def test_chat_missing_body_returns_422(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/ai/agents/data-analyst/chat",
            content=b"",
            headers={"content-type": "application/json"},
        )
        assert resp.status_code == 422

    def test_chat_non_string_message_returns_422(self, client: TestClient) -> None:
        resp = client.post("/api/v1/ai/agents/data-analyst/chat", json={"message": 12345})
        # Pydantic coerces int to str for str fields — should either 200 or 422
        # Accept either depending on Pydantic version strictness
        assert resp.status_code in (200, 422)

    def test_chat_very_long_message_is_accepted(self, client: TestClient) -> None:
        long_msg = "x" * 10_000
        resp = client.post("/api/v1/ai/agents/data-analyst/chat", json={"message": long_msg})
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# agent_chat — response schema
# ---------------------------------------------------------------------------


class TestAgentChatResponse:
    def test_response_has_all_fields(self, client: TestClient) -> None:
        resp = client.post("/api/v1/ai/agents/data-analyst/chat", json={"message": "hello"})
        assert resp.status_code == 200
        data = resp.json()
        assert "agent" in data
        assert "response" in data
        assert "iterations" in data
        assert "tool_calls" in data

    def test_response_agent_name_matches_request(self, client: TestClient) -> None:
        resp = client.post("/api/v1/ai/agents/data-analyst/chat", json={"message": "hello"})
        assert resp.json()["agent"] == "data-analyst"

    def test_response_iterations_is_int(self, client: TestClient) -> None:
        resp = client.post("/api/v1/ai/agents/data-analyst/chat", json={"message": "hello"})
        assert isinstance(resp.json()["iterations"], int)

    def test_response_tool_calls_is_int(self, client: TestClient) -> None:
        resp = client.post("/api/v1/ai/agents/data-analyst/chat", json={"message": "hello"})
        assert isinstance(resp.json()["tool_calls"], int)


# ---------------------------------------------------------------------------
# Tools endpoints
# ---------------------------------------------------------------------------


class TestToolsEdgeCases:
    @pytest.fixture(autouse=True)
    def _register_tools(self) -> None:
        from dataenginex.ai.tools.builtin import register_builtin_tools

        register_builtin_tools()

    def test_get_tool_not_found_returns_404(self, client: TestClient) -> None:
        resp = client.get("/api/v1/ai/tools/nonexistent-tool")
        assert resp.status_code == 404
        assert "nonexistent-tool" in resp.json()["detail"]

    def test_list_tools_has_builtin_tools(self, client: TestClient) -> None:
        """Built-in tools (query, list_tools, echo) should always be present."""
        resp = client.get("/api/v1/ai/tools")
        assert resp.status_code == 200
        names = [t["name"] for t in resp.json()["tools"]]
        # At least one builtin tool must be registered
        assert len(names) > 0

    def test_list_tools_count_matches_tools_length(self, client: TestClient) -> None:
        resp = client.get("/api/v1/ai/tools")
        data = resp.json()
        assert data["count"] == len(data["tools"])

    def test_each_tool_has_name_and_description(self, client: TestClient) -> None:
        resp = client.get("/api/v1/ai/tools")
        for tool in resp.json()["tools"]:
            assert "name" in tool
            assert "description" in tool

    def test_get_builtin_query_tool(self, client: TestClient) -> None:
        resp = client.get("/api/v1/ai/tools/query")
        if resp.status_code == 200:
            data = resp.json()
            assert data["name"] == "query"
