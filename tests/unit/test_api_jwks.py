"""Tests for RS256 + JWKS token verification (ADR-005)."""

from __future__ import annotations

from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from dataenginex.api.auth import decode_token_auto
from dataenginex.api.jwks import JWKSClient, JWKSError, decode_rs256_token


@pytest.fixture(scope="module")
def rsa_keypair() -> tuple[rsa.RSAPrivateKey, dict[str, Any]]:
    """Generate an RSA keypair and a JWKS-style public key representation."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_numbers = key.public_key().public_numbers()

    import base64

    def _b64(n: int) -> str:
        byte_len = (n.bit_length() + 7) // 8
        return base64.urlsafe_b64encode(n.to_bytes(byte_len, "big")).rstrip(b"=").decode()

    jwk = {
        "kty": "RSA",
        "use": "sig",
        "alg": "RS256",
        "kid": "test-key-1",
        "n": _b64(public_numbers.n),
        "e": _b64(public_numbers.e),
    }
    return key, jwk


def _sign_rs256(
    key: rsa.RSAPrivateKey,
    claims: dict[str, Any],
    *,
    kid: str = "test-key-1",
) -> str:
    pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return jwt.encode(claims, pem, algorithm="RS256", headers={"kid": kid})


class _StubClient(JWKSClient):
    """JWKS client that short-circuits the network and serves a provided JWK."""

    def __init__(self, jwk: dict[str, Any]) -> None:
        super().__init__(url="https://stub.example/jwks.json")
        self._seed = jwk

    def _refresh(self) -> None:  # type: ignore[override]
        from jwt.algorithms import RSAAlgorithm

        self._keys = {self._seed["kid"]: RSAAlgorithm.from_jwk(self._seed)}
        import time

        self._fetched_at = time.monotonic()


class TestDecodeRS256Token:
    def test_valid_token_decodes(self, rsa_keypair) -> None:  # type: ignore[no-untyped-def]
        import time

        key, jwk = rsa_keypair
        token = _sign_rs256(
            key,
            {
                "sub": "u1",
                "roles": ["editor"],
                "exp": int(time.time()) + 60,
                "iss": "https://issuer.example",
            },
        )
        client = _StubClient(jwk)
        payload = decode_rs256_token(token, client, issuer="https://issuer.example")
        assert payload["sub"] == "u1"
        assert payload["roles"] == ["editor"]

    def test_missing_kid_rejected(self, rsa_keypair) -> None:  # type: ignore[no-untyped-def]
        import time

        key, jwk = rsa_keypair
        pem = key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        token = jwt.encode({"sub": "u", "exp": int(time.time()) + 60}, pem, algorithm="RS256")
        client = _StubClient(jwk)
        with pytest.raises(ValueError, match="kid"):
            decode_rs256_token(token, client)

    def test_unknown_kid_rejected(self, rsa_keypair) -> None:  # type: ignore[no-untyped-def]
        import time

        key, jwk = rsa_keypair
        token = _sign_rs256(key, {"sub": "u", "exp": int(time.time()) + 60}, kid="other")
        client = _StubClient(jwk)
        with pytest.raises(ValueError):
            decode_rs256_token(token, client)

    def test_expired_rejected(self, rsa_keypair) -> None:  # type: ignore[no-untyped-def]
        key, jwk = rsa_keypair
        token = _sign_rs256(key, {"sub": "u", "exp": 1})
        client = _StubClient(jwk)
        with pytest.raises(ValueError, match="expired|Expired|Invalid"):
            decode_rs256_token(token, client)


class TestDecodeTokenAutoDispatch:
    def test_hs256_path(self) -> None:
        from dataenginex.api.auth import create_token

        token = create_token({"sub": "u", "roles": ["viewer"]}, secret="s3cret")
        payload = decode_token_auto(token, hs256_secret="s3cret")
        assert payload["sub"] == "u"

    def test_rs256_path(self, rsa_keypair, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        import time

        from dataenginex.api import auth as auth_mod

        key, jwk = rsa_keypair
        client = _StubClient(jwk)

        monkeypatch.setattr(
            auth_mod,
            "_jwks_client_for",
            lambda _url: client,
        )

        token = _sign_rs256(key, {"sub": "u", "exp": int(time.time()) + 60})
        payload = decode_token_auto(token, jwks_url="https://any")
        assert payload["sub"] == "u"

    def test_hs256_without_secret_rejected(self) -> None:
        from dataenginex.api.auth import create_token

        token = create_token({"sub": "u"}, secret="s")
        with pytest.raises(ValueError, match="no secret configured"):
            decode_token_auto(token)

    def test_rs256_without_jwks_rejected(self, rsa_keypair) -> None:  # type: ignore[no-untyped-def]
        import time

        key, _jwk = rsa_keypair
        token = _sign_rs256(key, {"sub": "u", "exp": int(time.time()) + 60})
        with pytest.raises(ValueError, match="DEX_JWKS_URL"):
            decode_token_auto(token)

    def test_unsupported_alg_rejected(self) -> None:
        # Hand-craft a token with alg=none (unsupported)
        import base64
        import json

        header = base64.urlsafe_b64encode(json.dumps({"alg": "none"}).encode()).rstrip(b"=")
        payload = base64.urlsafe_b64encode(json.dumps({"sub": "u"}).encode()).rstrip(b"=")
        token = f"{header.decode()}.{payload.decode()}.x"
        with pytest.raises(ValueError, match="Unsupported"):
            decode_token_auto(token, hs256_secret="s")


class TestJWKSClientErrors:
    def test_unknown_kid_after_refresh(self, rsa_keypair) -> None:  # type: ignore[no-untyped-def]
        _, jwk = rsa_keypair
        client = _StubClient(jwk)
        # First call primes the cache, then asking for a different kid must raise
        client.get_key(jwk["kid"])
        with pytest.raises(JWKSError):
            client.get_key("nonexistent-kid")
