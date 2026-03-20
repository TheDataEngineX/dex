"""Tests for JWT authentication utilities and middleware."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from dataenginex.api.auth import AuthMiddleware, AuthUser, create_token, decode_token


class TestTokenHelpers:
    def test_create_and_decode_roundtrip(self) -> None:
        payload = {"sub": "user1", "roles": ["admin"]}
        token = create_token(payload, secret="test-secret")
        claims = decode_token(token, secret="test-secret")
        assert claims["sub"] == "user1"
        assert claims["roles"] == ["admin"]

    def test_token_has_iat_and_exp(self) -> None:
        token = create_token({"sub": "u"}, secret="s", ttl=60)
        claims = decode_token(token, secret="s")
        assert "iat" in claims
        assert "exp" in claims
        assert claims["exp"] > claims["iat"]

    def test_wrong_secret_raises(self) -> None:
        token = create_token({"sub": "u"}, secret="correct")
        with pytest.raises(ValueError, match="Invalid JWT signature"):
            decode_token(token, secret="wrong")

    def test_malformed_token_raises(self) -> None:
        with pytest.raises(ValueError, match="Malformed JWT"):
            decode_token("only.two", secret="s")

    def test_expired_token_raises(self) -> None:
        token = create_token({"sub": "u"}, secret="s", ttl=-1)
        with pytest.raises(ValueError, match="expired"):
            decode_token(token, secret="s")


class TestAuthUser:
    def test_fields(self) -> None:
        user = AuthUser(sub="u1", roles=["reader"], claims={"sub": "u1"})
        assert user.sub == "u1"
        assert user.roles == ["reader"]


class TestAuthMiddleware:
    def _app(self) -> FastAPI:
        app = FastAPI()
        app.add_middleware(AuthMiddleware)

        @app.get("/protected")
        def protected() -> dict[str, str]:
            return {"ok": "yes"}

        @app.get("/health")
        def health() -> dict[str, str]:
            return {"status": "ok"}

        return app

    def test_auth_disabled_passes_all_requests(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DEX_AUTH_ENABLED", "false")
        client = TestClient(self._app())
        assert client.get("/protected").status_code == 200

    def test_public_path_skips_auth(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DEX_AUTH_ENABLED", "true")
        monkeypatch.setenv("DEX_JWT_SECRET", "s")
        client = TestClient(self._app())
        assert client.get("/health").status_code == 200

    def test_missing_secret_returns_500(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DEX_AUTH_ENABLED", "true")
        monkeypatch.delenv("DEX_JWT_SECRET", raising=False)
        client = TestClient(self._app())
        assert client.get("/protected").status_code == 500

    def test_missing_bearer_returns_401(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DEX_AUTH_ENABLED", "true")
        monkeypatch.setenv("DEX_JWT_SECRET", "secret")
        client = TestClient(self._app())
        assert client.get("/protected").status_code == 401

    def test_invalid_token_returns_401(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DEX_AUTH_ENABLED", "true")
        monkeypatch.setenv("DEX_JWT_SECRET", "secret")
        client = TestClient(self._app())
        resp = client.get("/protected", headers={"Authorization": "Bearer bad.token.here"})
        assert resp.status_code == 401

    def test_valid_token_passes(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DEX_AUTH_ENABLED", "true")
        monkeypatch.setenv("DEX_JWT_SECRET", "secret")
        token = create_token({"sub": "u1", "roles": []}, secret="secret")
        client = TestClient(self._app())
        resp = client.get("/protected", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
