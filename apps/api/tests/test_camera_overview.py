"""GET /v1/companies/{c}/establishments/{e}/cameras/overview — grid tiles with open counts + last frame."""

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
from argus.services.database import company_session, dispose_engine
from argus.services.latest_frames import latest_frame_key
from argus.services.redis import close_redis, get_redis
from tests.conftest import SEED_CAMERA_ID, SEED_COMPANY_ID, SEED_ESTABLISHMENT_ID
from tests.helpers import bearer, session_token

get_settings.cache_clear()

_COMPANY = uuid.UUID(SEED_COMPANY_ID)
_CAMERA = uuid.UUID(SEED_CAMERA_ID)
_ESTABLISHMENT = uuid.UUID(SEED_ESTABLISHMENT_ID)
OVERVIEW = f"/v1/companies/{SEED_COMPANY_ID}/establishments/{SEED_ESTABLISHMENT_ID}/cameras/overview"


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
    async with company_session(_COMPANY, UserRole.MANAGER.value) as session:
        detection = Detection(
            company_id=_COMPANY, camera_id=_CAMERA, establishment_id=_ESTABLISHMENT,
            sequence_id=f"seq-{uuid.uuid4().hex[:8]}", summary="Person in restricted area",
            confidence=0.9, prompt_hits=[], clip_uri="s3://argus-clips/demo/clip.mp4",
            window_started_at=now - timedelta(seconds=30), window_ended_at=now,
        )
        session.add(detection)
        await session.flush()
        case = TriageCase(company_id=_COMPANY, detection_id=detection.id, state=TriageCaseState.OPEN)
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
                 "company_id": SEED_COMPANY_ID, "establishment_id": SEED_ESTABLISHMENT_ID},
    )
    headers = bearer(await session_token(UserRole.OPERATOR, SEED_COMPANY_ID))
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
    headers = bearer(await session_token(UserRole.MANAGER, SEED_COMPANY_ID))
    response = await client.get(OVERVIEW, headers=headers)
    assert response.status_code == 200
    seed = next(tile for tile in response.json() if tile["id"] == SEED_CAMERA_ID)
    assert seed["last_frame_at"] is None


@pytest.mark.asyncio
async def test_overview_cross_company_denied_and_unknown_unit_empty(client: AsyncClient) -> None:
    other = uuid.uuid4()
    denied = await client.get(
        f"/v1/companies/{other}/establishments/{SEED_ESTABLISHMENT_ID}/cameras/overview",
        headers=bearer(await session_token(UserRole.OPERATOR, SEED_COMPANY_ID)),
    )
    assert denied.status_code == 403
    empty = await client.get(
        f"/v1/companies/{SEED_COMPANY_ID}/establishments/{uuid.uuid4()}/cameras/overview",
        headers=bearer(await session_token(UserRole.OPERATOR, SEED_COMPANY_ID)),
    )
    assert empty.status_code == 200
    assert empty.json() == []
