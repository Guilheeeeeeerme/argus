"""Lens builder and RAG retrieval tests."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from argus.domain.enums import FeedbackDisposition, UserRole
from argus.domain.models import Decision, Feedback, Lens, Rule
from argus.integrations.openai_vlm import BIOMETRICS_PROHIBITION
from argus.services.database import dispose_engine, tenant_session
from argus.services.lens_builder import build_prompt, retrieve_rag_feedback

SEED_TENANT_ID = uuid.UUID("11111111-1111-4111-8111-111111111111")
SEED_CAMERA_ID = uuid.UUID("33333333-3333-4333-8333-333333333333")


@pytest.fixture
def sample_lens() -> Lens:
    return Lens(
        tenant_id=SEED_TENANT_ID,
        context_mode_id=uuid.uuid4(),
        name="Test Lens",
        system_prompt="Monitor suspicious shelf activity.",
        output_schema={"type": "object"},
    )


def test_build_prompt_includes_biometrics_prohibition(sample_lens: Lens) -> None:
    rules = [
        Rule(
            tenant_id=SEED_TENANT_ID,
            context_mode_id=sample_lens.context_mode_id,
            name="Tamper",
            condition={"field": "suspicious", "op": "eq", "value": True},
            severity_weight=2,
        )
    ]
    prompt = build_prompt(sample_lens, rules, [])
    assert BIOMETRICS_PROHIBITION in prompt
    assert "Tamper" in prompt


@pytest.mark.asyncio
async def test_retrieve_rag_feedback_returns_false_positives() -> None:
    async with tenant_session(SEED_TENANT_ID, UserRole.TENANT_ADMIN.value) as session:
        decision = Decision(
            tenant_id=SEED_TENANT_ID,
            camera_id=SEED_CAMERA_ID,
            region_id=None,
            window_start=datetime.now(UTC),
            window_end=datetime.now(UTC),
        )
        session.add(decision)
        await session.flush()
        session.add(
            Feedback(
                tenant_id=SEED_TENANT_ID,
                decision_id=decision.id,
                disposition=FeedbackDisposition.FALSE_POSITIVE,
                reasoning="Shadow looked like a person.",
                submitted_by="watcher@test",
            )
        )
        await session.commit()

    async with tenant_session(SEED_TENANT_ID, UserRole.TENANT_ADMIN.value) as session:
        rows = await retrieve_rag_feedback(
            session,
            tenant_id=SEED_TENANT_ID,
            camera_id=SEED_CAMERA_ID,
        )
        assert rows
        assert "Shadow" in rows[0].reasoning

    await dispose_engine()
