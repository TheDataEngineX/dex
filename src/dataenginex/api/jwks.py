"""JWKS client and RS256 token verification — per ADR-005.

Enterprise identity providers (Okta, Auth0, Keycloak, AWS Cognito, Azure AD)
publish their signing keys at a JWKS endpoint. This module fetches those
keys on demand, caches them with a short TTL, and exposes an RS256 token
verifier that selects the correct key by the ``kid`` header.

Requires the ``[auth]`` extra::

    pip install dataenginex[auth]
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any

import httpx
import structlog

logger = structlog.get_logger()

__all__ = [
    "JWKSClient",
    "JWKSError",
    "decode_rs256_token",
]


class JWKSError(RuntimeError):
    """Raised on JWKS fetch or key-lookup failure."""


@dataclass
class JWKSClient:
    """Fetches and caches public keys from a JWKS endpoint.

    Attributes:
        url: JWKS endpoint URL (e.g. ``https://auth.example.com/.well-known/jwks.json``).
        ttl_seconds: How long to cache a successful fetch before refetching.
        timeout_seconds: httpx request timeout.
    """

    url: str
    ttl_seconds: int = 3600
    timeout_seconds: int = 10
    _keys: dict[str, Any] = field(default_factory=dict, init=False, repr=False)
    _fetched_at: float = field(default=0.0, init=False, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)

    def get_key(self, kid: str) -> Any:
        """Return the public key for ``kid``, refreshing JWKS if unknown or stale."""
        with self._lock:
            if self._is_stale() or kid not in self._keys:
                self._refresh()
            if kid not in self._keys:
                msg = f"No key with kid={kid!r} in JWKS at {self.url}"
                raise JWKSError(msg)
            return self._keys[kid]

    def _is_stale(self) -> bool:
        return (time.monotonic() - self._fetched_at) > self.ttl_seconds

    def _refresh(self) -> None:
        try:
            import jwt  # noqa: F401 — ensures PyJWKClient is available
        except ImportError as exc:
            msg = "pyjwt[crypto] is required for JWKS support — pip install dataenginex[auth]"
            raise JWKSError(msg) from exc

        try:
            resp = httpx.get(self.url, timeout=self.timeout_seconds)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            msg = f"Failed to fetch JWKS from {self.url}: {exc}"
            raise JWKSError(msg) from exc

        from jwt.algorithms import RSAAlgorithm

        data = resp.json()
        keys = data.get("keys") or []
        if not keys:
            msg = f"JWKS at {self.url} contains no keys"
            raise JWKSError(msg)

        loaded: dict[str, Any] = {}
        for jwk in keys:
            kid = jwk.get("kid")
            if not kid:
                continue
            try:
                loaded[kid] = RSAAlgorithm.from_jwk(jwk)
            except Exception:  # noqa: BLE001 — key parse failures are skipped
                logger.warning("jwks.key_parse_failed", kid=kid)
                continue

        if not loaded:
            msg = f"JWKS at {self.url} contains no parseable RSA keys"
            raise JWKSError(msg)

        self._keys = loaded
        self._fetched_at = time.monotonic()
        logger.info("jwks.refreshed", url=self.url, key_count=len(loaded))


def decode_rs256_token(
    token: str,
    jwks_client: JWKSClient,
    *,
    audience: str | None = None,
    issuer: str | None = None,
) -> dict[str, Any]:
    """Decode and verify an RS256 JWT using a JWKS-resolved public key.

    Raises :class:`ValueError` on any validation failure so callers can
    treat RS256 and HS256 verification paths uniformly.
    """
    try:
        import jwt
    except ImportError as exc:
        msg = "pyjwt[crypto] is required for RS256 — pip install dataenginex[auth]"
        raise ValueError(msg) from exc

    try:
        header = jwt.get_unverified_header(token)
    except jwt.InvalidTokenError as exc:
        raise ValueError(f"Malformed JWT: {exc}") from exc

    kid = header.get("kid")
    if not kid:
        msg = "RS256 token missing 'kid' header"
        raise ValueError(msg)

    try:
        key = jwks_client.get_key(kid)
    except JWKSError as exc:
        raise ValueError(str(exc)) from exc

    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            key=key,
            algorithms=["RS256"],
            audience=audience,
            issuer=issuer,
            options={"verify_aud": audience is not None},
        )
    except jwt.ExpiredSignatureError as exc:
        raise ValueError("Token expired") from exc
    except jwt.InvalidTokenError as exc:
        raise ValueError(f"Invalid RS256 token: {exc}") from exc

    return payload
