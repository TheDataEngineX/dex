"""End-to-end API tests using a real Uvicorn server."""

from __future__ import annotations

import socket
import threading
import time
from datetime import UTC, datetime

import httpx
import pytest
import uvicorn
from dataenginex.ml.registry import ModelArtifact, ModelStage

from careerdex.api.main import app


def _get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _run_server(port: int) -> tuple[uvicorn.Server, threading.Thread]:
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)

    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    # Wait for server to start
    deadline = time.time() + 5
    while not server.started and time.time() < deadline:
        time.sleep(0.05)

    if not server.started:
        server.should_exit = True
        thread.join(timeout=2)
        pytest.skip("Uvicorn server failed to start in time")

    return server, thread


def _stop_server(server: uvicorn.Server, thread: threading.Thread) -> None:
    server.should_exit = True
    thread.join(timeout=5)


def test_e2e_root_health_ready() -> None:
    """Spin up Uvicorn and validate core endpoints."""
    port = _get_free_port()
    server, thread = _run_server(port)

    try:
        base_url = f"http://127.0.0.1:{port}"
        with httpx.Client(timeout=5.0) as client:
            root = client.get(f"{base_url}/")
            assert root.status_code == 200
            assert root.json().get("message") == "CareerDEX API"

            health = client.get(f"{base_url}/health")
            assert health.status_code == 200
            assert health.json() == {"status": "alive"}

            ready = client.get(f"{base_url}/ready")
            assert ready.status_code in {200, 503}
            payload = ready.json()
            if ready.status_code == 200:
                assert "status" in payload
            else:
                assert payload["error"] == "service_unavailable"
    finally:
        _stop_server(server, thread)


def test_e2e_ml_endpoints() -> None:
    """Test ML model serving endpoints via real app."""
    from unittest.mock import MagicMock

    port = _get_free_port()
    server, thread = _run_server(port)

    try:
        # Register a test model in the app's model server
        from careerdex.api.routers import ml as ml_module

        registry = ml_module._model_registry
        if registry is not None:
            artifact = ModelArtifact(
                name="test-model",
                version="1.0.0",
                stage=ModelStage.PRODUCTION,
                metrics={"accuracy": 0.95},
                parameters={"n_estimators": 100},
                created_at=datetime.now(UTC),
            )
            registry.register(artifact)

            # Load a mock model
            server_instance = ml_module._model_server
            if server_instance is not None:
                mock_model = MagicMock()
                mock_model.predict.return_value = [0.42]
                server_instance.load_model("test-model", "1.0.0", mock_model)

        base_url = f"http://127.0.0.1:{port}"
        with httpx.Client(timeout=5.0) as client:
            # Test GET /api/v1/models
            models_resp = client.get(f"{base_url}/api/v1/models")
            assert models_resp.status_code == 200
            models_data = models_resp.json()
            assert "models" in models_data
            assert "total" in models_data

            # Test GET /api/v1/models/{name}
            model_resp = client.get(f"{base_url}/api/v1/models/test-model")
            assert model_resp.status_code == 200
            model_data = model_resp.json()
            assert model_data["name"] == "test-model"
            assert model_data["version"] == "1.0.0"
            assert model_data["stage"] == "production"

            # Test POST /api/v1/predict
            predict_resp = client.post(
                f"{base_url}/api/v1/predict",
                json={
                    "model_name": "test-model",
                    "version": "1.0.0",
                    "features": [{"x": 1.0}],
                },
            )
            assert predict_resp.status_code == 200
            pred_data = predict_resp.json()
            assert pred_data["model_name"] == "test-model"
            assert "predictions" in pred_data
            assert "latency_ms" in pred_data

            # Test GET /api/v1/models/{name} with non-existent model
            not_found_resp = client.get(f"{base_url}/api/v1/models/nonexistent")
            assert not_found_resp.status_code == 404
    finally:
        _stop_server(server, thread)
