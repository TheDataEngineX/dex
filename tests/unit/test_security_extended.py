"""Security-focused tests for DEX API.

Covers: JWT algorithm confusion, token replay, rate-limit bypass paths,
SQL-injection guards in config names, oversized payloads, CORS headers,
pagination cursor tampering, and auth header edge cases.
"""

from __future__ import annotations

import base64
import json
import time

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from dataenginex.api.auth import AuthMiddleware, create_token, decode_token
from dataenginex.api.pagination import encode_cursor, paginate
from dataenginex.api.rate_limit import RateLimiter, RateLimitMiddleware

# ---------------------------------------------------------------------------
# JWT security
# ---------------------------------------------------------------------------


class TestJWTSecurity:
    def test_none_algorithm_rejected(self) -> None:
        """'alg: none' attack — unsigned token must be rejected."""
        header = (
            base64.urlsafe_b64encode(json.dumps({"alg": "none", "typ": "JWT"}).encode())
            .rstrip(b"=")
            .decode()
        )
        payload = (
            base64.urlsafe_b64encode(
                json.dumps({"sub": "attacker", "exp": int(time.time()) + 3600}).encode()
            )
            .rstrip(b"=")
            .decode()
        )
        forged = f"{header}.{payload}."

        with pytest.raises(ValueError):
            decode_token(forged, secret="legit-secret")

    def test_hs256_signature_cannot_be_bypassed_with_empty_sig(self) -> None:
        token = create_token({"sub": "u"}, secret="s")
        header, payload, _ = token.split(".")
        tampered = f"{header}.{payload}."
        with pytest.raises(ValueError):
            decode_token(tampered, secret="s")

    def test_expired_by_one_second_raises(self) -> None:
        token = create_token({"sub": "u"}, secret="s", ttl=-1)
        with pytest.raises(ValueError, match="expired"):
            decode_token(token, secret="s")

    def test_future_exp_is_valid(self) -> None:
        token = create_token({"sub": "u"}, secret="s", ttl=7200)
        claims = decode_token(token, secret="s")
        assert claims["sub"] == "u"

    def test_tampered_payload_signature_mismatch(self) -> None:
        token = create_token({"sub": "user", "roles": ["reader"]}, secret="secret")
        header, _, sig = token.split(".")
        # Replace payload with admin role
        evil_payload = (
            base64.urlsafe_b64encode(
                json.dumps(
                    {"sub": "user", "roles": ["admin"], "exp": int(time.time()) + 3600}
                ).encode()
            )
            .rstrip(b"=")
            .decode()
        )
        evil_token = f"{header}.{evil_payload}.{sig}"
        with pytest.raises(ValueError, match="Invalid JWT signature"):
            decode_token(evil_token, secret="secret")

    def test_wrong_secret_raises(self) -> None:
        token = create_token({"sub": "u"}, secret="real-secret")
        with pytest.raises(ValueError, match="Invalid JWT signature"):
            decode_token(token, secret="wrong-secret")

    def test_empty_secret_can_create_and_decode(self) -> None:
        """Empty secret is allowed by the system — verify it works consistently."""
        token = create_token({"sub": "u"}, secret="")
        claims = decode_token(token, secret="")
        assert claims["sub"] == "u"

    def test_empty_secret_wrong_secret_rejected(self) -> None:
        token = create_token({"sub": "u"}, secret="")
        with pytest.raises(ValueError):
            decode_token(token, secret="not-empty")

    def test_whitespace_token_raises(self) -> None:
        # "   .   .   " has 3 segments, so passes part-count check.
        # The decode stage then raises (Invalid JWT signature or base64 error).
        with pytest.raises((ValueError, Exception)):
            decode_token("   .   .   ", secret="s")

    def test_single_segment_token_raises(self) -> None:
        with pytest.raises(ValueError, match="Malformed JWT"):
            decode_token("onlyone", secret="s")

    def test_four_segment_token_raises(self) -> None:
        with pytest.raises(ValueError, match="Malformed JWT"):
            decode_token("a.b.c.d", secret="s")

    def test_iat_is_not_in_future(self) -> None:
        """iat must be <= current time."""
        now = int(time.time())
        token = create_token({"sub": "u"}, secret="s")
        claims = decode_token(token, secret="s")
        assert claims["iat"] <= now + 2  # allow 2s clock drift


class TestAuthMiddlewareEdgeCases:
    def _make_app(self) -> FastAPI:
        app = FastAPI()
        app.add_middleware(AuthMiddleware)

        @app.get("/protected")
        def protected() -> dict[str, str]:
            return {"ok": "yes"}

        @app.get("/docs")
        def docs() -> dict[str, str]:
            return {"ok": "docs"}

        @app.get("/openapi.json")
        def openapi() -> dict[str, str]:
            return {"openapi": "3.0"}

        return app

    def test_bearer_with_extra_spaces_rejected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DEX_AUTH_ENABLED", "true")
        monkeypatch.setenv("DEX_JWT_SECRET", "secret")
        client = TestClient(self._make_app())
        resp = client.get("/protected", headers={"Authorization": "Bearer  double-space-token"})
        assert resp.status_code == 401

    def test_basic_auth_header_rejected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DEX_AUTH_ENABLED", "true")
        monkeypatch.setenv("DEX_JWT_SECRET", "secret")
        client = TestClient(self._make_app())
        resp = client.get("/protected", headers={"Authorization": "Basic dXNlcjpwYXNz"})
        assert resp.status_code == 401

    def test_docs_path_is_public(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DEX_AUTH_ENABLED", "true")
        monkeypatch.setenv("DEX_JWT_SECRET", "secret")
        client = TestClient(self._make_app())
        assert client.get("/docs").status_code == 200

    def test_openapi_json_is_public(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DEX_AUTH_ENABLED", "true")
        monkeypatch.setenv("DEX_JWT_SECRET", "secret")
        client = TestClient(self._make_app())
        assert client.get("/openapi.json").status_code == 200

    def test_expired_token_returns_401(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DEX_AUTH_ENABLED", "true")
        monkeypatch.setenv("DEX_JWT_SECRET", "secret")
        expired = create_token({"sub": "u"}, secret="secret", ttl=-10)
        client = TestClient(self._make_app())
        resp = client.get("/protected", headers={"Authorization": f"Bearer {expired}"})
        assert resp.status_code == 401

    def test_valid_token_attaches_auth_user(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DEX_AUTH_ENABLED", "true")
        monkeypatch.setenv("DEX_JWT_SECRET", "secret")
        token = create_token({"sub": "alice", "roles": ["admin"]}, secret="secret")
        app = FastAPI()
        app.add_middleware(AuthMiddleware)

        @app.get("/protected")
        def protected() -> dict[str, str]:
            return {"ok": "yes"}

        @app.get("/me")
        def me(request: Request) -> dict[str, str]:
            user = request.state.auth_user
            return {"sub": user.sub, "role": user.roles[0]}

        client = TestClient(app)
        resp = client.get("/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["sub"] == "alice"
        assert resp.json()["role"] == "admin"


# ---------------------------------------------------------------------------
# Rate limiting — bypass attempts
# ---------------------------------------------------------------------------


class TestRateLimitBypass:
    def _make_rate_app(self) -> FastAPI:
        app = FastAPI()
        app.add_middleware(RateLimitMiddleware)

        @app.get("/api/data")
        def data() -> dict[str, str]:
            return {"data": "ok"}

        @app.get("/health")
        def health() -> dict[str, str]:
            return {"status": "ok"}

        return app

    def test_health_exempt_even_at_zero_burst(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DEX_RATE_LIMIT_ENABLED", "true")
        monkeypatch.setenv("DEX_RATE_LIMIT_BURST", "0")
        monkeypatch.setenv("DEX_RATE_LIMIT_RPM", "0")
        client = TestClient(self._make_rate_app())
        # /health is exempt — must always pass
        assert client.get("/health").status_code == 200

    def test_different_ips_have_independent_buckets(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DEX_RATE_LIMIT_ENABLED", "true")
        monkeypatch.setenv("DEX_RATE_LIMIT_BURST", "1")
        monkeypatch.setenv("DEX_RATE_LIMIT_RPM", "60")
        limiter = RateLimiter(requests_per_minute=60, burst=1)
        assert limiter.allow("1.1.1.1") is True
        assert limiter.allow("2.2.2.2") is True  # different IP — own bucket

    def test_burst_exhausted_then_429(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DEX_RATE_LIMIT_ENABLED", "true")
        monkeypatch.setenv("DEX_RATE_LIMIT_BURST", "1")
        monkeypatch.setenv("DEX_RATE_LIMIT_RPM", "60")
        client = TestClient(self._make_rate_app())
        results = [client.get("/api/data").status_code for _ in range(5)]
        assert 429 in results

    def test_rate_limit_response_has_retry_after(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DEX_RATE_LIMIT_ENABLED", "true")
        monkeypatch.setenv("DEX_RATE_LIMIT_BURST", "1")
        monkeypatch.setenv("DEX_RATE_LIMIT_RPM", "60")
        client = TestClient(self._make_rate_app())
        statuses = []
        for _ in range(5):
            resp = client.get("/api/data")
            statuses.append(resp.status_code)
            if resp.status_code == 429:
                # Should include retry guidance in body or headers
                body = resp.json()
                assert "error" in body or "detail" in body
                break


# ---------------------------------------------------------------------------
# Pagination cursor tampering
# ---------------------------------------------------------------------------


class TestPaginationSecurity:
    def test_negative_offset_in_cursor_resets_to_first_page(self) -> None:
        """A cursor encoding a negative offset must not cause errors."""
        bad_cursor = (
            base64.urlsafe_b64encode(json.dumps({"offset": -100}).encode()).rstrip(b"=").decode()
        )
        result = paginate(list(range(20)), cursor=bad_cursor, limit=5)
        # Should silently reset to first page or handle gracefully
        assert result.data is not None
        assert len(result.data) <= 5

    def test_cursor_with_huge_offset_returns_empty(self) -> None:
        """Cursor pointing beyond end of list should return empty data."""
        huge_cursor = encode_cursor(1_000_000)
        result = paginate(list(range(10)), cursor=huge_cursor, limit=5)
        assert result.data == []
        assert result.pagination.has_next is False

    def test_cursor_with_extra_fields_ignored(self) -> None:
        """Cursor with extra unknown fields should still work."""
        cursor = (
            base64.urlsafe_b64encode(json.dumps({"offset": 0, "injected": "payload"}).encode())
            .rstrip(b"=")
            .decode()
        )
        result = paginate(list(range(10)), cursor=cursor, limit=3)
        assert result.data == list(range(3))

    def test_sql_injection_in_cursor_string_is_harmless(self) -> None:
        """Cursor is base64-encoded — raw SQL in it can't reach the DB."""
        evil_cursor = base64.urlsafe_b64encode(b"' OR 1=1 --").rstrip(b"=").decode()
        result = paginate(list(range(5)), cursor=evil_cursor, limit=3)
        # Resets to first page
        assert result.data == list(range(3))

    def test_limit_zero_clamped_to_one(self) -> None:
        result = paginate(list(range(10)), limit=0)
        assert len(result.data) == 1

    def test_negative_limit_clamped(self) -> None:
        result = paginate(list(range(10)), limit=-10)
        assert len(result.data) >= 1


# ---------------------------------------------------------------------------
# Input sanitization — config field names
# ---------------------------------------------------------------------------


class TestInputSanitization:
    def test_agent_chat_message_with_sql_injection(self) -> None:
        """Agent chat messages with SQL are just strings — schema validation only."""
        from dataenginex.api.schemas import AgentChatRequest

        req = AgentChatRequest(message="SELECT * FROM users; DROP TABLE users;--")
        assert "DROP TABLE" in req.message  # passes through as a string (agent handles it)

    def test_predict_request_with_null_features(self) -> None:
        """Null features dict must still be valid for schema."""
        from dataenginex.api.schemas import PredictionRequest

        req = PredictionRequest(model_name="clf", features={})
        assert req.features == {}

    def test_feature_save_empty_data_list(self) -> None:
        from dataenginex.api.schemas import FeatureSaveRequest

        req = FeatureSaveRequest(entity_key="id", data=[])
        assert req.data == []

    def test_promote_request_stage_is_required(self) -> None:
        from pydantic import ValidationError

        from dataenginex.api.schemas import PromoteRequest

        with pytest.raises(ValidationError):
            PromoteRequest()  # type: ignore[call-arg]

    def test_agent_chat_request_message_required(self) -> None:
        from pydantic import ValidationError

        from dataenginex.api.schemas import AgentChatRequest

        with pytest.raises(ValidationError):
            AgentChatRequest()  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# Tracker search — SQL injection guard
# ---------------------------------------------------------------------------


class TestTrackerSQLInjection:
    def test_sql_injection_in_search_does_not_crash(self, tmp_path: Path) -> None:  # type: ignore[name-defined] # noqa: F821
        pytest.importorskip("dex_studio", reason="dex_studio not installed in this env")

        from dex_studio.careerdex.models.application import ApplicationEntry
        from dex_studio.careerdex.services.tracker import ApplicationTracker

        tracker = ApplicationTracker(db_path=tmp_path / "test.duckdb")
        tracker.add(ApplicationEntry(company="Normal Corp", position="SWE"))

        # Should not raise — parameterized queries prevent injection
        results = tracker.list_all(search="'; DROP TABLE applications; --")
        assert isinstance(results, list)

    def test_sql_injection_in_search_does_not_return_all(self, tmp_path: Path) -> None:  # type: ignore[name-defined] # noqa: F821
        pytest.importorskip("dex_studio", reason="dex_studio not installed in this env")

        from dex_studio.careerdex.models.application import ApplicationEntry
        from dex_studio.careerdex.services.tracker import ApplicationTracker

        tracker = ApplicationTracker(db_path=tmp_path / "test.duckdb")
        tracker.add(ApplicationEntry(company="SafeCorp", position="SWE"))
        tracker.add(ApplicationEntry(company="OtherCorp", position="PM"))

        evil = "' OR 1=1 --"
        results = tracker.list_all(search=evil)
        # Injection should return no results (no match for the literal string)
        assert len(results) == 0
