"""Admin API tests."""

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
from tests.helpers import bearer, session_token

get_settings.cache_clear()

SEED_COMPANY_ID = "11111111-1111-4111-8111-111111111111"
SEED_LOCATION_ID = "22222222-2222-4222-8222-222222222222"
SEED_ROOT_EMAIL = "root@argus.local"
SEED_PASSWORD = "Password123!"


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
    assert any(t["slug"] == "downtown-retail" for t in response.json())


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
        f"/v1/companies/{other}/locations",
        headers=bearer(await _token(UserRole.MANAGER)),
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_manager_lists_locations(client: AsyncClient) -> None:
    response = await client.get(
        f"/v1/companies/{SEED_COMPANY_ID}/locations",
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
async def test_root_can_switch_active_location(client: AsyncClient) -> None:
    login = await client.post(
        "/v1/auth/login",
        json={"email": SEED_ROOT_EMAIL, "password": SEED_PASSWORD},
    )
    token = login.json()["token"]
    await client.patch("/v1/auth/context", json={"companyId": SEED_COMPANY_ID}, headers=bearer(token))
    locations = (
        await client.get(f"/v1/companies/{SEED_COMPANY_ID}/locations", headers=bearer(token))
    ).json()
    location_id = locations[0]["id"]
    response = await client.patch(
        "/v1/auth/context",
        json={"locationId": location_id},
        headers=bearer(token),
    )
    assert response.status_code == 200
    assert response.json()["activeLocation"]["id"] == location_id
    assert response.json()["activeLocation"]["address"]


@pytest.mark.asyncio
async def test_root_can_manage_users_but_manager_cannot(client: AsyncClient) -> None:
    email = f"new-manager-{uuid.uuid4().hex[:8]}@downtown-retail.local"
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
            "email": "blocked@downtown-retail.local",
            "role": "manager",
        },
        headers=bearer(await _token(UserRole.MANAGER)),
    )
    assert denied.status_code == 403

    login = await client.post("/v1/auth/login", json={"email": email, "password": SEED_PASSWORD})
    assert login.status_code == 200
    assert login.json()["user"]["role"] == "manager"


@pytest.mark.asyncio
async def test_manager_can_update_market_location(client: AsyncClient) -> None:
    headers = bearer(await _token(UserRole.MANAGER))
    locations = (
        await client.get(f"/v1/companies/{SEED_COMPANY_ID}/locations", headers=headers)
    ).json()
    market = locations[0]
    response = await client.patch(
        f"/v1/companies/{SEED_COMPANY_ID}/locations/{market['id']}",
        json={"name": market["name"], "address": "New Location 42", "timezone": market["timezone"]},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["address"] == "New Location 42"
