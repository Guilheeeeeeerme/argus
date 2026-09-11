"""Inbound webhook hook → ContextEvent."""

from __future__ import annotations

import os
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

os.environ.setdefault("AUTH0_USE_MOCK", "true")
os.environ.setdefault("AUTH0_DOMAIN", "dev.argus.local")

from argus.apps.http import create_admin_app
from argus.config import get_settings
from argus.domain.enums import UserRole
from argus.domain.models import ContextEvent
from argus.services.database import company_session, dispose_engine
from argus.services.redis import close_redis
from tests.conftest import SEED_CAMERA_ID, SEED_COMPANY_ID, SEED_ESTABLISHMENT_ID
from tests.helpers import bearer, session_token

get_settings.cache_clear()


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=create_admin_app())
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    await close_redis()
    await dispose_engine()


async def _manager_headers() -> dict[str, str]:
    return bearer(await session_token(UserRole.MANAGER, SEED_COMPANY_ID))


@pytest.mark.asyncio
async def test_create_webhook_and_ingest_context_event(client: AsyncClient) -> None:
    headers = await _manager_headers()
    created = await client.post(
        f"/v1/companies/{SEED_COMPANY_ID}/webhook-endpoints",
        json={
            "name": f"hook-{uuid.uuid4().hex[:8]}",
            "establishment_id": SEED_ESTABLISHMENT_ID,
            "active": True,
        },
        headers=headers,
    )
    assert created.status_code == 201
    body = created.json()
    endpoint_id = body["id"]
    raw_token = body["token"]
    assert raw_token and raw_token.startswith("whsec_")

    response = await client.post(
        f"/v1/hooks/{endpoint_id}",
        json={
            "kind": "pos.sale",
            "payload": {"amount": 12.5, "sku": "DEMO-1"},
            "establishment_id": SEED_ESTABLISHMENT_ID,
            "camera_id": SEED_CAMERA_ID,
        },
        headers={"Authorization": f"Bearer {raw_token}"},
    )
    assert response.status_code == 202
    event = response.json()
    assert event["webhook_id"] == endpoint_id
    assert event["kind"] == "pos.sale"
    assert event["establishment_id"] == SEED_ESTABLISHMENT_ID
    assert event["camera_id"] == SEED_CAMERA_ID
    assert event["payload"]["sku"] == "DEMO-1"

    async with company_session(
        uuid.UUID(SEED_COMPANY_ID), UserRole.MANAGER.value
    ) as session:
        row = await session.scalar(
            select(ContextEvent).where(ContextEvent.id == uuid.UUID(event["id"]))
        )
        assert row is not None
        assert row.kind == "pos.sale"
        assert row.webhook_id == uuid.UUID(endpoint_id)


@pytest.mark.asyncio
async def test_webhook_rejects_invalid_token(client: AsyncClient) -> None:
    headers = await _manager_headers()
    created = await client.post(
        f"/v1/companies/{SEED_COMPANY_ID}/webhook-endpoints",
        json={"name": f"hook-bad-{uuid.uuid4().hex[:8]}", "active": True},
        headers=headers,
    )
    assert created.status_code == 201
    endpoint_id = created.json()["id"]

    response = await client.post(
        f"/v1/hooks/{endpoint_id}",
        json={
            "kind": "noop",
            "payload": {},
            "establishment_id": SEED_ESTABLISHMENT_ID,
        },
        headers={"Authorization": "Bearer wrong-token"},
    )
    assert response.status_code == 401
