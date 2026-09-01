"""Ingestion API tests — auth, validation, Redis Stream enqueue."""

from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("AUTH0_USE_MOCK", "true")
os.environ.setdefault("AUTH0_DOMAIN", "dev.argus.local")

from argus.apps.http import create_ingest_app  # noqa: E402
from argus.config import get_settings  # noqa: E402
from argus.domain.enums import UserRole  # noqa: E402
from argus.integrations.auth0 import create_mock_m2m_token, create_mock_token  # noqa: E402
from argus.services.redis import close_redis, delete_key, get_redis  # noqa: E402
from argus.services.stream import INGEST_STREAM  # noqa: E402

get_settings.cache_clear()

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "sample_ingest_payload.json"
SEED_TENANT_ID = "11111111-1111-4111-8111-111111111111"
SEED_CAMERA_ID = "33333333-3333-4333-8333-333333333333"
SEED_MODE_ID = "55555555-5555-4555-8555-555555555555"


@pytest_asyncio.fixture(autouse=True)
async def _reset_redis_client():
    await close_redis()
    yield
    await close_redis()


@pytest_asyncio.fixture
async def client() -> AsyncClient:
    transport = ASGITransport(app=create_ingest_app())
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def sample_payload() -> dict:
    return json.loads(FIXTURE_PATH.read_text())


@pytest.fixture
def m2m_token() -> str:
    return create_mock_m2m_token(
        sub="edge-device-demo-001@clients",
        tenant_id=SEED_TENANT_ID,
        camera_id=SEED_CAMERA_ID,
    )


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def active_camera_mode():
    key = f"camera:active_mode:{SEED_CAMERA_ID}"
    await get_redis().set(key, SEED_MODE_ID)
    yield
    await delete_key(key)


@pytest.mark.asyncio
async def test_valid_payload_writes_to_redis_stream(
    client: AsyncClient,
    sample_payload: dict,
    m2m_token: str,
    active_camera_mode,
) -> None:
    ingestion_id = str(uuid.uuid4())
    payload = {**sample_payload, "ingestion_id": ingestion_id}

    start = time.perf_counter()
    response = await client.post(
        "/v1/ingest/sequences",
        json=payload,
        headers=_auth_headers(m2m_token),
    )
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "queued"
    assert body["ingestion_id"] == ingestion_id
    assert elapsed_ms < 500

    entries = await get_redis().xrevrange(INGEST_STREAM, count=1)
    assert entries
    _msg_id, fields = entries[0]
    assert fields["ingestion_id"] == ingestion_id
    assert fields["tenant_id"] == SEED_TENANT_ID
    assert fields["camera_id"] == SEED_CAMERA_ID


@pytest.mark.asyncio
async def test_invalid_token_rejected(
    client: AsyncClient,
    sample_payload: dict,
) -> None:
    response = await client.post(
        "/v1/ingest/sequences",
        json=sample_payload,
        headers={"Authorization": "Bearer not-a-valid-token"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_sso_token_rejected(
    client: AsyncClient,
    sample_payload: dict,
) -> None:
    sso_token = create_mock_token(
        sub="auth0|watcher",
        tenant_id=SEED_TENANT_ID,
        role=UserRole.WATCHER.value,
        camera_id=SEED_CAMERA_ID,
    )
    response = await client.post(
        "/v1/ingest/sequences",
        json=sample_payload,
        headers=_auth_headers(sso_token),
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_claim_mismatch_returns_422(
    client: AsyncClient,
    sample_payload: dict,
    m2m_token: str,
    active_camera_mode,
) -> None:
    payload = {
        **sample_payload,
        "ingestion_id": str(uuid.uuid4()),
        "tenant_id": str(uuid.uuid4()),
    }
    response = await client.post(
        "/v1/ingest/sequences",
        json=payload,
        headers=_auth_headers(m2m_token),
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_duplicate_ingestion_returns_409(
    client: AsyncClient,
    sample_payload: dict,
    m2m_token: str,
    active_camera_mode,
) -> None:
    ingestion_id = str(uuid.uuid4())
    payload = {**sample_payload, "ingestion_id": ingestion_id}
    headers = _auth_headers(m2m_token)

    first = await client.post("/v1/ingest/sequences", json=payload, headers=headers)
    second = await client.post("/v1/ingest/sequences", json=payload, headers=headers)

    assert first.status_code == 202
    assert second.status_code == 409
    assert second.json()["status"] == "duplicate"


@pytest.mark.asyncio
async def test_no_active_mode_returns_400(
    client: AsyncClient,
    sample_payload: dict,
    m2m_token: str,
) -> None:
    payload = {**sample_payload, "ingestion_id": str(uuid.uuid4())}
    response = await client.post(
        "/v1/ingest/sequences",
        json=payload,
        headers=_auth_headers(m2m_token),
    )
    assert response.status_code == 400
    assert "active context mode" in response.json()["error"]["message"].lower()
