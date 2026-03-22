"""FastAPI application factory.

Creates a fully configured DEX API from ``DexConfig``.

Usage::

    from dataenginex.api.factory import create_app
    app = create_app(config)
"""

from __future__ import annotations

from typing import Any

import structlog

from dataenginex.config.schema import DexConfig

logger = structlog.get_logger()


def create_app(config: DexConfig | None = None, **kwargs: Any) -> Any:
    """Build a configured FastAPI application.

    Args:
        config: DexConfig instance. If None, uses minimal defaults.
        **kwargs: Extra FastAPI constructor kwargs.

    Returns:
        A FastAPI application instance.
    """
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware

    from dataenginex.api.routers.health import router as health_router
    from dataenginex.api.routers.pipelines import router as pipelines_router
    from dataenginex.api.routers.root import router as root_router

    if config is None:
        from dataenginex.config.schema import ProjectConfig

        config = DexConfig(project=ProjectConfig(name="dataenginex"))

    app = FastAPI(
        title=config.project.name,
        version=config.project.version,
        description=config.project.description or "DataEngineX API",
        **kwargs,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.server.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Store config on app state
    app.state.config = config

    # Include routers
    app.include_router(root_router)
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(pipelines_router, prefix="/api/v1")

    logger.info(
        "app created",
        name=config.project.name,
        version=config.project.version,
    )

    return app
