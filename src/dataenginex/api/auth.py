"""
JWT authentication middleware for DEX API.

Provides a ``JWTAuth`` dependency for FastAPI that validates bearer tokens
using HMAC-SHA256 (symmetric) or RSA (asymmetric via ``DEX_JWT_PUBLIC_KEY``).

Configuration is via environment variables:
    DEX_JWT_SECRET   — HMAC shared secret (required unless RSA key is set)
    DEX_JWT_ALGORITHM — Algorithm (default HS256)
    DEX_AUTH_ENABLED  — "true" to enforce auth (default "false")
"""

from __future__ import annotations

import hmac
import json
import os
import time
from base64 import urlsafe_b64decode, urlsafe_b64encode
from dataclasses import dataclass
from hashlib import sha256
from typing import Any

import structlog
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

logger = structlog.get_logger()
__all__ = [
    "AuthMiddleware",
    "AuthUser",
    "create_token",
    "decode_token",
    "decode_token_auto",
]

# ---------------------------------------------------------------------------
# Token helpers (pure-Python HS256 — no external ``pyjwt`` needed)
# ---------------------------------------------------------------------------


def _b64url_decode(data: str) -> bytes:
    padding = 4 - len(data) % 4
    return urlsafe_b64decode(data + "=" * padding)


def _b64url_encode(data: bytes) -> str:
    return urlsafe_b64encode(data).rstrip(b"=").decode()


def create_token(payload: dict[str, Any], secret: str, ttl: int = 3600) -> str:
    """Create a HS256 JWT token.

    Parameters
    ----------
    payload:
        Claims dict (e.g. ``{"sub": "user123", "roles": ["admin"]}``).
    secret:
        HMAC shared secret.
    ttl:
        Time-to-live in seconds (default 1 hour).
    """
    header = {"alg": "HS256", "typ": "JWT"}
    now = int(time.time())
    payload = {**payload, "iat": now, "exp": now + ttl}

    segments = [
        _b64url_encode(json.dumps(header).encode()),
        _b64url_encode(json.dumps(payload, default=str).encode()),
    ]
    signing_input = f"{segments[0]}.{segments[1]}"
    signature = hmac.new(secret.encode(), signing_input.encode(), sha256).digest()
    segments.append(_b64url_encode(signature))
    return ".".join(segments)


def decode_token(token: str, secret: str) -> dict[str, Any]:
    """Decode and verify a HS256 JWT token.  Raises ``ValueError`` on failure."""
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Malformed JWT")

    signing_input = f"{parts[0]}.{parts[1]}"
    expected_sig = hmac.new(secret.encode(), signing_input.encode(), sha256).digest()
    actual_sig = _b64url_decode(parts[2])

    if not hmac.compare_digest(expected_sig, actual_sig):
        raise ValueError("Invalid JWT signature")

    payload: dict[str, Any] = json.loads(_b64url_decode(parts[1]))
    exp = payload.get("exp")
    if exp is not None and int(exp) < int(time.time()):
        raise ValueError("Token expired")

    return payload


def decode_token_auto(
    token: str,
    *,
    hs256_secret: str | None = None,
    jwks_url: str | None = None,
    audience: str | None = None,
    issuer: str | None = None,
) -> dict[str, Any]:
    """Decode a JWT, dispatching on the ``alg`` header.

    Supports HS256 (shared secret) and RS256 (JWKS-resolved public key).
    Raises :class:`ValueError` on any validation failure.
    """
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Malformed JWT")
    try:
        header = json.loads(_b64url_decode(parts[0]))
    except ValueError as exc:
        raise ValueError("Malformed JWT header") from exc

    alg = header.get("alg")
    if alg == "HS256":
        if not hs256_secret:
            raise ValueError("HS256 token received but no secret configured")
        return decode_token(token, hs256_secret)
    if alg == "RS256":
        if not jwks_url:
            raise ValueError("RS256 token received but DEX_JWKS_URL not configured")
        from dataenginex.api.jwks import decode_rs256_token

        client = _jwks_client_for(jwks_url)
        return decode_rs256_token(token, client, audience=audience, issuer=issuer)
    raise ValueError(f"Unsupported JWT algorithm: {alg!r}")


_JWKS_CACHE: dict[str, Any] = {}


def _jwks_client_for(url: str) -> Any:
    """Return a cached :class:`~dataenginex.api.jwks.JWKSClient` for ``url``."""
    if url not in _JWKS_CACHE:
        from dataenginex.api.jwks import JWKSClient

        _JWKS_CACHE[url] = JWKSClient(url=url)
    return _JWKS_CACHE[url]


# ---------------------------------------------------------------------------
# Dataclass carrying the authenticated user info
# ---------------------------------------------------------------------------


@dataclass
class AuthUser:
    """Resolved identity from a valid JWT."""

    sub: str
    roles: list[str]
    claims: dict[str, Any]


# ---------------------------------------------------------------------------
# FastAPI middleware
# ---------------------------------------------------------------------------

# Paths that never require authentication
_PUBLIC_PATHS: set[str] = {
    "/",
    "/health",
    "/ready",
    "/startup",
    "/metrics",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/openapi.yaml",
}


class AuthMiddleware(BaseHTTPMiddleware):
    """Starlette middleware that enforces JWT auth when enabled.

    When ``DEX_AUTH_ENABLED`` is ``"true"`` (case-insensitive), every request
    to a non-public path must carry a valid ``Authorization: Bearer <token>``
    header. The decoded claims are stored on ``request.state.auth_user``.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Validate the bearer token and attach ``auth_user`` to request state."""
        enabled = os.getenv("DEX_AUTH_ENABLED", "false").lower() == "true"
        if not enabled:
            return await call_next(request)

        # Skip public endpoints
        if request.url.path in _PUBLIC_PATHS:
            return await call_next(request)

        secret = os.getenv("DEX_JWT_SECRET", "")
        jwks_url = os.getenv("DEX_JWKS_URL", "")
        if not secret and not jwks_url:
            logger.error(
                "DEX_AUTH_ENABLED=true but neither DEX_JWT_SECRET nor DEX_JWKS_URL is set",
            )
            return JSONResponse(
                status_code=500,
                content={"error": "auth_config_error", "message": "Auth not configured"},
            )

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"error": "unauthorized", "message": "Missing bearer token"},
            )

        token = auth_header[7:]
        audience = os.getenv("DEX_JWT_AUDIENCE") or None
        issuer = os.getenv("DEX_JWT_ISSUER") or None
        try:
            claims = decode_token_auto(
                token,
                hs256_secret=secret or None,
                jwks_url=jwks_url or None,
                audience=audience,
                issuer=issuer,
            )
        except ValueError:
            logger.exception("JWT validation failed")
            return JSONResponse(
                status_code=401,
                content={
                    "error": "unauthorized",
                    "message": "Invalid or expired authentication token",
                },
            )

        request.state.auth_user = AuthUser(
            sub=claims.get("sub", "anonymous"),
            roles=claims.get("roles", []),
            claims=claims,
        )
        return await call_next(request)
