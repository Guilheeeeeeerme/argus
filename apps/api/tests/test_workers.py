"""Worker pipeline integration tests."""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from sqlalchemy import select

os.environ.setdefault("AUTH0_USE_MOCK", "true")

from argus.domain.enums import DecisionState, UserRole  # noqa: E402
from argus.domain.models import Decision, Evidence, Recipe  # noqa: E402
from argus.integrations.openai_vlm import MockVLMClient  # noqa: E402
from argus.services.aggregation import AggregationService  # noqa: E402
from argus.services.database import dispose_engine, company_session  # noqa: E402
from argus.services.redis import close_redis, delete_key, get_redis  # noqa: E402
from argus.workers import vlm_analyzer  # noqa: E402
from argus.workers.utils import run_async  # noqa: E402

SEED_COMPANY_ID = uuid.UUID("11111111-1111-4111-8111-111111111111")
SEED_CAMERA_ID = uuid.UUID("33333333-3333-4333-8333-333333333333")
SEED_MODE_ID = uuid.UUID("55555555-5555-4555-8555-555555555555")
SEED_REGION_ID = uuid.UUID("44444444-4444-4444-8444-444444444444")


@pytest_asyncio.fixture(autouse=True)
async def _cleanup():
    yield
    await close_redis()
    await dispose_engine()


@pytest.fixture
def mock_vlm() -> MockVLMClient:
    client = MockVLMClient(
        {
            "is_suspicious": True,
            "confidence_score": 0.95,
            "reasoning": "Person lingering near checkout.",
            "severity_hint": 3,
        }
    )
    vlm_analyzer.set_vlm_client(client)
    return client


@pytest.mark.asyncio
async def test_vlm_analyze_creates_evidence(mock_vlm: MockVLMClient) -> None:
    ingestion_id = uuid.uuid4()
    fields = {
        "ingestion_id": str(ingestion_id),
        "company_id": str(SEED_COMPANY_ID),
        "camera_id": str(SEED_CAMERA_ID),
        "captured_at": datetime.now(UTC).isoformat(),
        "rule_set_id": str(SEED_MODE_ID),
        "region_id": str(SEED_REGION_ID),
        "frame_uris": '["s3://argus-frames/test/frame0.bin"]',
        "edge_trigger_metadata": "{}",
    }

    evidence_id = await vlm_analyzer._analyze_message("test-msg-1", fields)
    assert evidence_id

    async with company_session(SEED_COMPANY_ID, UserRole.MANAGER.value) as session:
        evidence = await session.get(Evidence, uuid.UUID(evidence_id))
        assert evidence is not None
        assert evidence.ingestion_id == ingestion_id
        assert evidence.vlm_result["is_suspicious"] is True
        assert evidence.severity_score >= 1

    assert mock_vlm.calls
    assert "NEVER identify individuals" in mock_vlm.calls[0]["system_prompt"]


@pytest_asyncio.fixture
async def clean_open_decision():
    key = f"decision:open:{SEED_COMPANY_ID}:{SEED_CAMERA_ID}:{SEED_REGION_ID}"
    await delete_key(key)
    yield
    await delete_key(key)


@pytest.mark.asyncio
async def test_aggregator_groups_evidences_into_decision(
    clean_open_decision,
) -> None:
    service = AggregationService()
    base_time = datetime.now(UTC)
    evidence_ids: list[uuid.UUID] = []

    async with company_session(SEED_COMPANY_ID, UserRole.MANAGER.value) as session:
        for idx in range(3):
            evidence = Evidence(
                company_id=SEED_COMPANY_ID,
                camera_id=SEED_CAMERA_ID,
                region_id=SEED_REGION_ID,
                rule_set_id=SEED_MODE_ID,
                captured_at=base_time + timedelta(seconds=idx * 10),
                vlm_result={"is_suspicious": True, "severity_hint": 2},
                severity_score=2,
                frame_storage_uri=f"s3://argus-frames/test/{idx}.bin",
                ingestion_id=uuid.uuid4(),
            )
            session.add(evidence)
            await session.flush()
            evidence_ids.append(evidence.id)

    decision_id: uuid.UUID | None = None
    for eid in evidence_ids:
        decision = await service.aggregate(eid)
        decision_id = decision.id

    assert decision_id is not None
    async with company_session(SEED_COMPANY_ID, UserRole.MANAGER.value) as session:
        decision = await session.get(Decision, decision_id)
        assert decision is not None
        assert decision.evidence_count == 3
        assert decision.cumulative_severity == 6
        assert decision.state in {DecisionState.WEIRD, DecisionState.WARNING}


@pytest.mark.asyncio
async def test_out_of_order_evidence_merges_into_same_decision(
    clean_open_decision,
) -> None:
    service = AggregationService()
    t0 = datetime.now(UTC)
    t1 = t0 + timedelta(minutes=1)
    t3 = t0 + timedelta(minutes=3)

    async with company_session(SEED_COMPANY_ID, UserRole.MANAGER.value) as session:
        ids: list[uuid.UUID] = []
        for captured_at in (t3, t1):
            evidence = Evidence(
                company_id=SEED_COMPANY_ID,
                camera_id=SEED_CAMERA_ID,
                region_id=SEED_REGION_ID,
                rule_set_id=SEED_MODE_ID,
                captured_at=captured_at,
                vlm_result={"is_suspicious": True},
                severity_score=1,
                frame_storage_uri="s3://argus-frames/test/late.bin",
                ingestion_id=uuid.uuid4(),
            )
            session.add(evidence)
            await session.flush()
            ids.append(evidence.id)

    d1 = await service.aggregate(ids[0])
    d2 = await service.aggregate(ids[1])
    assert d1.id == d2.id
    assert d2.evidence_count == 2
