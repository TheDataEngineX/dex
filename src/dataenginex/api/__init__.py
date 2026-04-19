"""Reusable API components — auth, health, errors, pagination, rate limiting.

Public API::

    from dataenginex.api import (
        HealthChecker, HealthStatus, ComponentHealth,
        APIHTTPException, BadRequestError, NotFoundError, ServiceUnavailableError,
        PaginatedResponse, paginate,
        AuthMiddleware, AuthUser, create_token, decode_token,
        RateLimiter, RateLimitMiddleware,
    )

Routers are defined in application packages that build on dataenginex.

Requires the ``[api]`` extra::

    pip install dataenginex[api]
"""

from __future__ import annotations

try:
    from .auth import (
        AuthMiddleware,
        AuthUser,
        create_token,
        decode_token,
        decode_token_auto,
    )
    from .errors import (
        APIHTTPException,
        BadRequestError,
        NotFoundError,
        ServiceUnavailableError,
    )
    from .health import ComponentHealth, HealthChecker, HealthStatus
    from .pagination import PaginatedResponse, PaginationMeta, paginate
    from .rate_limit import RateLimiter, RateLimitMiddleware
    from .rbac import Role, has_role, require_role
except ImportError as _exc:
    _MISSING_MSG = (
        "dataenginex.api requires the [api] extra. Install it with: pip install dataenginex[api]"
    )
    raise ImportError(_MISSING_MSG) from _exc

__all__ = [
    # Auth
    "AuthMiddleware",
    "AuthUser",
    "create_token",
    "decode_token",
    "decode_token_auto",
    # Errors
    "APIHTTPException",
    "BadRequestError",
    "NotFoundError",
    "ServiceUnavailableError",
    # Health
    "ComponentHealth",
    "HealthChecker",
    "HealthStatus",
    # Pagination
    "PaginatedResponse",
    "PaginationMeta",
    "paginate",
    # Rate limiting
    "RateLimiter",
    "RateLimitMiddleware",
    # RBAC
    "Role",
    "has_role",
    "require_role",
]
