from __future__ import annotations

import os
from collections.abc import AsyncIterator, Mapping, Sequence
from contextlib import asynccontextmanager
from typing import Any

import structlog
import uvicorn
import yaml
from dataenginex.api.auth import AuthMiddleware
from dataenginex.api.errors import APIHTTPException, ServiceUnavailableError
from dataenginex.api.health import HealthChecker, HealthStatus
from dataenginex.api.rate_limit import RateLimitMiddleware
from dataenginex.core.schemas import (
    ComponentStatus,
    EchoRequest,
    EchoResponse,
    ErrorDetail,
    ErrorResponse,
    HealthResponse,
    ReadinessResponse,
    RootResponse,
    StartupResponse,
)
from dataenginex.middleware.logging_config import APP_VERSION, configure_logging
from dataenginex.middleware.metrics import get_metrics
from dataenginex.middleware.metrics_middleware import PrometheusMetricsMiddleware
from dataenginex.middleware.request_logging import RequestLoggingMiddleware
from dataenginex.middleware.tracing import configure_tracing, instrument_fastapi
from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse, PlainTextResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from careerdex.api.routers.ml import ml_router
from careerdex.api.routers.v1 import v1_router
from careerdex.phases.phase5_api_services import careerdex_router

log_level = os.getenv("LOG_LEVEL", "INFO")
json_logs = os.getenv("LOG_FORMAT", "json") == "json"
configure_logging(log_level=log_level, json_logs=json_logs)

logger = structlog.get_logger(__name__)

otlp_endpoint = os.getenv("OTLP_ENDPOINT")
enable_console_traces = os.getenv("ENABLE_CONSOLE_TRACES", "false").lower() == "true"
configure_tracing(otlp_endpoint=otlp_endpoint, enable_console_export=enable_console_traces)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    from dataenginex.ml.registry import ModelRegistry
    from dataenginex.ml.serving import ModelServer

    from careerdex.api.routers.ml import set_model_server

    app.state.startup_complete = False
    logger.info("application_started", environment=os.getenv("ENVIRONMENT", "dev"))

    # Initialize ML model server and registry
    model_registry = ModelRegistry()
    model_server = ModelServer(registry=model_registry)
    set_model_server(model_server, model_registry)

    app.state.startup_complete = True
    yield
    app.state.startup_complete = False
    logger.info("application_shutdown")


app = FastAPI(
    title="CareerDEX",
    version=APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

instrument_fastapi(app)

app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(PrometheusMetricsMiddleware)
app.add_middleware(AuthMiddleware)
app.add_middleware(RateLimitMiddleware)

app.include_router(v1_router)
app.include_router(ml_router)
app.include_router(careerdex_router)

health_checker = HealthChecker()


def custom_openapi() -> dict[str, object]:
    if app.openapi_schema:
        return app.openapi_schema

    schema = get_openapi(
        title="CareerDEX",
        version=APP_VERSION,
        description=(
            "CareerDEX API documentation.\n\n"
            "Authentication: This API supports bearer token authentication. "
            "Provide an Authorization header using the format `Bearer <token>` "
            "when auth is enabled."
        ),
        routes=app.routes,
    )

    schema.setdefault("components", {})
    schema["components"].setdefault("securitySchemes", {})
    schema["components"]["securitySchemes"]["BearerAuth"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
        "description": "Optional bearer token authentication.",
    }

    schema["tags"] = [
        {"name": "core", "description": "Core service endpoints."},
        {"name": "health", "description": "Health and readiness probes."},
        {"name": "v1", "description": "Versioned data and warehouse API."},
        {"name": "ml", "description": "ML model serving and registry."},
        {"name": "docs", "description": "OpenAPI export utilities."},
        {"name": "observability", "description": "Metrics and telemetry."},
    ]

    app.openapi_schema = schema
    return app.openapi_schema


app.openapi = custom_openapi  # type: ignore[method-assign]


def _request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def _format_validation_errors(
    errors: Sequence[Mapping[str, Any]],
) -> list[ErrorDetail]:
    details: list[ErrorDetail] = []
    for error in errors:
        loc = error.get("loc", [])
        if isinstance(loc, (list, tuple)):
            field = ".".join(str(item) for item in loc if item != "body")
        else:
            field = str(loc)
        details.append(
            ErrorDetail(
                field=field or None,
                message=str(error.get("msg", "Invalid value")),
                type=str(error.get("type", "validation_error")),
            )
        )
    return details


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    details = _format_validation_errors(exc.errors())
    payload = ErrorResponse(
        error="validation_error",
        message="Request validation failed",
        request_id=_request_id(request),
        details=details,
    )
    return JSONResponse(status_code=422, content=payload.model_dump())


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    code = "http_error"
    details = None
    if isinstance(exc, APIHTTPException):
        code = exc.code
        details = exc.details
    payload = ErrorResponse(
        error=code,
        message=str(exc.detail),
        request_id=_request_id(request),
        details=details,
    )
    return JSONResponse(status_code=exc.status_code, content=payload.model_dump())


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("unhandled_exception", error=str(exc), error_type=type(exc).__name__)
    payload = ErrorResponse(
        error="internal_server_error",
        message="Unexpected error occurred",
        request_id=_request_id(request),
    )
    return JSONResponse(status_code=500, content=payload.model_dump())


@app.exception_handler(NotImplementedError)
async def not_implemented_handler(request: Request, exc: NotImplementedError) -> JSONResponse:
    logger.warning("not_implemented", error=str(exc), path=str(request.url.path))
    payload = ErrorResponse(
        error="not_implemented",
        message=str(exc) or "This feature is not implemented yet",
        request_id=_request_id(request),
    )
    return JSONResponse(status_code=501, content=payload.model_dump())


@app.get("/metrics", tags=["observability"])
async def metrics() -> Response:
    data, content_type = get_metrics()
    return Response(content=data, media_type=content_type)


@app.get("/", response_model=RootResponse, tags=["core"])
def read_root() -> RootResponse:
    logger.debug("root_endpoint_called")
    return RootResponse(message="CareerDEX API", version=APP_VERSION)


@app.get("/health", response_model=HealthResponse, tags=["health"])
def health_check() -> HealthResponse:
    logger.debug("health check")
    return HealthResponse(status="alive")


@app.get("/ready", response_model=ReadinessResponse, tags=["health"])
async def readiness_check() -> ReadinessResponse:
    logger.debug("readiness_check_called")
    components = await health_checker.check_all()
    overall = health_checker.overall_status(components)
    status = "ready" if overall != HealthStatus.UNHEALTHY else "not_ready"
    if overall == HealthStatus.UNHEALTHY:
        raise ServiceUnavailableError(message="Dependencies are unhealthy")
    return ReadinessResponse(
        status=status,
        components=[
            ComponentStatus.model_validate(component.to_dict()) for component in components
        ],
    )


@app.get("/startup", response_model=StartupResponse, tags=["health"])
def startup_check() -> StartupResponse:
    ready = bool(getattr(app.state, "startup_complete", False))
    return StartupResponse(status="started" if ready else "starting")


@app.post("/echo", response_model=EchoResponse, tags=["core"])
def echo_payload(payload: EchoRequest) -> EchoResponse:
    return EchoResponse(
        message=payload.message,
        count=payload.count,
        echo=[payload.message for _ in range(payload.count)],
    )


@app.get("/openapi.yaml", tags=["docs"], response_class=PlainTextResponse)
def openapi_yaml() -> PlainTextResponse:
    schema = app.openapi()
    return PlainTextResponse(yaml.safe_dump(schema, sort_keys=False))


if __name__ == "__main__":
    host = os.getenv("CAREERDEX_HOST", "0.0.0.0")
    port = int(os.getenv("CAREERDEX_PORT", "8000"))
    uvicorn.run(app, host=host, port=port)
