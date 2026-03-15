"""Pydantic schemas for API requests and responses.

This module contains only **generic framework schemas** used across all
DEX applications.  Domain-specific schemas should live in the application
package (e.g. ``myapp.core.schemas``).
"""

from __future__ import annotations

from pydantic import BaseModel, Field

__all__ = [
    "ComponentStatus",
    "EchoRequest",
    "EchoResponse",
    "ErrorDetail",
    "ErrorResponse",
    "HealthResponse",
    "ReadinessResponse",
    "RootResponse",
    "StartupResponse",
]


class RootResponse(BaseModel):
    """Response body for the root ``/`` endpoint."""

    message: str
    version: str

    model_config = {
        "json_schema_extra": {"examples": [{"message": "DataEngineX API", "version": "0.1.0"}]}
    }


class HealthResponse(BaseModel):
    """Response body for the ``/health`` liveness probe."""

    status: str

    model_config = {"json_schema_extra": {"examples": [{"status": "alive"}]}}


class StartupResponse(BaseModel):
    """Response body for the ``/startup`` probe."""

    status: str

    model_config = {"json_schema_extra": {"examples": [{"status": "started"}]}}


class ComponentStatus(BaseModel):
    """Health status of a single dependency component."""

    name: str
    status: str
    message: str | None = None
    duration_ms: float | None = None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "name": "database",
                    "status": "healthy",
                    "message": "reachable",
                    "duration_ms": 12.5,
                }
            ]
        }
    }


class ReadinessResponse(BaseModel):
    """Response body for the ``/ready`` readiness probe."""

    status: str
    components: list[ComponentStatus]

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "status": "ready",
                    "components": [
                        {
                            "name": "database",
                            "status": "healthy",
                            "message": "reachable",
                            "duration_ms": 12.5,
                        },
                        {
                            "name": "cache",
                            "status": "skipped",
                            "message": "cache not configured",
                            "duration_ms": None,
                        },
                    ],
                }
            ]
        }
    }


class ErrorDetail(BaseModel):
    """Detail of a single validation or processing error."""

    field: str | None = None
    message: str
    type: str | None = None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "field": "message",
                    "message": "String should have at least 1 character",
                    "type": "string_too_short",
                }
            ]
        }
    }


class ErrorResponse(BaseModel):
    """Standard error response returned by all API error handlers."""

    error: str
    message: str
    request_id: str | None = None
    details: list[ErrorDetail] | None = None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "error": "validation_error",
                    "message": "Request validation failed",
                    "request_id": "1f9b6b1c-5b90-4c6c-8d2a-1f28f6f0b5a1",
                    "details": [
                        {
                            "field": "message",
                            "message": "String should have at least 1 character",
                            "type": "string_too_short",
                        }
                    ],
                }
            ]
        }
    }


class EchoRequest(BaseModel):
    """Request body for the ``/echo`` debug endpoint."""

    message: str = Field(min_length=1)
    count: int = Field(default=1, ge=1, le=10)

    model_config = {"json_schema_extra": {"examples": [{"message": "hello", "count": 2}]}}


class EchoResponse(BaseModel):
    """Response body for the ``/echo`` debug endpoint."""

    message: str
    count: int
    echo: list[str]

    model_config = {
        "json_schema_extra": {
            "examples": [{"message": "hello", "count": 2, "echo": ["hello", "hello"]}]
        }
    }
