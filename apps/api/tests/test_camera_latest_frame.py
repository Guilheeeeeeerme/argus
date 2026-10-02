"""GET /v1/accounts/{c}/cameras/{cam}/latest-frame — authenticated proxy with ETag/304."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from botocore.exceptions import ClientError
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from argus.api import deps
from argus.api.triage import cameras
from argus.core.auth import AuthContext, get_auth_context
from argus.domain.enums import UserRole
from argus.services.latest_frames import LatestFrame

CAPTURED = "2026-10-02T12:00:00+00:00"


def _app(monkeypatch, *, account_id, auth_account=None, camera_owned=True, frame, download):
    session = SimpleNamespace(scalar=AsyncMock(return_value=uuid4() if camera_owned else None))

    async def db():
        yield session

    app = FastAPI()
    app.include_router(cameras.router, prefix="/v1")
    monkeypatch.setattr(deps, "_get_db", db)
    monkeypatch.setattr(deps, "set_account_context", AsyncMock())
    if auth_account is not None:
        app.dependency_overrides[get_auth_context] = lambda: AuthContext(
            sub="user", email="operator@example.com", role=UserRole.OPERATOR,
            account_id=auth_account, token="opaque-session",
        )
    monkeypatch.setattr(cameras, "get_latest_frame", AsyncMock(return_value=frame))
    monkeypatch.setattr(cameras, "download_bytes", download)
    return app


@pytest.mark.asyncio
async def test_latest_frame_returns_jpeg_with_etag(monkeypatch):
    account_id, camera_id = uuid4(), uuid4()
    frame = LatestFrame(camera_id=str(camera_id), uri="s3://frames/t/e/c/latest.jpg", captured_at=CAPTURED,
                        account_id=str(account_id), unit_id="e")
    download = AsyncMock(return_value=(b"\xff\xd8\xff", "image/jpeg"))
    app = _app(monkeypatch, account_id=account_id, auth_account=account_id, frame=frame, download=download)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/v1/accounts/{account_id}/cameras/{camera_id}/latest-frame")
        assert response.status_code == 200
        assert response.content == b"\xff\xd8\xff"
        assert response.headers["content-type"] == "image/jpeg"
        assert response.headers["etag"] == f'W/"{CAPTURED}"'
        assert response.headers["cache-control"] == "private, no-store"
        assert response.headers["x-captured-at"] == CAPTURED

        cached = await client.get(
            f"/v1/accounts/{account_id}/cameras/{camera_id}/latest-frame",
            headers={"If-None-Match": f'W/"{CAPTURED}"'},
        )
    assert cached.status_code == 304
    assert cached.headers["etag"] == f'W/"{CAPTURED}"'
    download.assert_awaited_once_with("s3://frames/t/e/c/latest.jpg")


@pytest.mark.asyncio
@pytest.mark.parametrize("scenario,expected", [
    ("anonymous", 401), ("other_account", 403), ("camera_not_owned", 404),
    ("no_hash", 404), ("hash_account_mismatch", 404), ("storage_missing", 404), ("storage_down", 502),
])
async def test_latest_frame_error_paths(monkeypatch, scenario, expected):
    account_id, camera_id = uuid4(), uuid4()
    frame = LatestFrame(camera_id=str(camera_id), uri="s3://frames/x/latest.jpg", captured_at=CAPTURED,
                        account_id=str(account_id), unit_id="e")
    if scenario == "no_hash":
        frame = None
    elif scenario == "hash_account_mismatch":
        frame = LatestFrame(camera_id=str(camera_id), uri=frame.uri, captured_at=CAPTURED,
                            account_id=str(uuid4()), unit_id="e")
    download = AsyncMock(return_value=(b"jpeg", "image/jpeg"))
    if scenario == "storage_missing":
        download = AsyncMock(side_effect=ClientError({"Error": {"Code": "NoSuchKey"}}, "GetObject"))
    elif scenario == "storage_down":
        download = AsyncMock(side_effect=ClientError({"Error": {"Code": "InternalError"}}, "GetObject"))
    auth_account = None if scenario == "anonymous" else uuid4() if scenario == "other_account" else account_id
    app = _app(
        monkeypatch, account_id=account_id, auth_account=auth_account,
        camera_owned=scenario != "camera_not_owned", frame=frame, download=download,
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/v1/accounts/{account_id}/cameras/{camera_id}/latest-frame")
    assert response.status_code == expected
    if scenario in {"anonymous", "other_account", "camera_not_owned", "no_hash", "hash_account_mismatch"}:
        download.assert_not_awaited()
