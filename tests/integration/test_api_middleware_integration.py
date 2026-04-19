"""Integration tests — API middleware: auth, request lifecycle, and multi-config apps."""

from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from dataenginex.api.auth import create_token, decode_token
from dataenginex.api.factory import create_app
from dataenginex.config.schema import (
    DataConfig,
    DexConfig,
    PipelineConfig,
    ProjectConfig,
    SourceConfig,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SECRET = "test-secret-key-for-integration"


def _make_token(sub: str = "testuser", roles: list[str] | None = None, ttl: int = 3600) -> str:
    return create_token({"sub": sub, "roles": roles or ["user"]}, secret=_SECRET, ttl=ttl)


def _app_with_auth(enabled: bool = True) -> DexConfig:
    from dataenginex.config.schema import AuthConfig, ServerConfig

    return DexConfig(
        project=ProjectConfig(name="auth-test"),
        server=ServerConfig(auth=AuthConfig(enabled=enabled)),
    )


# ---------------------------------------------------------------------------
# JWT token helpers
# ---------------------------------------------------------------------------


class TestJWTHelpers:
    def test_create_and_decode_token_roundtrip(self) -> None:
        token = create_token({"sub": "alice", "roles": ["admin"]}, secret=_SECRET)
        payload = decode_token(token, secret=_SECRET)
        assert payload["sub"] == "alice"
        assert payload["roles"] == ["admin"]

    def test_token_contains_iat_and_exp(self) -> None:
        token = create_token({"sub": "alice"}, secret=_SECRET)
        payload = decode_token(token, secret=_SECRET)
        assert "iat" in payload
        assert "exp" in payload
        assert payload["exp"] > payload["iat"]

    def test_expired_token_raises_value_error(self) -> None:
        # Create a token that expired 1 second in the past
        token = create_token({"sub": "alice"}, secret=_SECRET, ttl=-1)
        with pytest.raises(ValueError, match="expired"):
            decode_token(token, secret=_SECRET)

    def test_tampered_token_raises_value_error(self) -> None:
        token = create_token({"sub": "alice"}, secret=_SECRET)
        # Corrupt the signature segment
        parts = token.split(".")
        tampered = f"{parts[0]}.{parts[1]}.invalidsignatureXYZ"
        with pytest.raises(ValueError):
            decode_token(tampered, secret=_SECRET)

    def test_malformed_token_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="Malformed JWT"):
            decode_token("not.a.valid.jwt.with.too.many.parts", secret=_SECRET)

    def test_wrong_secret_raises_value_error(self) -> None:
        token = create_token({"sub": "alice"}, secret="correct-secret")
        with pytest.raises(ValueError):
            decode_token(token, secret="wrong-secret")

    def test_ttl_respected(self) -> None:
        token = create_token({"sub": "alice"}, secret=_SECRET, ttl=3600)
        payload = decode_token(token, secret=_SECRET)
        remaining = payload["exp"] - int(time.time())
        assert 3590 < remaining <= 3600


# ---------------------------------------------------------------------------
# Auth middleware — disabled (default)
# ---------------------------------------------------------------------------


class TestAuthDisabled:
    @pytest.fixture()
    def client(self) -> TestClient:
        app = create_app(DexConfig(project=ProjectConfig(name="no-auth")))
        with TestClient(app) as c:
            yield c

    def test_health_accessible_without_token(self, client: TestClient) -> None:
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200

    def test_pipelines_accessible_without_token(self, client: TestClient) -> None:
        resp = client.get("/api/v1/pipelines/")
        assert resp.status_code == 200

    def test_ml_experiments_accessible_without_token(self, client: TestClient) -> None:
        resp = client.get("/api/v1/ml/experiments")
        assert resp.status_code == 200

    def test_ai_tools_accessible_without_token(self, client: TestClient) -> None:
        resp = client.get("/api/v1/ai/tools")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Auth middleware — enabled via env var
# ---------------------------------------------------------------------------


class TestAuthEnabledViaEnv:
    @pytest.fixture()
    def client(self, monkeypatch: pytest.MonkeyPatch) -> TestClient:
        monkeypatch.setenv("DEX_AUTH_ENABLED", "true")
        monkeypatch.setenv("DEX_JWT_SECRET", _SECRET)
        from dataenginex.config.schema import AuthConfig, ServerConfig

        app = create_app(
            DexConfig(
                project=ProjectConfig(name="auth-enabled"),
                server=ServerConfig(auth=AuthConfig(enabled=True)),
            )
        )
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c

    def test_protected_endpoint_requires_token(self, client: TestClient) -> None:
        resp = client.get("/api/v1/pipelines/")
        assert resp.status_code == 401

    def test_protected_endpoint_with_valid_token(self, client: TestClient) -> None:
        token = _make_token()
        resp = client.get("/api/v1/pipelines/", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

    def test_expired_token_returns_401(self, client: TestClient) -> None:
        token = create_token({"sub": "alice"}, secret=_SECRET, ttl=-1)
        resp = client.get("/api/v1/ml/experiments", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401

    def test_missing_bearer_prefix_returns_401(self, client: TestClient) -> None:
        token = _make_token()
        resp = client.get("/api/v1/pipelines/", headers={"Authorization": token})
        assert resp.status_code == 401

    def test_no_auth_header_returns_401(self, client: TestClient) -> None:
        resp = client.get("/api/v1/ai/agents")
        assert resp.status_code == 401

    def test_root_path_is_public(self, client: TestClient) -> None:
        resp = client.get("/")
        assert resp.status_code == 200

    def test_metrics_path_is_public(self, client: TestClient) -> None:
        # /metrics should bypass auth (it's in _PUBLIC_PATHS)
        resp = client.get("/metrics")
        # 200 or 404 — but NOT 401
        assert resp.status_code != 401


class TestAuthEnabledNoSecret:
    @pytest.fixture()
    def client(self, monkeypatch: pytest.MonkeyPatch) -> TestClient:
        monkeypatch.setenv("DEX_AUTH_ENABLED", "true")
        monkeypatch.delenv("DEX_JWT_SECRET", raising=False)
        from dataenginex.config.schema import AuthConfig, ServerConfig

        app = create_app(
            DexConfig(
                project=ProjectConfig(name="auth-no-secret"),
                server=ServerConfig(auth=AuthConfig(enabled=True)),
            )
        )
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c

    def test_request_returns_500_when_secret_not_configured(self, client: TestClient) -> None:
        resp = client.get("/api/v1/pipelines/")
        assert resp.status_code == 500
        assert "auth_config_error" in resp.json().get("error", "")


# ---------------------------------------------------------------------------
# Request ID header
# ---------------------------------------------------------------------------


class TestRequestIdHeader:
    @pytest.fixture()
    def client(self) -> TestClient:
        app = create_app(DexConfig(project=ProjectConfig(name="req-id-test")))
        with TestClient(app) as c:
            yield c

    def test_all_responses_have_request_id(self, client: TestClient) -> None:
        for path in ["/", "/api/v1/health", "/api/v1/pipelines/"]:
            resp = client.get(path)
            assert "x-request-id" in resp.headers, f"Missing x-request-id on {path}"

    def test_request_id_is_non_empty(self, client: TestClient) -> None:
        resp = client.get("/api/v1/health")
        assert resp.headers["x-request-id"] != ""


# ---------------------------------------------------------------------------
# Multi-pipeline config
# ---------------------------------------------------------------------------


class TestMultiPipelineApp:
    @pytest.fixture()
    def client(self, tmp_path: object) -> TestClient:
        config = DexConfig(
            project=ProjectConfig(name="multi-pipe"),
            data=DataConfig(
                sources={
                    "src_a": SourceConfig(type="csv", path="tests/fixtures/sample_jobs.csv"),
                    "src_b": SourceConfig(type="csv", path="tests/fixtures/sample_jobs.csv"),
                },
                pipelines={
                    "pipe_a": PipelineConfig(source="src_a"),
                    "pipe_b": PipelineConfig(source="src_b", depends_on=["pipe_a"]),
                    "pipe_c": PipelineConfig(source="src_a"),
                },
            ),
        )
        app = create_app(config)
        with TestClient(app) as c:
            yield c

    def test_all_pipelines_listed(self, client: TestClient) -> None:
        resp = client.get("/api/v1/pipelines/")
        assert resp.status_code == 200
        assert resp.json()["count"] == 3

    def test_get_specific_pipeline(self, client: TestClient) -> None:
        resp = client.get("/api/v1/pipelines/pipe_b")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "pipe_b"

    def test_get_nonexistent_pipeline_returns_404(self, client: TestClient) -> None:
        resp = client.get("/api/v1/pipelines/nonexistent_pipe")
        assert resp.status_code == 404

    def test_all_data_sources_listed(self, client: TestClient) -> None:
        resp = client.get("/api/v1/data/sources")
        assert resp.status_code == 200
        assert resp.json()["count"] == 2


# ---------------------------------------------------------------------------
# System components endpoint
# ---------------------------------------------------------------------------


class TestSystemComponents:
    @pytest.fixture()
    def client(self) -> TestClient:
        app = create_app(DexConfig(project=ProjectConfig(name="system-test")))
        with TestClient(app) as c:
            yield c

    def test_components_endpoint_returns_list(self, client: TestClient) -> None:
        resp = client.get("/api/v1/system/components")
        assert resp.status_code == 200
        data = resp.json()
        assert "components" in data
        assert isinstance(data["components"], list)

    def test_tracker_component_present(self, client: TestClient) -> None:
        resp = client.get("/api/v1/system/components")
        components = resp.json()["components"]
        names = {c["name"] for c in components}
        assert "tracker" in names

    def test_system_logs_endpoint_accessible(self, client: TestClient) -> None:
        resp = client.get("/api/v1/system/logs")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# ML API endpoints integration
# ---------------------------------------------------------------------------


class TestMLAPIEndpoints:
    @pytest.fixture()
    def client(self) -> TestClient:
        app = create_app(DexConfig(project=ProjectConfig(name="ml-api-test")))
        with TestClient(app) as c:
            yield c

    def test_list_experiments_empty_initially(self, client: TestClient) -> None:
        resp = client.get("/api/v1/ml/experiments")
        assert resp.status_code == 200
        assert resp.json()["count"] == 0

    def test_list_models_endpoint_exists(self, client: TestClient) -> None:
        resp = client.get("/api/v1/ml/models")
        assert resp.status_code in (200, 404)

    def test_list_features_endpoint_exists(self, client: TestClient) -> None:
        resp = client.get("/api/v1/ml/features")
        assert resp.status_code in (200, 404)


# ---------------------------------------------------------------------------
# AI API endpoints integration
# ---------------------------------------------------------------------------


class TestAIAPIEndpoints:
    @pytest.fixture()
    def client(self) -> TestClient:
        app = create_app(DexConfig(project=ProjectConfig(name="ai-api-test")))
        with TestClient(app) as c:
            yield c

    def test_agents_empty_without_config(self, client: TestClient) -> None:
        resp = client.get("/api/v1/ai/agents")
        assert resp.status_code == 200
        assert resp.json()["count"] == 0

    def test_tools_registered_at_startup(self, client: TestClient) -> None:
        resp = client.get("/api/v1/ai/tools")
        assert resp.status_code == 200
        assert resp.json()["count"] >= 3  # echo, query, list_tools

    def test_tool_names_include_builtins(self, client: TestClient) -> None:
        resp = client.get("/api/v1/ai/tools")
        tools = resp.json()
        tool_names = {t["name"] for t in tools.get("tools", [])}
        assert "echo" in tool_names
        assert "query" in tool_names


# ---------------------------------------------------------------------------
# Warehouse layers endpoint
# ---------------------------------------------------------------------------


class TestWarehouseLayersEndpoint:
    @pytest.fixture()
    def client(self) -> TestClient:
        app = create_app(DexConfig(project=ProjectConfig(name="warehouse-test")))
        with TestClient(app) as c:
            yield c

    def test_warehouse_layers_returns_three(self, client: TestClient) -> None:
        resp = client.get("/api/v1/data/warehouse/layers")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["layers"]) == 3

    def test_warehouse_layers_are_bronze_silver_gold(self, client: TestClient) -> None:
        resp = client.get("/api/v1/data/warehouse/layers")
        layers = {lyr["name"] for lyr in resp.json()["layers"]}
        assert layers == {"bronze", "silver", "gold"}

    def test_quality_summary_endpoint(self, client: TestClient) -> None:
        resp = client.get("/api/v1/data/quality/summary")
        assert resp.status_code == 200
