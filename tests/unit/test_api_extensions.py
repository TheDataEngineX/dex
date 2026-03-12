"""Tests for dataenginex.api — auth, rate limiting, pagination, v1 router."""

from __future__ import annotations

import os
from typing import Any
from unittest.mock import patch

import pytest
from dataenginex.api.auth import create_token, decode_token
from dataenginex.api.pagination import (
    decode_cursor,
    encode_cursor,
    paginate,
)
from dataenginex.api.rate_limit import RateLimiter
from httpx import ASGITransport, AsyncClient

from careerdex.api.main import app

# ============================================================================
# JWT Auth
# ============================================================================


class TestJWTAuth:
    SECRET = "test-secret-key-for-unit-tests"

    def test_create_and_decode(self) -> None:
        token = create_token({"sub": "user1", "roles": ["admin"]}, self.SECRET)
        claims = decode_token(token, self.SECRET)
        assert claims["sub"] == "user1"
        assert "admin" in claims["roles"]

    def test_expired_token(self) -> None:
        token = create_token({"sub": "user1"}, self.SECRET, ttl=-1)
        with pytest.raises(ValueError, match="expired"):
            decode_token(token, self.SECRET)

    def test_invalid_signature(self) -> None:
        token = create_token({"sub": "user1"}, self.SECRET)
        with pytest.raises(ValueError, match="signature"):
            decode_token(token, "wrong-secret")

    def test_malformed_token(self) -> None:
        with pytest.raises(ValueError, match="Malformed"):
            decode_token("not.a.valid.jwt.token", self.SECRET)


class TestAuthMiddleware:
    """Integration tests for the auth middleware via the app."""

    @pytest.fixture()
    def _enable_auth(self) -> Any:
        with patch.dict(os.environ, {"DEX_AUTH_ENABLED": "true", "DEX_JWT_SECRET": "s3cret"}):
            yield

    async def test_public_paths_no_auth(self, _enable_auth: Any) -> None:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/health")
            assert resp.status_code == 200

    async def test_protected_path_requires_token(self, _enable_auth: Any) -> None:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/echo", params={"message": "hi"})
            assert resp.status_code == 401

    async def test_protected_path_with_valid_token(self, _enable_auth: Any) -> None:
        token = create_token({"sub": "testuser"}, "s3cret")
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/echo",
                json={"message": "hello"},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 200


# ============================================================================
# Rate Limiting
# ============================================================================


class TestRateLimiter:
    def test_allows_within_burst(self) -> None:
        limiter = RateLimiter(requests_per_minute=60, burst=5)
        for _ in range(5):
            assert limiter.allow("client1") is True

    def test_rejects_over_burst(self) -> None:
        limiter = RateLimiter(requests_per_minute=60, burst=2)
        assert limiter.allow("c") is True
        assert limiter.allow("c") is True
        assert limiter.allow("c") is False

    def test_separate_clients(self) -> None:
        limiter = RateLimiter(requests_per_minute=60, burst=1)
        assert limiter.allow("a") is True
        assert limiter.allow("b") is True

    def test_cleanup(self) -> None:
        limiter = RateLimiter(requests_per_minute=60, burst=5)
        limiter.allow("x")
        evicted = limiter.cleanup(max_age_seconds=0.0)
        assert evicted == 1

    def test_stats(self) -> None:
        limiter = RateLimiter(requests_per_minute=120, burst=10)
        limiter.allow("a")
        stats = limiter.get_stats()
        assert stats["rpm"] == 120
        assert stats["active_clients"] == 1


# ============================================================================
# Pagination
# ============================================================================


class TestPagination:
    def test_encode_decode_cursor(self) -> None:
        cursor = encode_cursor(42)
        assert decode_cursor(cursor) == 42

    def test_decode_invalid_cursor(self) -> None:
        with pytest.raises(ValueError, match="Invalid pagination cursor"):
            decode_cursor("garbage")

    def test_first_page(self) -> None:
        items = list(range(50))
        result = paginate(items, limit=10)
        assert len(result.data) == 10
        assert result.pagination.has_next is True
        assert result.pagination.has_previous is False
        assert result.pagination.total == 50

    def test_second_page(self) -> None:
        items = list(range(50))
        page1 = paginate(items, limit=10)
        assert page1.pagination.next_cursor is not None
        page2 = paginate(items, cursor=page1.pagination.next_cursor, limit=10)
        assert page2.data[0] == 10
        assert page2.pagination.has_previous is True

    def test_last_page(self) -> None:
        items = list(range(5))
        result = paginate(items, limit=10)
        assert result.pagination.has_next is False
        assert result.pagination.next_cursor is None

    def test_max_limit_enforced(self) -> None:
        items = list(range(200))
        result = paginate(items, limit=999, max_limit=50)
        assert len(result.data) == 50


# ============================================================================
# V1 Router
# ============================================================================


class TestV1Router:
    async def test_data_sources(self) -> None:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/careerdex/data/sources")
            assert resp.status_code == 200
            body = resp.json()
            assert "sources" in body
            assert len(body["sources"]) == 4

    async def test_data_quality(self) -> None:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/data/quality")
            assert resp.status_code == 200
            body = resp.json()
            assert "overall_score" in body
            assert "dimensions" in body
            assert "layer_scores" in body

    async def test_data_quality_layer(self) -> None:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/data/quality/bronze")
            assert resp.status_code == 200
            body = resp.json()
            assert body["layer"] == "bronze"
            assert "latest" in body
            assert "history" in body

    async def test_warehouse_layers(self) -> None:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/warehouse/layers")
            assert resp.status_code == 200
            body = resp.json()
            assert len(body["layers"]) == 3

    async def test_system_config(self) -> None:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/careerdex/system/config")
            assert resp.status_code == 200
            body = resp.json()
            assert "schedule" in body
            assert "expected_jobs_per_cycle" in body
            assert "sources" in body
