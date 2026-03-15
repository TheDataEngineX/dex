"""Custom exception types for API error handling."""

from __future__ import annotations

from fastapi import HTTPException, status

from dataenginex.core.schemas import ErrorDetail

__all__ = [
    "APIHTTPException",
    "BadRequestError",
    "NotFoundError",
    "ServiceUnavailableError",
]


class APIHTTPException(HTTPException):
    """Base HTTP exception with error code and details."""

    def __init__(
        self,
        status_code: int,
        message: str,
        code: str = "api_error",
        details: list[ErrorDetail] | None = None,
    ) -> None:
        self.code = code
        self.details = details
        super().__init__(status_code=status_code, detail=message)


class BadRequestError(APIHTTPException):
    """Raised for 400 validation or malformed requests."""

    def __init__(
        self,
        message: str = "Bad request",
        details: list[ErrorDetail] | None = None,
    ) -> None:
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=message,
            code="bad_request",
            details=details,
        )


class NotFoundError(APIHTTPException):
    """Raised for 404 not found errors."""

    def __init__(
        self,
        message: str = "Resource not found",
        details: list[ErrorDetail] | None = None,
    ) -> None:
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            message=message,
            code="not_found",
            details=details,
        )


class ServiceUnavailableError(APIHTTPException):
    """Raised when a dependency is unavailable."""

    def __init__(
        self,
        message: str = "Service unavailable",
        details: list[ErrorDetail] | None = None,
    ) -> None:
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            message=message,
            code="service_unavailable",
            details=details,
        )
