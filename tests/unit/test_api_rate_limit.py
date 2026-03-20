"""Tests for token-bucket rate limiting."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from dataenginex.api.rate_limit import RateLimiter, RateLimitMiddleware


class TestRateLimiter:
    def test_allows_first_request(self) -> None:
        limiter = RateLimiter(requests_per_minute=60, burst=10)
        assert limiter.allow("client1") is True

    def test_exhausts_burst(self) -> None:
        limiter = RateLimiter(requests_per_minute=60, burst=3)
        results = [limiter.allow("c") for _ in range(5)]
        # First 3 (burst) should pass, then fail
        assert results[:3] == [True, True, True]
        assert results[3] is False

    def test_get_stats(self) -> None:
        limiter = RateLimiter(requests_per_minute=30, burst=5)
        limiter.allow("c1")
        limiter.allow("c2")
        stats = limiter.get_stats()
        assert stats["rpm"] == 30
        assert stats["burst"] == 5
        assert stats["active_clients"] == 2

    def test_cleanup_removes_stale_buckets(self) -> None:
        limiter = RateLimiter()
        limiter.allow("c1")
        # Force last_refill to be very old
        limiter._buckets["c1"].last_refill -= 400
        removed = limiter.cleanup(max_age_seconds=300)
        assert removed == 1
        assert "c1" not in limiter._buckets

    def test_cleanup_keeps_fresh_buckets(self) -> None:
        limiter = RateLimiter()
        limiter.allow("fresh")
        removed = limiter.cleanup(max_age_seconds=300)
        assert removed == 0


class TestRateLimitMiddleware:
    def _app(self) -> FastAPI:
        app = FastAPI()
        app.add_middleware(RateLimitMiddleware)

        @app.get("/api/data")
        def data() -> dict[str, str]:
            return {"data": "ok"}

        @app.get("/health")
        def health() -> dict[str, str]:
            return {"status": "ok"}

        return app

    def test_disabled_passes_all(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DEX_RATE_LIMIT_ENABLED", "false")
        client = TestClient(self._app())
        assert client.get("/api/data").status_code == 200

    def test_exempt_path_always_passes(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DEX_RATE_LIMIT_ENABLED", "true")
        monkeypatch.setenv("DEX_RATE_LIMIT_RPM", "1")
        monkeypatch.setenv("DEX_RATE_LIMIT_BURST", "1")
        client = TestClient(self._app())
        for _ in range(5):
            assert client.get("/health").status_code == 200

    def test_rate_limit_returns_429(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DEX_RATE_LIMIT_ENABLED", "true")
        monkeypatch.setenv("DEX_RATE_LIMIT_RPM", "60")
        monkeypatch.setenv("DEX_RATE_LIMIT_BURST", "2")
        client = TestClient(self._app())
        # First two requests should pass (burst=2)
        assert client.get("/api/data").status_code == 200
        assert client.get("/api/data").status_code == 200
        # Third should be throttled
        assert client.get("/api/data").status_code == 429
