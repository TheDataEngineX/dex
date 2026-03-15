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
    http://localhost:8000/          → root info
    http://localhost:8000/health    → health check
    http://localhost:8000/api/v1/data/sources   → data sources
    http://localhost:8000/api/v1/data/quality   → quality summary
    http://localhost:8000/api/v1/warehouse/layers → medallion layers
"""

from __future__ import annotations

import uvicorn
from fastapi import FastAPI
from fastapi.responses import Response

from dataenginex.api import HealthChecker
from dataenginex.middleware.logging_config import configure_logging
from dataenginex.middleware.metrics import get_metrics


def create_app() -> FastAPI:
    """Build and configure the DEX FastAPI application."""
    configure_logging(log_level="INFO", json_logs=False)

    app = FastAPI(
        title="DataEngineX",
        version="0.6.0",
        description="Example DEX API instance",
    )

    # Health endpoint
    checker = HealthChecker()

    @app.get("/")
    def root() -> dict[str, str]:
        return {"service": "dataenginex", "status": "running"}

    @app.get("/health")
    async def health() -> dict[str, object]:
        components = await checker.check_all()
        status = checker.overall_status(components)
        return {"status": status.value}

    @app.get("/metrics")
    def metrics() -> Response:
        data, content_type = get_metrics()
        return Response(content=data, media_type=content_type)

    return app


app = create_app()

if __name__ == "__main__":
    print("Starting DEX API on http://localhost:8000")
    print("Press Ctrl+C to stop\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)
