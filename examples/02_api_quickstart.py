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
from dataenginex.api import HealthChecker, HealthStatus
from careerdex.api.routers.v1 import v1_router
from dataenginex.middleware.logging_config import configure_logging
from dataenginex.middleware.metrics import PrometheusMetrics
from fastapi import FastAPI


def create_app() -> FastAPI:
    """Build and configure the DEX FastAPI application."""
    configure_logging(log_level="INFO", json_format=False)

    app = FastAPI(
        title="DataEngineX",
        version="0.5.0",
        description="Example DEX API instance",
    )

    # Mount versioned API router
    app.include_router(v1_router)

    # Health endpoint
    checker = HealthChecker()
    checker.add_check("api", lambda: HealthStatus.HEALTHY)

    @app.get("/")
    def root() -> dict[str, str]:
        return {"service": "dataenginex", "status": "running"}

    @app.get("/health")
    def health() -> dict[str, str]:
        result = checker.check()
        return {
            "status": result.status.value,
            "components": {name: comp.status.value for name, comp in result.components.items()},
        }

    # Prometheus metrics
    metrics = PrometheusMetrics("dex_example")
    metrics.register_default_metrics()

    return app


app = create_app()

if __name__ == "__main__":
    print("Starting DEX API on http://localhost:8000")
    print("Press Ctrl+C to stop\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)
