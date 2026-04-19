"""Tests for SCIM 2.0 endpoints (api/scim.py)."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from dataenginex.api.scim import (
    MemorySCIMStore,
    SCIMEmail,
    SCIMUser,
    reset_store,
    router,
)


@pytest.fixture(autouse=True)
def _fresh_store() -> None:
    reset_store(MemorySCIMStore())


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


class TestMemorySCIMStore:
    def test_create_assigns_id_and_meta(self) -> None:
        store = MemorySCIMStore()
        user = store.create_user(SCIMUser(userName="alice"))
        assert user.id
        assert user.meta["resourceType"] == "User"
        assert user.meta["location"].startswith("/scim/v2/Users/")

    def test_create_duplicate_username_raises(self) -> None:
        store = MemorySCIMStore()
        store.create_user(SCIMUser(userName="alice"))
        with pytest.raises(KeyError, match="alice"):
            store.create_user(SCIMUser(userName="alice"))

    def test_patch_replaces_top_level_field(self) -> None:
        store = MemorySCIMStore()
        created = store.create_user(SCIMUser(userName="bob", displayName="Bob"))
        assert created.id is not None
        patched = store.patch_user(
            created.id,
            [{"op": "replace", "path": "displayName", "value": "Bobby"}],
        )
        assert patched.displayName == "Bobby"

    def test_replace_preserves_created_timestamp(self) -> None:
        store = MemorySCIMStore()
        original = store.create_user(SCIMUser(userName="eve"))
        assert original.id is not None
        replaced = store.replace_user(original.id, SCIMUser(userName="eve", displayName="Eve"))
        assert replaced.meta["created"] == original.meta["created"]
        assert replaced.displayName == "Eve"

    def test_delete_then_get_returns_none(self) -> None:
        store = MemorySCIMStore()
        created = store.create_user(SCIMUser(userName="x"))
        assert created.id is not None
        store.delete_user(created.id)
        assert store.get_user(created.id) is None

    def test_filter_by_username(self) -> None:
        store = MemorySCIMStore()
        store.create_user(SCIMUser(userName="a"))
        store.create_user(SCIMUser(userName="b"))
        users, total = store.list_users(filter_expr='userName eq "a"')
        assert total == 1
        assert users[0].userName == "a"


class TestSCIMDiscovery:
    def test_service_provider_config(self, client: TestClient) -> None:
        resp = client.get("/scim/v2/ServiceProviderConfig")
        assert resp.status_code == 200
        body = resp.json()
        assert body["patch"]["supported"] is True
        assert body["filter"]["supported"] is True

    def test_resource_types(self, client: TestClient) -> None:
        resp = client.get("/scim/v2/ResourceTypes")
        assert resp.status_code == 200
        body = resp.json()
        assert body["totalResults"] == 1
        assert body["Resources"][0]["id"] == "User"

    def test_schemas(self, client: TestClient) -> None:
        resp = client.get("/scim/v2/Schemas")
        assert resp.status_code == 200


class TestSCIMUsersCRUD:
    def test_create_and_get(self, client: TestClient) -> None:
        payload = {
            "userName": "alice",
            "emails": [{"value": "alice@example.com", "primary": True}],
        }
        create_resp = client.post("/scim/v2/Users", json=payload)
        assert create_resp.status_code == 201
        user_id = create_resp.json()["id"]

        get_resp = client.get(f"/scim/v2/Users/{user_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["userName"] == "alice"

    def test_list_returns_scim_envelope(self, client: TestClient) -> None:
        client.post("/scim/v2/Users", json={"userName": "x"})
        client.post("/scim/v2/Users", json={"userName": "y"})
        resp = client.get("/scim/v2/Users")
        body = resp.json()
        assert body["totalResults"] == 2
        assert body["itemsPerPage"] == 2
        assert body["startIndex"] == 1

    def test_patch(self, client: TestClient) -> None:
        create_resp = client.post("/scim/v2/Users", json={"userName": "p"})
        user_id = create_resp.json()["id"]
        patch_resp = client.patch(
            f"/scim/v2/Users/{user_id}",
            json={
                "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
                "Operations": [
                    {"op": "replace", "path": "displayName", "value": "P User"},
                ],
            },
        )
        assert patch_resp.status_code == 200
        assert patch_resp.json()["displayName"] == "P User"

    def test_duplicate_username_returns_409(self, client: TestClient) -> None:
        client.post("/scim/v2/Users", json={"userName": "dup"})
        resp = client.post("/scim/v2/Users", json={"userName": "dup"})
        assert resp.status_code == 409

    def test_missing_user_returns_404(self, client: TestClient) -> None:
        resp = client.get("/scim/v2/Users/does-not-exist")
        assert resp.status_code == 404

    def test_delete(self, client: TestClient) -> None:
        create_resp = client.post("/scim/v2/Users", json={"userName": "to-delete"})
        user_id = create_resp.json()["id"]
        del_resp = client.delete(f"/scim/v2/Users/{user_id}")
        assert del_resp.status_code == 204
        assert client.get(f"/scim/v2/Users/{user_id}").status_code == 404


class TestSCIMModels:
    def test_email_extra_allowed(self) -> None:
        email = SCIMEmail(value="a@b.com", primary=True, display="A")  # type: ignore[call-arg]
        assert email.value == "a@b.com"

    def test_user_round_trip(self) -> None:
        user = SCIMUser(userName="round", emails=[SCIMEmail(value="r@b.com")])
        dumped = user.model_dump(exclude_none=True)
        parsed = SCIMUser(**dumped)
        assert parsed.userName == "round"
