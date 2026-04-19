"""SCIM 2.0 user provisioning endpoints (RFC 7643/7644).

Minimal surface for enterprise IdP integration (Okta, Azure AD, OneLogin):

- ``GET/POST /scim/v2/Users``
- ``GET/PUT/PATCH/DELETE /scim/v2/Users/{id}``
- ``GET /scim/v2/ServiceProviderConfig``
- ``GET /scim/v2/ResourceTypes``
- ``GET /scim/v2/Schemas``

Storage is pluggable via :class:`SCIMStore`. The default :class:`MemorySCIMStore`
is intended for dev/testing only; production deployments should supply a
persistent store (e.g. DuckDB, Postgres).

Router is mounted by :func:`dataenginex.api.factory.create_app` when
``DEX_SCIM_ENABLED=true``.
"""

from __future__ import annotations

import os
import uuid
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, ConfigDict, Field

from dataenginex.api.rbac import Role, require_role

_RequireAdmin = Depends(require_role(Role.ADMIN))

logger = structlog.get_logger()

__all__ = [
    "MemorySCIMStore",
    "SCIMEmail",
    "SCIMName",
    "SCIMStore",
    "SCIMUser",
    "get_store",
    "reset_store",
    "router",
]


_USER_SCHEMA = "urn:ietf:params:scim:schemas:core:2.0:User"
_LIST_SCHEMA = "urn:ietf:params:scim:api:messages:2.0:ListResponse"
_PATCH_SCHEMA = "urn:ietf:params:scim:api:messages:2.0:PatchOp"
_ERROR_SCHEMA = "urn:ietf:params:scim:api:messages:2.0:Error"


class SCIMName(BaseModel):
    """SCIM name sub-resource."""

    model_config = ConfigDict(extra="allow")
    formatted: str | None = None
    familyName: str | None = None  # noqa: N815 — SCIM spec field name
    givenName: str | None = None  # noqa: N815


class SCIMEmail(BaseModel):
    """SCIM email sub-resource."""

    model_config = ConfigDict(extra="allow")
    value: str
    primary: bool = False
    type: str | None = None


class SCIMUser(BaseModel):
    """SCIM 2.0 Core User resource (RFC 7643 §4.1)."""

    model_config = ConfigDict(extra="allow")

    schemas: list[str] = Field(default_factory=lambda: [_USER_SCHEMA])
    id: str | None = None
    externalId: str | None = None  # noqa: N815
    userName: str  # noqa: N815
    name: SCIMName | None = None
    displayName: str | None = None  # noqa: N815
    emails: list[SCIMEmail] = Field(default_factory=list)
    active: bool = True
    roles: list[str] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)


class SCIMStore(ABC):
    """Abstract SCIM persistence interface."""

    @abstractmethod
    def list_users(
        self,
        start_index: int = 1,
        count: int = 100,
        filter_expr: str | None = None,
    ) -> tuple[list[SCIMUser], int]:
        """Return (users, total_count) for the requested page."""

    @abstractmethod
    def get_user(self, user_id: str) -> SCIMUser | None:
        """Return a user by id or None."""

    @abstractmethod
    def create_user(self, user: SCIMUser) -> SCIMUser:
        """Persist a new user; assigns id/meta; raises ``KeyError`` on duplicate userName."""

    @abstractmethod
    def replace_user(self, user_id: str, user: SCIMUser) -> SCIMUser:
        """Replace the user at ``user_id``."""

    @abstractmethod
    def patch_user(self, user_id: str, operations: list[dict[str, Any]]) -> SCIMUser:
        """Apply a SCIM PatchOp document."""

    @abstractmethod
    def delete_user(self, user_id: str) -> None:
        """Deactivate/remove the user."""


class MemorySCIMStore(SCIMStore):
    """In-memory SCIM store — dev/testing only, not thread-safe."""

    def __init__(self) -> None:
        self._users: dict[str, SCIMUser] = {}

    def list_users(
        self,
        start_index: int = 1,
        count: int = 100,
        filter_expr: str | None = None,
    ) -> tuple[list[SCIMUser], int]:
        users = list(self._users.values())
        if filter_expr:
            users = [u for u in users if self._matches_filter(u, filter_expr)]
        total = len(users)
        start = max(start_index - 1, 0)
        return users[start : start + count], total

    def get_user(self, user_id: str) -> SCIMUser | None:
        return self._users.get(user_id)

    def create_user(self, user: SCIMUser) -> SCIMUser:
        if any(u.userName == user.userName for u in self._users.values()):
            msg = f"userName '{user.userName}' already exists"
            raise KeyError(msg)
        uid = user.id or str(uuid.uuid4())
        now = datetime.now(UTC).isoformat()
        user.id = uid
        user.meta = {
            "resourceType": "User",
            "created": now,
            "lastModified": now,
            "location": f"/scim/v2/Users/{uid}",
        }
        self._users[uid] = user
        return user

    def replace_user(self, user_id: str, user: SCIMUser) -> SCIMUser:
        existing = self._users.get(user_id)
        if existing is None:
            msg = user_id
            raise KeyError(msg)
        user.id = user_id
        created = existing.meta.get("created", datetime.now(UTC).isoformat())
        user.meta = {
            "resourceType": "User",
            "created": created,
            "lastModified": datetime.now(UTC).isoformat(),
            "location": f"/scim/v2/Users/{user_id}",
        }
        self._users[user_id] = user
        return user

    def patch_user(self, user_id: str, operations: list[dict[str, Any]]) -> SCIMUser:
        user = self._users.get(user_id)
        if user is None:
            msg = user_id
            raise KeyError(msg)
        data = user.model_dump()
        for op in operations:
            verb = str(op.get("op", "")).lower()
            path = op.get("path", "")
            value = op.get("value")
            if verb == "replace" and path:
                data[path] = value
            elif verb == "replace" and isinstance(value, dict):
                data.update(value)
            elif verb == "add" and path:
                data[path] = value
            elif verb == "remove" and path:
                data.pop(path, None)
        data["id"] = user_id
        updated = SCIMUser(**data)
        updated.meta = {
            **user.meta,
            "lastModified": datetime.now(UTC).isoformat(),
        }
        self._users[user_id] = updated
        return updated

    def delete_user(self, user_id: str) -> None:
        if user_id not in self._users:
            msg = user_id
            raise KeyError(msg)
        del self._users[user_id]

    @staticmethod
    def _matches_filter(user: SCIMUser, filter_expr: str) -> bool:
        """Minimal SCIM filter — supports ``userName eq "x"`` only."""
        parts = filter_expr.split(maxsplit=2)
        if len(parts) != 3 or parts[1].lower() != "eq":
            return True
        attr, _, raw = parts
        value = raw.strip('"')
        return bool(getattr(user, attr, None) == value)


_STORE: SCIMStore | None = None


def get_store() -> SCIMStore:
    """Return the process-global SCIM store, creating the default lazily."""
    global _STORE  # noqa: PLW0603
    if _STORE is None:
        _STORE = MemorySCIMStore()
    return _STORE


def reset_store(store: SCIMStore | None = None) -> None:
    """Replace the global SCIM store (test hook)."""
    global _STORE  # noqa: PLW0603
    _STORE = store


def _scim_error(detail: str, code: int) -> HTTPException:
    return HTTPException(
        status_code=code,
        detail={"schemas": [_ERROR_SCHEMA], "detail": detail, "status": str(code)},
    )


router = APIRouter(prefix="/scim/v2", tags=["scim"])


@router.get("/ServiceProviderConfig")
def service_provider_config() -> dict[str, Any]:
    """Publish SCIM server capabilities per RFC 7644 §5."""
    return {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:ServiceProviderConfig"],
        "patch": {"supported": True},
        "bulk": {"supported": False, "maxOperations": 0, "maxPayloadSize": 0},
        "filter": {"supported": True, "maxResults": 200},
        "changePassword": {"supported": False},
        "sort": {"supported": False},
        "etag": {"supported": False},
        "authenticationSchemes": [
            {
                "type": "oauthbearertoken",
                "name": "OAuth Bearer Token",
                "description": "Authentication scheme using the OAuth Bearer Token Standard",
            },
        ],
    }


@router.get("/ResourceTypes")
def resource_types() -> dict[str, Any]:
    """Describe available SCIM resource types."""
    return {
        "schemas": [_LIST_SCHEMA],
        "totalResults": 1,
        "Resources": [
            {
                "schemas": ["urn:ietf:params:scim:schemas:core:2.0:ResourceType"],
                "id": "User",
                "name": "User",
                "endpoint": "/Users",
                "schema": _USER_SCHEMA,
            },
        ],
    }


@router.get("/Schemas")
def schemas() -> dict[str, Any]:
    """Describe supported SCIM schemas (minimal)."""
    return {
        "schemas": [_LIST_SCHEMA],
        "totalResults": 1,
        "Resources": [
            {
                "id": _USER_SCHEMA,
                "name": "User",
                "description": "SCIM core User",
                "attributes": [
                    {"name": "userName", "type": "string", "required": True},
                    {"name": "displayName", "type": "string"},
                    {"name": "active", "type": "boolean"},
                ],
            },
        ],
    }


@router.get("/Users")
def list_users(
    _user: Any = _RequireAdmin,
    startIndex: int = Query(1, ge=1),  # noqa: N803 — SCIM param name
    count: int = Query(100, ge=0, le=500),
    filter: str | None = Query(None),  # noqa: A002 — SCIM param name
) -> dict[str, Any]:
    users, total = get_store().list_users(startIndex, count, filter)
    return {
        "schemas": [_LIST_SCHEMA],
        "totalResults": total,
        "startIndex": startIndex,
        "itemsPerPage": len(users),
        "Resources": [u.model_dump(exclude_none=True) for u in users],
    }


@router.post("/Users", status_code=status.HTTP_201_CREATED)
def create_user(
    user: SCIMUser,
    _request: Request,
    _auth: Any = _RequireAdmin,
) -> dict[str, Any]:
    try:
        created = get_store().create_user(user)
    except KeyError as exc:
        raise _scim_error(str(exc), status.HTTP_409_CONFLICT) from exc
    logger.info("scim.user.created", user_id=created.id, user_name=created.userName)
    return created.model_dump(exclude_none=True)


@router.get("/Users/{user_id}")
def get_user(user_id: str, _auth: Any = _RequireAdmin) -> dict[str, Any]:
    user = get_store().get_user(user_id)
    if user is None:
        raise _scim_error(f"user '{user_id}' not found", status.HTTP_404_NOT_FOUND)
    return user.model_dump(exclude_none=True)


@router.put("/Users/{user_id}")
def replace_user(
    user_id: str,
    user: SCIMUser,
    _auth: Any = _RequireAdmin,
) -> dict[str, Any]:
    try:
        replaced = get_store().replace_user(user_id, user)
    except KeyError as exc:
        raise _scim_error(f"user '{user_id}' not found", status.HTTP_404_NOT_FOUND) from exc
    logger.info("scim.user.replaced", user_id=user_id)
    return replaced.model_dump(exclude_none=True)


@router.patch("/Users/{user_id}")
def patch_user(
    user_id: str,
    payload: dict[str, Any],
    _auth: Any = _RequireAdmin,
) -> dict[str, Any]:
    if payload.get("schemas") and _PATCH_SCHEMA not in payload["schemas"]:
        raise _scim_error("invalid patch schema", status.HTTP_400_BAD_REQUEST)
    ops = payload.get("Operations", [])
    if not isinstance(ops, list):
        raise _scim_error("Operations must be a list", status.HTTP_400_BAD_REQUEST)
    try:
        patched = get_store().patch_user(user_id, ops)
    except KeyError as exc:
        raise _scim_error(f"user '{user_id}' not found", status.HTTP_404_NOT_FOUND) from exc
    logger.info("scim.user.patched", user_id=user_id, ops=len(ops))
    return patched.model_dump(exclude_none=True)


@router.delete("/Users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: str, _auth: Any = _RequireAdmin) -> None:
    try:
        get_store().delete_user(user_id)
    except KeyError as exc:
        raise _scim_error(f"user '{user_id}' not found", status.HTTP_404_NOT_FOUND) from exc
    logger.info("scim.user.deleted", user_id=user_id)


def scim_enabled() -> bool:
    """Whether SCIM endpoints should be registered (env-gated)."""
    return os.getenv("DEX_SCIM_ENABLED", "false").lower() == "true"
