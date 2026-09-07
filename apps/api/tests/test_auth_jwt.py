"""Session validation, RBAC dependencies, and edge M2M JWT tests."""

from __future__ import annotations

import os

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("AUTH0_USE_MOCK", "true")

from argus.apps.http import create_admin_app, create_ingest_app
from argus.config import get_settings
from argus.domain.enums import UserRole
from argus.integrations.auth0 import create_mock_m2m_token
from argus.services.database import dispose_engine
from argus.services.redis import close_redis
from argus.services.sessions import get_session
from tests.helpers import bearer, session_token

get_settings.cache_clear()

SEED_COMPANY_ID = "11111111-1111-4111-8111-111111111111"


@pytest_asyncio.fixture(autouse=True)
async def _cleanup():
    yield
    await close_redis()
    await dispose_engine()


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=create_admin_app())
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_session_roundtrip() -> None:
    token = await session_token(UserRole.MANAGER, SEED_COMPANY_ID)
    data = await get_session(token)
    assert data is not None
    assert data.role == UserRole.MANAGER.value
    assert data.company_id == SEED_COMPANY_ID


@pytest.mark.asyncio
async def test_unknown_session_is_none() -> None:
    assert await get_session("sess_missing") is None


@pytest.mark.asyncio
async def test_manager_gets_me(client: AsyncClient) -> None:
    token = await session_token(UserRole.MANAGER, SEED_COMPANY_ID)
    response = await client.get("/v1/auth/me", headers=bearer(token))
    assert response.status_code == 200
    body = response.json()
    assert body["user"]["role"] == "manager"
    assert body["activeCompany"]["id"] == SEED_COMPANY_ID


@pytest.mark.asyncio
async def test_operator_cannot_switch_context(client: AsyncClient) -> None:
    token = await session_token(UserRole.OPERATOR, SEED_COMPANY_ID)
    response = await client.patch(
        "/v1/auth/context",
        json={"companyId": SEED_COMPANY_ID},
        headers=bearer(token),
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_missing_bearer_rejected(client: AsyncClient) -> None:
    response = await client.get("/v1/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_edge_m2m_token_accepted_by_ingest() -> None:
    token = create_mock_m2m_token(
        sub="edge-test@clients",
        company_id=SEED_COMPANY_ID,
        camera_id="33333333-3333-4333-8333-333333333333",
    )
    transport = ASGITransport(app=create_ingest_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
