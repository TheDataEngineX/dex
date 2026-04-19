"""LDAP → SCIM user sync.

Pulls users from an LDAP/AD directory and upserts them into the local
:class:`~dataenginex.api.scim.SCIMStore`. Designed for periodic invocation
(cron/scheduler) to keep the SCIM store aligned with the corporate directory.

Requires the ``ldap3`` optional dependency::

    uv sync --extra auth

Configuration (env vars)::

    DEX_LDAP_URL          — ldaps://ldap.example.com:636
    DEX_LDAP_BIND_DN      — service account DN
    DEX_LDAP_BIND_PASSWORD — service account password
    DEX_LDAP_BASE_DN      — OU or DC to search under
    DEX_LDAP_USER_FILTER  — LDAP filter (default "(objectClass=person)")
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

import structlog

from dataenginex.api.scim import SCIMEmail, SCIMStore, SCIMUser, get_store

logger = structlog.get_logger()

__all__ = ["LDAPConfig", "LDAPSyncer", "sync_from_env"]


@dataclass
class LDAPConfig:
    """Connection and search parameters for an LDAP sync."""

    url: str
    bind_dn: str
    bind_password: str
    base_dn: str
    user_filter: str = "(objectClass=person)"
    attributes: list[str] = field(
        default_factory=lambda: [
            "uid",
            "sAMAccountName",
            "mail",
            "givenName",
            "sn",
            "displayName",
            "memberOf",
        ],
    )


@dataclass
class SyncResult:
    """Summary of a sync run."""

    scanned: int = 0
    created: int = 0
    updated: int = 0
    skipped: int = 0
    errors: int = 0


class LDAPSyncer:
    """Sync LDAP entries into a :class:`SCIMStore`."""

    def __init__(self, config: LDAPConfig, store: SCIMStore | None = None) -> None:
        self.config = config
        self.store = store or get_store()

    def run(self) -> SyncResult:
        """Bind, search, and upsert each matched LDAP entry."""
        try:
            from ldap3 import ALL, SUBTREE, Connection, Server
        except ImportError as exc:
            msg = "ldap3 is required for LDAPSyncer — install with: uv sync --extra auth"
            raise ImportError(msg) from exc

        result = SyncResult()
        server = Server(self.config.url, get_info=ALL)
        with Connection(
            server,
            user=self.config.bind_dn,
            password=self.config.bind_password,
            auto_bind=True,
        ) as conn:
            conn.search(
                search_base=self.config.base_dn,
                search_filter=self.config.user_filter,
                search_scope=SUBTREE,
                attributes=self.config.attributes,
            )
            for entry in conn.entries:
                result.scanned += 1
                try:
                    user = self._entry_to_user(entry)
                    if user is None:
                        result.skipped += 1
                        continue
                    self._upsert(user, result)
                except Exception:  # noqa: BLE001 — per-entry isolation
                    logger.exception("ldap sync entry failed")
                    result.errors += 1
        logger.info("ldap sync complete", **result.__dict__)
        return result

    def _upsert(self, user: SCIMUser, result: SyncResult) -> None:
        existing, _ = self.store.list_users(
            start_index=1,
            count=1,
            filter_expr=f'userName eq "{user.userName}"',
        )
        if existing:
            self.store.replace_user(existing[0].id or "", user)
            result.updated += 1
        else:
            self.store.create_user(user)
            result.created += 1

    @staticmethod
    def _entry_to_user(entry: Any) -> SCIMUser | None:
        """Map an ``ldap3.Entry`` to a :class:`SCIMUser`."""
        user_name = _attr(entry, "uid") or _attr(entry, "sAMAccountName")
        if not user_name:
            return None
        mail = _attr(entry, "mail")
        emails = [SCIMEmail(value=mail, primary=True)] if mail else []
        display = _attr(entry, "displayName") or user_name
        roles_raw = getattr(entry, "memberOf", None)
        roles = [str(r).split(",", 1)[0].removeprefix("cn=") for r in (roles_raw or [])]
        return SCIMUser(
            userName=user_name,
            displayName=display,
            emails=emails,
            active=True,
            roles=roles,
            externalId=str(getattr(entry, "entry_dn", user_name)),
        )


def _attr(entry: Any, name: str) -> str:
    """Best-effort read of a single-valued LDAP attribute as str."""
    raw = getattr(entry, name, None)
    if raw is None:
        return ""
    value = getattr(raw, "value", raw)
    if isinstance(value, list | tuple):
        value = value[0] if value else ""
    return str(value) if value else ""


def sync_from_env(store: SCIMStore | None = None) -> SyncResult:
    """Run a sync using configuration from environment variables."""
    required = ("DEX_LDAP_URL", "DEX_LDAP_BIND_DN", "DEX_LDAP_BIND_PASSWORD", "DEX_LDAP_BASE_DN")
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        msg = f"LDAP sync missing env: {', '.join(missing)}"
        raise RuntimeError(msg)
    config = LDAPConfig(
        url=os.environ["DEX_LDAP_URL"],
        bind_dn=os.environ["DEX_LDAP_BIND_DN"],
        bind_password=os.environ["DEX_LDAP_BIND_PASSWORD"],
        base_dn=os.environ["DEX_LDAP_BASE_DN"],
        user_filter=os.getenv("DEX_LDAP_USER_FILTER", "(objectClass=person)"),
    )
    return LDAPSyncer(config, store).run()
