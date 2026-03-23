"""FastAPI application factory.

Creates a fully configured DEX API from ``DexConfig``.

Usage::

    from dataenginex.api.factory import create_app
    app = create_app(config)
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any, cast

import structlog
from fastapi import FastAPI

from dataenginex.config.schema import DexConfig
from dataenginex.ml.llm import get_llm_provider

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Initialize all backends at startup, tear down on shutdown."""
    config: DexConfig = app.state.config

    # 1. Data backends
    from dataenginex.data.pipeline.runner import PipelineRunner
    from dataenginex.warehouse.lineage import PersistentLineage

    app.state.pipeline_runner = PipelineRunner(config)
    app.state.lineage = PersistentLineage(".dex/lineage.json")

    # 2. ML backends — import builtins first to trigger registry decoration
    import dataenginex.ml.features.builtin  # noqa: F401
    import dataenginex.ml.serving_engine.builtin  # noqa: F401
    import dataenginex.ml.tracking.builtin  # noqa: F401
    from dataenginex.ml.features import feature_store_registry
    from dataenginex.ml.registry import ModelRegistry
    from dataenginex.ml.serving_engine import serving_registry
    from dataenginex.ml.tracking import tracker_registry

    tracker_cls = tracker_registry.get(config.ml.tracking.backend)
    app.state.tracker = tracker_cls()

    fs_cls = feature_store_registry.get(config.ml.features.backend)
    app.state.feature_store = fs_cls(**config.ml.features.options)

    model_registry = ModelRegistry(persist_path=".dex/models/registry.json")
    app.state.model_registry = model_registry

    # Cast to Any: BackendRegistry returns type[BaseServingEngine] but the concrete
    # builtin class accepts kwargs not on the ABC; mypy can't narrow through registry.get()
    serving_cls_any: Any = cast(Any, serving_registry.get(config.ml.serving.engine))
    app.state.serving_engine = serving_cls_any(
        model_registry=model_registry,
        model_dir=".dex/models",
    )

    # 3. AI backends (graceful — server starts even if LLM unavailable)
    from dataenginex.ai.tools.builtin import register_builtin_tools

    register_builtin_tools()

    try:
        app.state.llm = get_llm_provider(
            config.ai.llm.provider,
            model=config.ai.llm.model,
        )
        logger.info("llm provider ready", provider=config.ai.llm.provider)
    except Exception:
        app.state.llm = None
        logger.warning("LLM provider unavailable, agent endpoints degraded")

    # 4. Agents — import builtin to trigger registration
    import dataenginex.ai.agents.builtin  # noqa: F401
    from dataenginex.ai.agents import agent_registry
    from dataenginex.ai.tools import tool_registry

    app.state.agents = {}
    for name, agent_cfg in config.ai.agents.items():
        if app.state.llm is None:
            logger.warning("skipping agent %s — no LLM available", name)
            continue
        agent_llm = app.state.llm
        if agent_cfg.model:
            try:
                agent_llm = get_llm_provider(
                    config.ai.llm.provider,
                    model=agent_cfg.model,
                )
            except Exception:
                logger.warning("agent %s model override failed, using default", name)
        # Cast to Any: BackendRegistry returns type[BaseAgentRuntime] but the concrete
        # builtin class accepts kwargs not on the ABC; mypy can't narrow through registry.get()
        agent_cls_any: Any = cast(Any, agent_registry.get(agent_cfg.runtime))
        app.state.agents[name] = agent_cls_any(
            llm=agent_llm,
            system_prompt=agent_cfg.system_prompt,
            tools=tool_registry,
            max_iterations=agent_cfg.max_iterations,
        )
        logger.info("agent initialized", agent=name, runtime=agent_cfg.runtime)

    logger.info("lifespan startup complete")

    yield  # --- app runs ---

    # Shutdown
    if hasattr(app.state, "feature_store") and hasattr(app.state.feature_store, "close"):
        app.state.feature_store.close()
    logger.info("shutdown complete")


def create_app(config: DexConfig | None = None, **kwargs: Any) -> FastAPI:
    """Build a configured FastAPI application.

    Args:
        config: DexConfig instance. If None, uses minimal defaults.
        **kwargs: Extra FastAPI constructor kwargs.

    Returns:
        A FastAPI application instance.
    """
    from fastapi.middleware.cors import CORSMiddleware

    from dataenginex.api.routers.ai import router as ai_router
    from dataenginex.api.routers.data import router as data_router
    from dataenginex.api.routers.health import router as health_router
    from dataenginex.api.routers.ml import router as ml_router
    from dataenginex.api.routers.pipelines import router as pipelines_router
    from dataenginex.api.routers.root import router as root_router
    from dataenginex.api.routers.system import router as system_router

    if config is None:
        from dataenginex.config.schema import ProjectConfig

        config = DexConfig(project=ProjectConfig(name="dataenginex"))

    app = FastAPI(
        title=config.project.name,
        version=config.project.version,
        description=config.project.description or "DataEngineX API",
        lifespan=lifespan,
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

    # Middleware stack (outermost → innermost):
    # RequestLogging → Metrics → Auth → RateLimit → CORS
    # Added in reverse order because FastAPI wraps last-added as outermost.

    # Rate limiting (innermost of custom middleware)
    import os

    if os.environ.get("DEX_RATE_LIMIT_ENABLED", "").lower() == "true":
        from dataenginex.api.rate_limit import RateLimitMiddleware

        app.add_middleware(RateLimitMiddleware)

    # Auth
    if config.server.auth.enabled:
        from dataenginex.api.auth import AuthMiddleware

        app.add_middleware(AuthMiddleware)

    # Prometheus metrics
    if config.observability.metrics:
        from dataenginex.middleware.metrics_middleware import PrometheusMetricsMiddleware

        app.add_middleware(PrometheusMetricsMiddleware)

    # Request logging (outermost — added last)
    from dataenginex.middleware.request_logging import RequestLoggingMiddleware

    app.add_middleware(RequestLoggingMiddleware)

    # Store config on app state
    app.state.config = config

    # Include routers
    app.include_router(root_router)
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(pipelines_router, prefix="/api/v1")
    app.include_router(data_router, prefix="/api/v1")
    app.include_router(ml_router, prefix="/api/v1")
    app.include_router(ai_router, prefix="/api/v1")
    app.include_router(system_router, prefix="/api/v1")

    logger.info(
        "app created",
        name=config.project.name,
        version=config.project.version,
    )

    return app
