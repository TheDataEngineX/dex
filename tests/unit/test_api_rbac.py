"""Tests for dataenginex.api.rbac."""

from __future__ import annotations

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from dataenginex.api.auth import AuthUser
from dataenginex.api.rbac import Role, has_role, require_role


class TestRole:
    def test_hierarchy_order(self) -> None:
        assert Role.VIEWER < Role.EDITOR < Role.ADMIN < Role.OWNER

    def test_from_str_lookup(self) -> None:
        assert Role.from_str("viewer") is Role.VIEWER
        assert Role.from_str("ADMIN") is Role.ADMIN
        assert Role.from_str("unknown") is None


class TestHasRole:
    def test_no_user(self) -> None:
        assert has_role(None, Role.VIEWER) is False

    def test_empty_roles(self) -> None:
        u = AuthUser(sub="u", roles=[], claims={})
        assert has_role(u, Role.VIEWER) is False

    def test_exact_match(self) -> None:
        u = AuthUser(sub="u", roles=["editor"], claims={})
        assert has_role(u, Role.EDITOR) is True

    def test_higher_role_grants_lower(self) -> None:
        u = AuthUser(sub="u", roles=["admin"], claims={})
        assert has_role(u, Role.VIEWER) is True
        assert has_role(u, Role.EDITOR) is True

    def test_lower_role_denies_higher(self) -> None:
        u = AuthUser(sub="u", roles=["viewer"], claims={})
        assert has_role(u, Role.ADMIN) is False

    def test_unknown_role_string_ignored(self) -> None:
        u = AuthUser(sub="u", roles=["nonsense"], claims={})
        assert has_role(u, Role.VIEWER) is False


class TestRequireRoleDependency:
    def _app(self) -> FastAPI:
        app = FastAPI()

        @app.get("/admin-only")
        def _route(_: object = Depends(require_role(Role.ADMIN))) -> dict[str, str]:
            return {"ok": "yes"}

        return app

    def test_off_mode_allows_all(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DEX_RBAC_ENFORCE", "off")
        client = TestClient(self._app())
        assert client.get("/admin-only").status_code == 200

    def test_warn_mode_logs_but_allows(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DEX_RBAC_ENFORCE", "warn")
        client = TestClient(self._app())
        assert client.get("/admin-only").status_code == 200

    def test_enforce_mode_denies_without_role(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DEX_RBAC_ENFORCE", "enforce")
        client = TestClient(self._app())
        r = client.get("/admin-only")
        assert r.status_code == 403

    def test_enforce_mode_allows_with_admin(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DEX_RBAC_ENFORCE", "enforce")

        app = FastAPI()

        @app.middleware("http")
        async def _inject(request, call_next):  # type: ignore[no-untyped-def]
            request.state.auth_user = AuthUser(sub="u", roles=["admin"], claims={})
            return await call_next(request)

        @app.get("/admin-only")
        def _route(_: object = Depends(require_role(Role.ADMIN))) -> dict[str, str]:
            return {"ok": "yes"}

        client = TestClient(app)
        assert client.get("/admin-only").status_code == 200

    def test_enforce_mode_denies_editor_for_admin_route(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("DEX_RBAC_ENFORCE", "enforce")

        app = FastAPI()

        @app.middleware("http")
        async def _inject(request, call_next):  # type: ignore[no-untyped-def]
            request.state.auth_user = AuthUser(sub="u", roles=["editor"], claims={})
            return await call_next(request)

        @app.get("/admin-only")
        def _route(_: object = Depends(require_role(Role.ADMIN))) -> dict[str, str]:
            return {"ok": "yes"}

        client = TestClient(app)
        assert client.get("/admin-only").status_code == 403
