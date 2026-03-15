"""Tests for OpenTelemetry tracing."""

import os
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from dataenginex.middleware.tracing import (
    configure_tracing,
    get_tracer,
    instrument_fastapi,
)


def test_configure_tracing() -> None:
    """Test tracing configuration."""
    provider = configure_tracing(
        service_name="test-service",
        service_version="1.0.0",
        enable_console_export=False,
    )

    assert provider is not None
    # TracerProvider can only be set once globally, verify it was created
    assert hasattr(provider, "add_span_processor")


def test_configure_tracing_with_otlp() -> None:
    """Test tracing configuration with OTLP endpoint."""
    provider = configure_tracing(
        service_name="test-service",
        otlp_endpoint="http://localhost:4317",
        enable_console_export=False,
    )

    assert provider is not None


def test_get_tracer() -> None:
    """Test getting a tracer instance."""
    configure_tracing()
    tracer = get_tracer(__name__)

    assert tracer is not None
    assert hasattr(tracer, "start_span")


def test_instrument_fastapi() -> None:
    """Test FastAPI instrumentation."""
    app = FastAPI()

    @app.get("/test")
    def test_endpoint() -> dict[str, str]:
        return {"message": "test"}

    # Instrument the app
    instrument_fastapi(app)

    # Create client and make request
    client = TestClient(app)
    response = client.get("/test")

    assert response.status_code == 200
    # If instrumentation worked, spans would be created
    # (we can't easily test span creation without a real exporter)


def test_tracing_with_environment_variables() -> None:
    """Test tracing respects environment variables."""
    with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
        provider = configure_tracing(service_name="test-service")

        # Check that the resource has the environment set
        resource = provider.resource
        assert resource.attributes.get("deployment.environment") == "production"


def test_tracer_creates_spans() -> None:
    """Test that tracer can create spans."""
    configure_tracing(enable_console_export=False)
    tracer = get_tracer(__name__)

    with tracer.start_as_current_span("test-span") as span:
        assert span is not None
        assert span.is_recording()
        span.set_attribute("test.attribute", "test-value")

    # Span should be ended after context manager
    assert not span.is_recording()
