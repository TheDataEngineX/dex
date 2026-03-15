"""Tests for health check utilities."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from dataenginex.api.health import ComponentHealth, HealthChecker, HealthStatus


class TestHealthStatus:
    def test_enum_values(self) -> None:
        assert HealthStatus.HEALTHY == "healthy"
        assert HealthStatus.DEGRADED == "degraded"
        assert HealthStatus.UNHEALTHY == "unhealthy"
        assert HealthStatus.SKIPPED == "skipped"


class TestComponentHealth:
    def test_to_dict(self) -> None:
        ch = ComponentHealth(
            name="db",
            status=HealthStatus.HEALTHY,
            message="ok",
            duration_ms=1.23,
        )
        d = ch.to_dict()
        assert d["name"] == "db"
        assert d["status"] == "healthy"
        assert d["message"] == "ok"
        assert d["duration_ms"] == 1.23

    def test_to_dict_defaults(self) -> None:
        ch = ComponentHealth(name="cache", status=HealthStatus.SKIPPED)
        d = ch.to_dict()
        assert d["message"] is None
        assert d["duration_ms"] is None


class TestHealthChecker:
    @pytest.fixture
    def checker(self) -> HealthChecker:
        return HealthChecker(timeout_seconds=0.5)

    @pytest.mark.asyncio
    async def test_check_database_skipped(self, checker: HealthChecker) -> None:
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("DEX_DB_HOST", None)
            os.environ.pop("DEX_DB_PORT", None)
            result = await checker.check_database()
        assert result.status == HealthStatus.SKIPPED
        assert result.name == "database"

    @pytest.mark.asyncio
    async def test_check_cache_skipped(self, checker: HealthChecker) -> None:
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("DEX_CACHE_HOST", None)
            os.environ.pop("DEX_CACHE_PORT", None)
            result = await checker.check_cache()
        assert result.status == HealthStatus.SKIPPED
        assert result.name == "cache"

    @pytest.mark.asyncio
    async def test_check_external_api_skipped(self, checker: HealthChecker) -> None:
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("DEX_EXTERNAL_API_URL", None)
            result = await checker.check_external_api()
        assert result.status == HealthStatus.SKIPPED
        assert result.name == "external_api"

    @pytest.mark.asyncio
    async def test_check_all_returns_three(self, checker: HealthChecker) -> None:
        with patch.dict(os.environ, {}, clear=True):
            for key in (
                "DEX_DB_HOST",
                "DEX_DB_PORT",
                "DEX_CACHE_HOST",
                "DEX_CACHE_PORT",
                "DEX_EXTERNAL_API_URL",
            ):
                os.environ.pop(key, None)
            components = await checker.check_all()
        assert len(components) == 3

    def test_overall_status_all_healthy(self, checker: HealthChecker) -> None:
        components = [
            ComponentHealth("a", HealthStatus.HEALTHY),
            ComponentHealth("b", HealthStatus.HEALTHY),
        ]
        assert checker.overall_status(components) == HealthStatus.HEALTHY

    def test_overall_status_degraded(self, checker: HealthChecker) -> None:
        components = [
            ComponentHealth("a", HealthStatus.HEALTHY),
            ComponentHealth("b", HealthStatus.DEGRADED),
        ]
        assert checker.overall_status(components) == HealthStatus.DEGRADED

    def test_overall_status_unhealthy(self, checker: HealthChecker) -> None:
        components = [
            ComponentHealth("a", HealthStatus.UNHEALTHY),
            ComponentHealth("b", HealthStatus.HEALTHY),
        ]
        assert checker.overall_status(components) == HealthStatus.UNHEALTHY

    @pytest.mark.asyncio
    async def test_check_database_unreachable(self, checker: HealthChecker) -> None:
        with patch.dict(os.environ, {"DEX_DB_HOST": "127.0.0.1", "DEX_DB_PORT": "59999"}):
            result = await checker.check_database()
        assert result.status == HealthStatus.UNHEALTHY
        assert result.duration_ms is not None

    @pytest.mark.asyncio
    async def test_check_cache_unreachable(self, checker: HealthChecker) -> None:
        with patch.dict(os.environ, {"DEX_CACHE_HOST": "127.0.0.1", "DEX_CACHE_PORT": "59998"}):
            result = await checker.check_cache()
        assert result.status == HealthStatus.UNHEALTHY

    @pytest.mark.asyncio
    async def test_check_external_api_bad_url(self, checker: HealthChecker) -> None:
        with patch.dict(os.environ, {"DEX_EXTERNAL_API_URL": "http://127.0.0.1:59997/nope"}):
            result = await checker.check_external_api()
        assert result.status == HealthStatus.UNHEALTHY
        assert result.duration_ms is not None
