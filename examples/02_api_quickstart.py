#!/usr/bin/env python
"""02_api_quickstart.py — Launch the DEX FastAPI application.

Demonstrates:
- Building the FastAPI app with health checks
- Mounting the v1 API router
- Configuring structured logging and metrics
- Running with uvicorn

Run:
    uv run python examples/02_api_quickstart.py

Then visit:
    http://localhost:17000/          → root info
    http://localhost:17000/health    → health check
    http://localhost:17000/echo      → echo endpoint (POST)
    http://localhost:17000/metrics   → Prometheus metrics
"""

from __future__ import annotations

import structlog
import uvicorn
from fastapi import FastAPI
from fastapi.responses import Response
from pydantic import BaseModel

from dataenginex.api import HealthChecker
from dataenginex.middleware.logging_config import configure_logging
from dataenginex.middleware.metrics import get_metrics

logger = structlog.get_logger()


class EchoRequest(BaseModel):
    """Echo request body."""

    message: str


class EchoResponse(BaseModel):
    """Echo response body."""

    echo: str


def create_app() -> FastAPI:
    """Build and configure the DEX FastAPI application."""
    configure_logging(log_level="INFO", json_logs=False)

    app = FastAPI(
        title="DataEngineX",
        version="0.8.9",
        description="Example DEX API instance",
    )

    checker = HealthChecker()

    @app.get("/")
    def root() -> dict[str, str]:
        return {"service": "dataenginex", "status": "running"}

    @app.get("/health")
    async def health() -> dict[str, object]:
        components = await checker.check_all()
        status = checker.overall_status(components)
        return {"status": status.value}

    @app.post("/echo", response_model=EchoResponse)
    def echo(body: EchoRequest) -> EchoResponse:
        return EchoResponse(echo=body.message)

    @app.get("/metrics")
    def metrics() -> Response:
        data, content_type = get_metrics()
        return Response(content=data, media_type=content_type)

    return app


app = create_app()

if __name__ == "__main__":
    logger.info("starting dex api", host="0.0.0.0", port=17000)
    uvicorn.run(app, host="0.0.0.0", port=17000)
