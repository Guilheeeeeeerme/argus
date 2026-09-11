"""Triage API tests — TriageCase + Detection."""

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
from argus.services.redis import close_redis
from tests.conftest import SEED_CAMERA_ID, SEED_COMPANY_ID, SEED_ESTABLISHMENT_ID
from tests.helpers import bearer, session_token

get_settings.cache_clear()

_COMPANY = uuid.UUID(SEED_COMPANY_ID)
_CAMERA = uuid.UUID(SEED_CAMERA_ID)
_ESTABLISHMENT = uuid.UUID(SEED_ESTABLISHMENT_ID)


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


async def _operator_token() -> str:
    return await session_token(UserRole.OPERATOR, SEED_COMPANY_ID)


async def _seed_open_case() -> tuple[str, str]:
    now = datetime.now(UTC)
    async with company_session(_COMPANY, UserRole.MANAGER.value) as session:
        detection = Detection(
            company_id=_COMPANY,
            camera_id=_CAMERA,
            establishment_id=_ESTABLISHMENT,
            sequence_id=f"seq-{uuid.uuid4().hex[:8]}",
            summary="Person in restricted area",
            confidence=0.91,
            prompt_hits=[
                {
                    "prompt_id": str(uuid.uuid4()),
                    "matched": True,
                    "confidence": 0.91,
                    "rationale": "visible intrusion",
                }
            ],
            clip_uri="s3://argus-clips/demo/clip.mp4",
            window_started_at=now - timedelta(seconds=30),
            window_ended_at=now,
            frame_uris=["s3://argus-frames/demo/0.bin"],
        )
        session.add(detection)
        await session.flush()
        case = TriageCase(
            company_id=_COMPANY,
            detection_id=detection.id,
            state=TriageCaseState.OPEN,
        )
        session.add(case)
        await session.flush()
        return str(case.id), str(detection.id)


@pytest.mark.asyncio
async def test_list_triage_cases(client: AsyncClient) -> None:
    await _seed_open_case()
    response = await client.get(
        f"/v1/companies/{SEED_COMPANY_ID}/triage-cases",
        headers=bearer(await _operator_token()),
    )
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert any(row.get("state") == "open" for row in body)


@pytest.mark.asyncio
async def test_resolve_triage_case_writes_feedback(client: AsyncClient) -> None:
    case_id, detection_id = await _seed_open_case()
    response = await client.post(
        f"/v1/companies/{SEED_COMPANY_ID}/triage-cases/{case_id}/resolve",
        json={
            "disposition": "false_positive",
            "reasoning": "Shadow from display case, not a person.",
        },
        headers=bearer(await _operator_token()),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["triage_case_id"] == case_id
    assert body["state"] == "false_positive"

    detail = await client.get(
        f"/v1/companies/{SEED_COMPANY_ID}/triage-cases/{case_id}",
        headers=bearer(await _operator_token()),
    )
    assert detail.status_code == 200
    assert detail.json()["state"] == "false_positive"
    assert detail.json()["detection"]["id"] == detection_id
