"""Triage API tests."""

from __future__ import annotations

import os
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

os.environ.setdefault("AUTH0_USE_MOCK", "true")

from argus.apps.http import create_admin_app
from argus.config import get_settings
from argus.domain.enums import DecisionState, UserRole
from argus.domain.models import Decision
from argus.integrations.auth0 import create_mock_token
from argus.services.database import dispose_engine, tenant_session
from argus.services.redis import close_redis, delete_key

get_settings.cache_clear()

SEED_TENANT_ID = "11111111-1111-4111-8111-111111111111"
SEED_CAMERA_ID = "33333333-3333-4333-8333-333333333333"
SEED_REGION_ID = "44444444-4444-4444-8444-444444444444"


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=create_admin_app())
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture(autouse=True)
async def _cleanup():
    yield
    await close_redis()
    await dispose_engine()


def _watcher_token() -> str:
    return create_mock_token(
        sub="auth0|watcher",
        tenant_id=SEED_TENANT_ID,
        role=UserRole.WATCHER.value,
    )


@pytest.mark.asyncio
async def test_list_decisions(client: AsyncClient) -> None:
    response = await client.get(
        f"/v1/tenants/{SEED_TENANT_ID}/decisions",
        headers={"Authorization": f"Bearer {_watcher_token()}"},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_resolve_decision_writes_feedback(client: AsyncClient) -> None:
    async with tenant_session(
        __import__("uuid").UUID(SEED_TENANT_ID),
        UserRole.TENANT_ADMIN.value,
    ) as session:
        decision = Decision(
            tenant_id=__import__("uuid").UUID(SEED_TENANT_ID),
            camera_id=__import__("uuid").UUID(SEED_CAMERA_ID),
            region_id=__import__("uuid").UUID(SEED_REGION_ID),
            state=DecisionState.WARNING,
            cumulative_severity=6,
            evidence_count=3,
            window_start=datetime.now(UTC),
            window_end=datetime.now(UTC),
        )
        session.add(decision)
        await session.flush()
        decision_id = str(decision.id)
        updated_at = decision.updated_at.isoformat()

    response = await client.post(
        f"/v1/tenants/{SEED_TENANT_ID}/decisions/{decision_id}/resolve",
        json={
            "disposition": "false_positive",
            "reasoning": "Shadow from display case, not a person.",
            "updated_at": updated_at,
        },
        headers={"Authorization": f"Bearer {_watcher_token()}"},
    )
    assert response.status_code == 200
    assert response.json()["state"] == "resolved_false_positive"

    open_key = f"decision:open:{SEED_TENANT_ID}:{SEED_CAMERA_ID}:{SEED_REGION_ID}"
    await delete_key(open_key)
