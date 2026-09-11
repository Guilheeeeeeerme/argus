"""PromptSet CRUD nested under cameras."""

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
from tests.conftest import SEED_CAMERA_ID, SEED_COMPANY_ID
from tests.helpers import bearer, session_token

get_settings.cache_clear()


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=create_admin_app())
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    await close_redis()
    await dispose_engine()


async def _headers() -> dict[str, str]:
    return bearer(await session_token(UserRole.MANAGER, SEED_COMPANY_ID))


@pytest.mark.asyncio
async def test_prompt_set_crud_on_camera(client: AsyncClient) -> None:
    headers = await _headers()
    base = f"/v1/companies/{SEED_COMPANY_ID}"

    created = await client.post(
        f"{base}/cameras/{SEED_CAMERA_ID}/prompt-sets",
        json={
            "name": f"Watchlist {uuid.uuid4().hex[:6]}",
            "prompts": [
                {"text": "Is anyone in the restricted zone?", "enabled": True, "sort_order": 0},
                {"text": "Is a door propped open?", "enabled": True, "sort_order": 1},
            ],
        },
        headers=headers,
    )
    assert created.status_code == 201
    body = created.json()
    prompt_set_id = body["id"]
    assert body["camera_id"] == SEED_CAMERA_ID
    assert len(body["prompts"]) == 2

    listed = await client.get(
        f"{base}/cameras/{SEED_CAMERA_ID}/prompt-sets",
        headers=headers,
    )
    assert listed.status_code == 200
    assert any(row["id"] == prompt_set_id for row in listed.json())

    renamed = await client.patch(
        f"{base}/prompt-sets/{prompt_set_id}",
        json={"name": "Renamed watchlist"},
        headers=headers,
    )
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "Renamed watchlist"

    prompt = await client.post(
        f"{base}/prompt-sets/{prompt_set_id}/prompts",
        json={"text": "Is a vehicle blocking the exit?", "enabled": True, "sort_order": 2},
        headers=headers,
    )
    assert prompt.status_code == 201
    prompt_id = prompt.json()["id"]

    updated_prompt = await client.patch(
        f"{base}/prompts/{prompt_id}",
        json={"enabled": False},
        headers=headers,
    )
    assert updated_prompt.status_code == 200
    assert updated_prompt.json()["enabled"] is False

    deleted = await client.delete(
        f"{base}/prompt-sets/{prompt_set_id}",
        headers=headers,
    )
    assert deleted.status_code == 204

    after = await client.get(
        f"{base}/cameras/{SEED_CAMERA_ID}/prompt-sets",
        headers=headers,
    )
    assert after.status_code == 200
    assert all(row["id"] != prompt_set_id for row in after.json())
