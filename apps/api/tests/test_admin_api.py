"""Admin API tests — companies, establishments, auth context."""

from __future__ import annotations

import os
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("AUTH0_USE_MOCK", "true")
os.environ.setdefault("AUTH0_DOMAIN", "dev.argus.local")

from argus.apps.http import create_admin_app
from argus.config import get_settings
from argus.domain.enums import UserRole
from argus.services.database import dispose_engine
from argus.services.redis import close_redis
from tests.conftest import (
    SEED_COMPANY_ID,
    SEED_ESTABLISHMENT_ID,
    SEED_PASSWORD,
    SEED_ROOT_EMAIL,
)
from tests.helpers import bearer, session_token

get_settings.cache_clear()


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=create_admin_app())
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    await close_redis()
    await dispose_engine()


async def _token(role: UserRole, company_id: str | None = SEED_COMPANY_ID) -> str:
    return await session_token(role, company_id or None)


@pytest.mark.asyncio
async def test_root_lists_companies(client: AsyncClient) -> None:
    response = await client.get("/v1/admin/companies", headers=bearer(await _token(UserRole.ROOT, "")))
    assert response.status_code == 200
    assert any(t["slug"] == "demo-company" for t in response.json())


@pytest.mark.asyncio
async def test_admin_role_can_list_companies(client: AsyncClient) -> None:
    response = await client.get("/v1/admin/companies", headers=bearer(await _token(UserRole.ADMIN, "")))
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_manager_cannot_create_company(client: AsyncClient) -> None:
    response = await client.post(
        "/v1/admin/companies",
        json={"name": "Blocked", "slug": "blocked"},
        headers=bearer(await _token(UserRole.MANAGER)),
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_cross_tenant_access_denied(client: AsyncClient) -> None:
    other = str(uuid.uuid4())
    response = await client.get(
        f"/v1/companies/{other}/establishments",
        headers=bearer(await _token(UserRole.MANAGER)),
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_manager_lists_establishments(client: AsyncClient) -> None:
    response = await client.get(
        f"/v1/companies/{SEED_COMPANY_ID}/establishments",
        headers=bearer(await _token(UserRole.MANAGER)),
    )
    assert response.status_code == 200
    assert len(response.json()) >= 1


@pytest.mark.asyncio
async def test_login_returns_opaque_token(client: AsyncClient) -> None:
    response = await client.post(
        "/v1/auth/login",
        json={"email": SEED_ROOT_EMAIL, "password": SEED_PASSWORD},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token"].startswith("sess_")
    assert body["user"]["role"] == "root"


@pytest.mark.asyncio
async def test_invalid_login_is_rejected(client: AsyncClient) -> None:
    response = await client.post(
        "/v1/auth/login",
        json={"email": SEED_ROOT_EMAIL, "password": "wrong"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_root_can_switch_active_tenant(client: AsyncClient) -> None:
    login = await client.post(
        "/v1/auth/login",
        json={"email": SEED_ROOT_EMAIL, "password": SEED_PASSWORD},
    )
    token = login.json()["token"]
    response = await client.patch(
        "/v1/auth/context",
        json={"companyId": SEED_COMPANY_ID},
        headers=bearer(token),
    )
    assert response.status_code == 200
    assert response.json()["activeCompany"]["id"] == SEED_COMPANY_ID

    me = await client.get("/v1/auth/me", headers=bearer(token))
    assert me.status_code == 200
    assert me.json()["activeCompany"]["id"] == SEED_COMPANY_ID


@pytest.mark.asyncio
async def test_root_can_switch_active_location_alias(client: AsyncClient) -> None:
    """activeLocation remains an API alias for establishment."""
    login = await client.post(
        "/v1/auth/login",
        json={"email": SEED_ROOT_EMAIL, "password": SEED_PASSWORD},
    )
    token = login.json()["token"]
    await client.patch("/v1/auth/context", json={"companyId": SEED_COMPANY_ID}, headers=bearer(token))
    establishments = (
        await client.get(
            f"/v1/companies/{SEED_COMPANY_ID}/establishments", headers=bearer(token)
        )
    ).json()
    establishment_id = establishments[0]["id"]
    response = await client.patch(
        "/v1/auth/context",
        json={"locationId": establishment_id},
        headers=bearer(token),
    )
    assert response.status_code == 200
    assert response.json()["activeLocation"]["id"] == establishment_id
    assert response.json()["activeEstablishment"]["id"] == establishment_id
    assert response.json()["activeLocation"]["address"]


@pytest.mark.asyncio
async def test_root_can_manage_users_but_manager_cannot(client: AsyncClient) -> None:
    email = f"new-manager-{uuid.uuid4().hex[:8]}@demo.local"
    created = await client.post(
        "/v1/admin/users",
        json={
            "company_id": SEED_COMPANY_ID,
            "email": email,
            "password": SEED_PASSWORD,
            "role": "manager",
        },
        headers=bearer(await _token(UserRole.ROOT, "")),
    )
    assert created.status_code == 201

    denied = await client.post(
        "/v1/admin/users",
        json={
            "company_id": SEED_COMPANY_ID,
            "email": "blocked@demo.local",
            "role": "manager",
        },
        headers=bearer(await _token(UserRole.MANAGER)),
    )
    assert denied.status_code == 403

    login = await client.post("/v1/auth/login", json={"email": email, "password": SEED_PASSWORD})
    assert login.status_code == 200
    assert login.json()["user"]["role"] == "manager"


@pytest.mark.asyncio
async def test_manager_can_update_establishment(client: AsyncClient) -> None:
    headers = bearer(await _token(UserRole.MANAGER))
    establishments = (
        await client.get(f"/v1/companies/{SEED_COMPANY_ID}/establishments", headers=headers)
    ).json()
    establishment = establishments[0]
    response = await client.patch(
        f"/v1/companies/{SEED_COMPANY_ID}/establishments/{establishment['id']}",
        json={
            "name": establishment["name"],
            "address": "New Address 42",
            "timezone": establishment["timezone"],
        },
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["address"] == "New Address 42"


@pytest.mark.asyncio
async def test_manager_gets_establishment_by_id(client: AsyncClient) -> None:
    headers = bearer(await _token(UserRole.MANAGER))
    response = await client.get(
        f"/v1/companies/{SEED_COMPANY_ID}/establishments/{SEED_ESTABLISHMENT_ID}",
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["id"] == SEED_ESTABLISHMENT_ID

    missing = await client.get(
        f"/v1/companies/{SEED_COMPANY_ID}/establishments/{uuid.uuid4()}",
        headers=headers,
    )
    assert missing.status_code == 404
    assert missing.json()["error"]["message"] == "Establishment not found"


@pytest.mark.asyncio
async def test_operator_cannot_get_establishment(client: AsyncClient) -> None:
    response = await client.get(
        f"/v1/companies/{SEED_COMPANY_ID}/establishments/{SEED_ESTABLISHMENT_ID}",
        headers=bearer(await _token(UserRole.OPERATOR)),
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_camera_list_sorted_and_include_inactive(client: AsyncClient) -> None:
    headers = bearer(await _token(UserRole.MANAGER))
    base = f"/v1/companies/{SEED_COMPANY_ID}/establishments/{SEED_ESTABLISHMENT_ID}/cameras"
    suffix = uuid.uuid4().hex[:6]
    zeta = (await client.post(base, json={"name": f"Zeta {suffix}"}, headers=headers)).json()
    alpha = (await client.post(base, json={"name": f"Alpha {suffix}"}, headers=headers)).json()

    listed = (await client.get(base, headers=headers)).json()
    names = [camera["name"] for camera in listed]
    assert names == sorted(names)
    assert names.index(alpha["name"]) < names.index(zeta["name"])

    disabled = await client.patch(
        f"/v1/companies/{SEED_COMPANY_ID}/cameras/{zeta['id']}",
        json={"is_active": False},
        headers=headers,
    )
    assert disabled.status_code == 200
    default_ids = {camera["id"] for camera in (await client.get(base, headers=headers)).json()}
    assert zeta["id"] not in default_ids
    assert alpha["id"] in default_ids

    with_inactive = (await client.get(f"{base}?include_inactive=true", headers=headers)).json()
    inactive_ids = {camera["id"] for camera in with_inactive}
    assert zeta["id"] in inactive_ids
    assert next(c for c in with_inactive if c["id"] == zeta["id"])["is_active"] is False

    for camera in (zeta, alpha):
        await client.delete(f"/v1/companies/{SEED_COMPANY_ID}/cameras/{camera['id']}", headers=headers)
    after_delete = (await client.get(f"{base}?include_inactive=true", headers=headers)).json()
    assert zeta["id"] not in {camera["id"] for camera in after_delete}


@pytest.mark.asyncio
async def test_camera_update_keeps_or_clears_credentials(client: AsyncClient) -> None:
    headers = bearer(await _token(UserRole.MANAGER))
    base = f"/v1/companies/{SEED_COMPANY_ID}/establishments/{SEED_ESTABLISHMENT_ID}/cameras"
    created = (
        await client.post(
            base,
            json={
                "name": f"Cred {uuid.uuid4().hex[:6]}",
                "stream_url": "rtsp://cam.local/stream",
                "stream_username": "user1",
                "stream_password": "secret",
            },
            headers=headers,
        )
    ).json()
    camera_url = f"/v1/companies/{SEED_COMPANY_ID}/cameras/{created['id']}"

    renamed = await client.patch(camera_url, json={"name": "Renamed"}, headers=headers)
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "Renamed"
    assert renamed.json()["stream_username"] == "user1"
    assert renamed.json()["stream_url"] == "rtsp://cam.local/stream"

    cleared = await client.patch(camera_url, json={"stream_username": ""}, headers=headers)
    assert cleared.status_code == 200
    assert cleared.json()["stream_username"] is None
    assert cleared.json()["stream_url"] == "rtsp://cam.local/stream"

    await client.delete(camera_url, headers=headers)
