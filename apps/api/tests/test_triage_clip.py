"""Authenticated clip playback without public object-storage access."""
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from argus.api import deps
from argus.api.triage import triage_cases
from argus.core.auth import AuthContext, get_auth_context
from argus.domain.enums import UserRole


@pytest.mark.asyncio
@pytest.mark.parametrize("scenario,expected", [
    ("playback", 200), ("anonymous", 401), ("other_company", 403),
    ("missing_case", 404), ("missing_clip", 404),
])
async def test_clip_requires_session_and_company(monkeypatch, scenario, expected):
    company_id, case_id = uuid4(), uuid4()
    case = SimpleNamespace(detection=SimpleNamespace(clip_uri="s3://private/clips/test.mp4"))
    if scenario == "missing_case":
        case = None
    elif scenario == "missing_clip":
        case.detection.clip_uri = None
    session = SimpleNamespace(scalar=AsyncMock(return_value=case))

    async def db():
        yield session

    app = FastAPI()
    app.include_router(triage_cases.router, prefix="/v1")
    monkeypatch.setattr(deps, "_get_db", db)
    if scenario != "anonymous":
        app.dependency_overrides[get_auth_context] = lambda: AuthContext(
            sub="user", email="operator@example.com", role=UserRole.OPERATOR,
            company_id=uuid4() if scenario == "other_company" else company_id,
            token="opaque-session",
        )
    monkeypatch.setattr(deps, "set_company_context", AsyncMock())
    download = AsyncMock(return_value=(b"\x00\x00\x00\x18ftypmp42", "video/mp4"))
    monkeypatch.setattr(triage_cases, "download_bytes", download)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/v1/companies/{company_id}/triage-cases/{case_id}/clip")
    assert response.status_code == expected
    if expected == 200:
        assert response.content == b"\x00\x00\x00\x18ftypmp42"
        assert response.headers["content-type"] == "video/mp4"
        assert response.headers["cache-control"] == "private, no-store"
        download.assert_awaited_once_with("s3://private/clips/test.mp4")
        # Explicit company constraint supplements RLS, including platform-role requests.
        params = session.scalar.call_args.args[0].compile().params
        assert company_id in params.values()
        assert case_id in params.values()
    else:
        download.assert_not_awaited()


@pytest.mark.asyncio
async def test_detail_returns_authenticated_api_path():
    from datetime import UTC, datetime
    from argus.domain.enums import TriageCaseState

    company_id, case_id, detection_id = uuid4(), uuid4(), uuid4()
    now = datetime.now(UTC)
    detection = SimpleNamespace(
        id=detection_id, camera_id=uuid4(), establishment_id=uuid4(),
        summary="Person visible", confidence=0.9, prompt_hits=[],
        clip_uri="s3://private/clip.mp4", window_started_at=now,
        window_ended_at=now, created_at=now,
    )
    case = SimpleNamespace(
        id=case_id, detection_id=detection_id, state=TriageCaseState.OPEN,
        resolved_at=None, resolved_by=None, updated_at=now, detection=detection,
    )
    result = await triage_cases.get_triage_case(
        company_id, case_id, session=SimpleNamespace(scalar=AsyncMock(return_value=case)),
        _auth=None,
    )
    assert result.clip_playback_url == f"/v1/companies/{company_id}/triage-cases/{case_id}/clip"
