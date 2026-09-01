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
from argus.integrations.auth0 import create_mock_token
from argus.services.database import dispose_engine
from argus.services.redis import close_redis

get_settings.cache_clear()

SEED_TENANT_ID = "11111111-1111-4111-8111-111111111111"


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=create_admin_app())
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    await close_redis()
    await dispose_engine()


def _token(role: UserRole, tenant_id: str | None = SEED_TENANT_ID) -> str:
    return create_mock_token(
        sub=f"auth0|{role.value}",
        tenant_id=tenant_id or "",
        role=role.value,
    )


@pytest.mark.asyncio
async def test_root_admin_lists_tenants(client: AsyncClient) -> None:
    response = await client.get(
        "/v1/admin/tenants",
        headers={"Authorization": f"Bearer {_token(UserRole.ROOT_ADMIN, '')}"},
    )
    assert response.status_code == 200
    assert any(t["slug"] == "demo-retail" for t in response.json())


@pytest.mark.asyncio
async def test_tenant_admin_cannot_create_tenant(client: AsyncClient) -> None:
    response = await client.post(
        "/v1/admin/tenants",
        json={"name": "Blocked", "slug": "blocked"},
        headers={"Authorization": f"Bearer {_token(UserRole.TENANT_ADMIN)}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_cross_tenant_access_denied(client: AsyncClient) -> None:
    other = str(uuid.uuid4())
    response = await client.get(
        f"/v1/tenants/{other}/markets",
        headers={"Authorization": f"Bearer {_token(UserRole.TENANT_ADMIN)}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_tenant_admin_lists_markets(client: AsyncClient) -> None:
    response = await client.get(
        f"/v1/tenants/{SEED_TENANT_ID}/markets",
        headers={"Authorization": f"Bearer {_token(UserRole.TENANT_ADMIN)}"},
    )
    assert response.status_code == 200
    assert len(response.json()) >= 1
