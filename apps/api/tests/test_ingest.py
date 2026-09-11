"""Ingestion inject path — frames:ready enqueue (MVP)."""

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
from argus.services.redis import close_redis, get_redis  # noqa: E402
from argus.services.stream import FRAMES_READY_STREAM  # noqa: E402

get_settings.cache_clear()

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "sample_ingest_payload.json"
SEED_COMPANY_ID = "11111111-1111-4111-8111-111111111111"
SEED_ESTABLISHMENT_ID = "22222222-2222-4222-8222-222222222222"
SEED_CAMERA_ID = "33333333-3333-4333-8333-333333333333"


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


@pytest.mark.asyncio
async def test_valid_payload_writes_to_redis_stream(
    client: AsyncClient,
    sample_payload: dict,
) -> None:
    sequence_id = f"seq-{uuid.uuid4().hex[:8]}"
    payload = {**sample_payload, "sequence_id": sequence_id}

    start = time.perf_counter()
    response = await client.post("/v1/ingest/sequences", json=payload)
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "queued"
    assert body["sequence_id"] == sequence_id
    assert elapsed_ms < 500

    entries = await get_redis().xrevrange(FRAMES_READY_STREAM, count=1)
    assert entries
    _msg_id, fields = entries[0]
    assert fields["sequence_id"] == sequence_id
    assert fields["company_id"] == SEED_COMPANY_ID
    assert fields["establishment_id"] == SEED_ESTABLISHMENT_ID
    assert fields["camera_id"] == SEED_CAMERA_ID


@pytest.mark.asyncio
async def test_missing_required_fields_rejected(client: AsyncClient) -> None:
    response = await client.post(
        "/v1/ingest/sequences",
        json={"company_id": SEED_COMPANY_ID},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_auto_sequence_id_when_omitted(
    client: AsyncClient,
    sample_payload: dict,
) -> None:
    payload = {k: v for k, v in sample_payload.items() if k != "sequence_id"}
    response = await client.post("/v1/ingest/sequences", json=payload)
    assert response.status_code == 202
    assert response.json()["sequence_id"]
