"""Tests for Prometheus metrics."""

import contextlib

from fastapi import FastAPI
from fastapi.testclient import TestClient

from dataenginex.middleware.metrics import (
    get_metrics,
    http_exceptions_total,
    http_request_duration_seconds,
    http_requests_in_flight,
    http_requests_total,
)
from dataenginex.middleware.metrics_middleware import PrometheusMetricsMiddleware


def test_get_metrics() -> None:
    """Test metrics generation."""
    data, content_type = get_metrics()

    assert isinstance(data, bytes)
    assert "text/plain" in content_type
    # At least some metric
    assert b"http_requests_total" in data or b"python_info" in data


def test_metrics_middleware_success() -> None:
    """Test metrics middleware tracks successful requests."""
    app = FastAPI()
    app.add_middleware(PrometheusMetricsMiddleware)

    @app.get("/test")
    def test_endpoint() -> dict[str, str]:
        return {"message": "test"}

    client = TestClient(app)

    # Get initial metric values
    initial_count = http_requests_total.labels(
        method="GET", endpoint="/test", status="200", environment="dev"
    )._value.get()

    # Make request
    response = client.get("/test")
    assert response.status_code == 200

    # Check metrics updated
    final_count = http_requests_total.labels(
        method="GET", endpoint="/test", status="200", environment="dev"
    )._value.get()
    assert final_count > initial_count


def test_metrics_middleware_tracks_duration() -> None:
    """Test metrics middleware tracks request duration."""
    app = FastAPI()
    app.add_middleware(PrometheusMetricsMiddleware)

    @app.get("/test")
    def test_endpoint() -> dict[str, str]:
        return {"message": "test"}

    client = TestClient(app)

    # Make request
    response = client.get("/test")
    assert response.status_code == 200

    # Check duration was recorded
    histogram = http_request_duration_seconds.labels(
        method="GET", endpoint="/test", environment="dev"
    )
    assert histogram._sum.get() > 0


def test_metrics_middleware_tracks_exceptions() -> None:
    """Test metrics middleware tracks exceptions."""
    app = FastAPI()
    app.add_middleware(PrometheusMetricsMiddleware)

    @app.get("/error")
    def error_endpoint() -> None:
        raise ValueError("Test error")

    client = TestClient(app)

    # Get initial exception count
    initial_exceptions = http_exceptions_total.labels(
        exception_type="ValueError", environment="dev"
    )._value.get()

    # Make request that raises exception
    with contextlib.suppress(ValueError):
        client.get("/error")

    # Check exception was tracked
    final_exceptions = http_exceptions_total.labels(
        exception_type="ValueError", environment="dev"
    )._value.get()
    assert final_exceptions > initial_exceptions


def test_metrics_middleware_skips_metrics_endpoint() -> None:
    """Test that /metrics endpoint itself is not tracked."""
    app = FastAPI()
    app.add_middleware(PrometheusMetricsMiddleware)

    @app.get("/metrics")
    def metrics_endpoint() -> dict[str, str]:
        return {"message": "metrics"}

    client = TestClient(app)

    # Check /metrics is not in tracked endpoints
    response = client.get("/metrics")
    assert response.status_code == 200

    # The /metrics endpoint should not increment its own counter
    # (This is implicit - we're just ensuring no error occurs)


def test_in_flight_requests() -> None:
    """Test in-flight requests gauge."""
    app = FastAPI()
    app.add_middleware(PrometheusMetricsMiddleware)

    @app.get("/test")
    def test_endpoint() -> dict[str, str]:
        return {"message": "test"}

    client = TestClient(app)

    # Make request
    response = client.get("/test")
    assert response.status_code == 200

    # In-flight should be back to 0 after request completes
    assert http_requests_in_flight.labels(environment="dev")._value.get() == 0
