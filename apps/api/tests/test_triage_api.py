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
from argus.services.database import account_session, dispose_engine
from argus.services.redis import close_redis
from tests.conftest import SEED_CAMERA_ID, SEED_ACCOUNT_ID, SEED_UNIT_ID
from tests.helpers import bearer, session_token

get_settings.cache_clear()

_ACCOUNT = uuid.UUID(SEED_ACCOUNT_ID)
_CAMERA = uuid.UUID(SEED_CAMERA_ID)
_UNIT = uuid.UUID(SEED_UNIT_ID)


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
    return await session_token(UserRole.OPERATOR, SEED_ACCOUNT_ID)


async def _seed_open_case() -> tuple[str, str]:
    now = datetime.now(UTC)
    async with account_session(_ACCOUNT, UserRole.MANAGER.value) as session:
        detection = Detection(
            account_id=_ACCOUNT,
            camera_id=_CAMERA,
            unit_id=_UNIT,
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
            account_id=_ACCOUNT,
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
        f"/v1/accounts/{SEED_ACCOUNT_ID}/triage-cases",
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
        f"/v1/accounts/{SEED_ACCOUNT_ID}/triage-cases/{case_id}/resolve",
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
        f"/v1/accounts/{SEED_ACCOUNT_ID}/triage-cases/{case_id}",
        headers=bearer(await _operator_token()),
    )
    assert detail.status_code == 200
    assert detail.json()["state"] == "false_positive"
    assert detail.json()["detection"]["id"] == detection_id


@pytest.mark.asyncio
async def test_list_filters_by_unit_and_camera_with_names(client: AsyncClient) -> None:
    case_id, _ = await _seed_open_case()
    headers = bearer(await _operator_token())
    base = f"/v1/accounts/{SEED_ACCOUNT_ID}/triage-cases"

    by_unit = await client.get(f"{base}?unit_id={SEED_UNIT_ID}&limit=5", headers=headers)
    assert by_unit.status_code == 200
    rows = by_unit.json()
    assert 1 <= len(rows) <= 5
    row = next(r for r in rows if r["id"] == case_id)
    assert row["detection"]["camera_name"]
    assert row["detection"]["unit_name"]
    assert row["detection"]["sequence_id"].startswith("seq-")

    by_camera = await client.get(f"{base}?camera_id={SEED_CAMERA_ID}", headers=headers)
    assert any(r["id"] == case_id for r in by_camera.json())

    none = await client.get(f"{base}?camera_id={uuid.uuid4()}", headers=headers)
    assert none.status_code == 200
    assert none.json() == []

    too_many = await client.get(f"{base}?limit=501", headers=headers)
    assert too_many.status_code == 422
