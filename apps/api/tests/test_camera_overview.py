"""GET /v1/accounts/{c}/units/{e}/cameras/overview — grid tiles with open counts + last frame."""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("AUTH0_USE_MOCK", "true")

from argus.apps.http import create_admin_app
from argus.config import get_settings
from argus.domain.enums import TriageCaseState, UserRole
from argus.domain.models import Detection, TriageCase
from argus.services.database import account_session, dispose_engine
from argus.services.latest_frames import latest_frame_key
from argus.services.redis import close_redis, get_redis
from tests.conftest import SEED_CAMERA_ID, SEED_ACCOUNT_ID, SEED_UNIT_ID
from tests.helpers import bearer, session_token

get_settings.cache_clear()

_ACCOUNT = uuid.UUID(SEED_ACCOUNT_ID)
_CAMERA = uuid.UUID(SEED_CAMERA_ID)
_UNIT = uuid.UUID(SEED_UNIT_ID)
OVERVIEW = f"/v1/accounts/{SEED_ACCOUNT_ID}/units/{SEED_UNIT_ID}/cameras/overview"


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=create_admin_app())
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    await get_redis().delete(latest_frame_key(_CAMERA))
    await close_redis()
    await dispose_engine()


async def _seed_open_case() -> str:
    now = datetime.now(UTC)
    async with account_session(_ACCOUNT, UserRole.MANAGER.value) as session:
        detection = Detection(
            account_id=_ACCOUNT, camera_id=_CAMERA, unit_id=_UNIT,
            sequence_id=f"seq-{uuid.uuid4().hex[:8]}", summary="Person in restricted area",
            confidence=0.9, prompt_hits=[], clip_uri="s3://argus-clips/demo/clip.mp4",
            window_started_at=now - timedelta(seconds=30), window_ended_at=now,
        )
        session.add(detection)
        await session.flush()
        case = TriageCase(account_id=_ACCOUNT, detection_id=detection.id, state=TriageCaseState.OPEN)
        session.add(case)
        await session.flush()
        return str(case.id)


@pytest.mark.asyncio
async def test_overview_counts_open_cases_and_reads_latest_frame(client: AsyncClient) -> None:
    await _seed_open_case()
    captured_at = "2026-10-02T12:00:00+00:00"
    await get_redis().hset(
        latest_frame_key(_CAMERA),
        mapping={"uri": "s3://argus-frames/x/latest.jpg", "captured_at": captured_at,
                 "account_id": SEED_ACCOUNT_ID, "unit_id": SEED_UNIT_ID},
    )
    headers = bearer(await session_token(UserRole.OPERATOR, SEED_ACCOUNT_ID))
    response = await client.get(OVERVIEW, headers=headers)
    assert response.status_code == 200
    tiles = response.json()
    names = [tile["name"] for tile in tiles]
    assert names == sorted(names)
    seed = next(tile for tile in tiles if tile["id"] == SEED_CAMERA_ID)
    assert seed["open_case_count"] >= 1
    assert seed["is_active"] is True
    assert datetime.fromisoformat(seed["last_frame_at"]) == datetime.fromisoformat(captured_at)


@pytest.mark.asyncio
async def test_overview_without_frame_pointer_has_null_last_frame(client: AsyncClient) -> None:
    await get_redis().delete(latest_frame_key(_CAMERA))
    headers = bearer(await session_token(UserRole.MANAGER, SEED_ACCOUNT_ID))
    response = await client.get(OVERVIEW, headers=headers)
    assert response.status_code == 200
    seed = next(tile for tile in response.json() if tile["id"] == SEED_CAMERA_ID)
    assert seed["last_frame_at"] is None


@pytest.mark.asyncio
async def test_overview_cross_account_denied_and_unknown_unit_empty(client: AsyncClient) -> None:
    other = uuid.uuid4()
    denied = await client.get(
        f"/v1/accounts/{other}/units/{SEED_UNIT_ID}/cameras/overview",
        headers=bearer(await session_token(UserRole.OPERATOR, SEED_ACCOUNT_ID)),
    )
    assert denied.status_code == 403
    empty = await client.get(
        f"/v1/accounts/{SEED_ACCOUNT_ID}/units/{uuid.uuid4()}/cameras/overview",
        headers=bearer(await session_token(UserRole.OPERATOR, SEED_ACCOUNT_ID)),
    )
    assert empty.status_code == 200
    assert empty.json() == []
