"""Tests for request logging middleware."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from dataenginex.middleware.request_logging import RequestLoggingMiddleware


@pytest.fixture
def test_app() -> FastAPI:
    """Create a test FastAPI application with middleware."""
    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware)

    @app.get("/test")
    def test_endpoint() -> dict[str, str]:
        return {"message": "test"}

    @app.get("/error")
    def error_endpoint() -> None:
        raise ValueError("Test error")

    return app


@pytest.fixture
def client(test_app: FastAPI) -> TestClient:
    """Create test client."""
    return TestClient(test_app)


def test_request_logging_middleware_success(client: TestClient) -> None:
    """Test middleware logs successful requests."""
    response = client.get("/test")

    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    assert response.json() == {"message": "test"}


def test_request_logging_middleware_request_id(client: TestClient) -> None:
    """Test that request ID is added to response headers."""
    response = client.get("/test")

    request_id = response.headers.get("X-Request-ID")
    assert request_id is not None
    assert len(request_id) > 0


def test_request_logging_middleware_error(client: TestClient) -> None:
    """Test middleware logs errors."""
    with pytest.raises(ValueError, match="Test error"):
        client.get("/error")


def test_request_logging_middleware_query_params(client: TestClient) -> None:
    """Test middleware logs query parameters."""
    response = client.get("/test?param1=value1&param2=value2")

    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
