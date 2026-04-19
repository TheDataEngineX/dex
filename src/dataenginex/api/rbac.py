"""RBAC dependency helpers for DEX API — per ADR-005.

Baseline roles: ``viewer``, ``editor``, ``admin``, ``owner``. Routes declare
required role via ``Depends(require_role(Role.ADMIN))``. Hierarchical:
``owner`` > ``admin`` > ``editor`` > ``viewer``.

Enforcement mode is controlled by ``DEX_RBAC_ENFORCE``:
    ``off``      — skip entirely (default during rollout)
    ``warn``     — log violation, allow request
    ``enforce``  — reject with 403
"""

from __future__ import annotations

import os
from collections.abc import Callable
from enum import IntEnum

import structlog
from fastapi import Request

from dataenginex.api.auth import AuthUser
from dataenginex.api.errors import APIHTTPException

logger = structlog.get_logger()

__all__ = ["Role", "has_role", "require_role"]


class Role(IntEnum):
    """Ordered roles. Higher value = more privilege."""

    VIEWER = 10
    EDITOR = 20
    ADMIN = 30
    OWNER = 40

    @classmethod
    def from_str(cls, value: str) -> Role | None:
        try:
            return cls[value.upper()]
        except KeyError:
            return None


def has_role(user: AuthUser | None, required: Role) -> bool:
    """Return ``True`` if ``user`` holds the required role or higher."""
    if user is None:
        return False
    granted = [Role.from_str(r) for r in user.roles]
    highest = max((r for r in granted if r is not None), default=None)
    return highest is not None and highest >= required


def _mode() -> str:
    return os.getenv("DEX_RBAC_ENFORCE", "off").lower()


def require_role(required: Role) -> Callable[[Request], AuthUser | None]:
    """FastAPI dependency factory — enforce a minimum role on a route."""

    def _dep(request: Request) -> AuthUser | None:
        user: AuthUser | None = getattr(request.state, "auth_user", None)
        mode = _mode()

        if mode == "off":
            return user

        if has_role(user, required):
            return user

        logger.warning(
            "rbac.denied",
            path=request.url.path,
            method=request.method,
            required=required.name,
            user_sub=user.sub if user else None,
            user_roles=user.roles if user else [],
            mode=mode,
        )

        if mode == "enforce":
            raise APIHTTPException(
                status_code=403,
                message=f"Role '{required.name.lower()}' or higher required",
                code="forbidden",
            )

        return user

    return _dep
