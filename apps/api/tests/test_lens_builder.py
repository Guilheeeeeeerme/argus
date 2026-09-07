"""Recipe builder and RAG retrieval tests."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from argus.domain.enums import FeedbackDisposition, UserRole
from argus.domain.models import Decision, Feedback, Recipe, Rule
from argus.integrations.openai_vlm import BIOMETRICS_PROHIBITION
from argus.services.database import dispose_engine, company_session
from argus.services.recipe_builder import build_prompt, compute_severity_score, retrieve_rag_feedback

SEED_COMPANY_ID = uuid.UUID("11111111-1111-4111-8111-111111111111")
SEED_CAMERA_ID = uuid.UUID("33333333-3333-4333-8333-333333333333")


@pytest.fixture
def sample_recipe() -> Recipe:
    return Recipe(
        company_id=SEED_COMPANY_ID,
        rule_set_id=uuid.uuid4(),
        name="Test Recipe",
        system_prompt="Monitor suspicious shelf activity.",
        output_schema={"type": "object"},
    )


def test_build_prompt_includes_biometrics_prohibition(sample_recipe: Recipe) -> None:
    rules = [
        Rule(
            company_id=SEED_COMPANY_ID,
            rule_set_id=sample_recipe.rule_set_id,
            name="Tamper",
            condition={"field": "suspicious", "op": "eq", "value": True},
            severity_weight=2,
        )
    ]
    prompt = build_prompt(sample_recipe, rules, [])
    assert BIOMETRICS_PROHIBITION in prompt
    assert "Tamper" in prompt


@pytest.mark.asyncio
async def test_retrieve_rag_feedback_returns_false_positives() -> None:
    async with company_session(SEED_COMPANY_ID, UserRole.MANAGER.value) as session:
        decision = Decision(
            company_id=SEED_COMPANY_ID,
            camera_id=SEED_CAMERA_ID,
            region_id=None,
            window_start=datetime.now(UTC),
            window_end=datetime.now(UTC),
        )
        session.add(decision)
        await session.flush()
        session.add(
            Feedback(
                company_id=SEED_COMPANY_ID,
                decision_id=decision.id,
                disposition=FeedbackDisposition.FALSE_POSITIVE,
                reasoning="Shadow looked like a person.",
                submitted_by="watcher@test",
            )
        )
        await session.commit()

    async with company_session(SEED_COMPANY_ID, UserRole.MANAGER.value) as session:
        rows = await retrieve_rag_feedback(
            session,
            company_id=SEED_COMPANY_ID,
            camera_id=SEED_CAMERA_ID,
        )
        assert rows
        assert "Shadow" in rows[0].reasoning

    await dispose_engine()


def _rule(detection_class: str | None, threshold: float) -> Rule:
    return Rule(
        company_id=SEED_COMPANY_ID,
        rule_set_id=uuid.uuid4(),
        name="Tamper",
        detection_class=detection_class,
        confidence_threshold=threshold,
        condition={"field": "suspicious", "op": "eq", "value": True},
        severity_weight=2,
    )


def test_rule_matches_on_class_and_confidence() -> None:
    rule = _rule("shelf_tamper", 0.600)
    matched = compute_severity_score(
        {"is_suspicious": True, "detection_class": "shelf_tamper", "confidence_score": 0.9},
        [rule],
    )
    assert matched == 2


def test_rule_rejects_wrong_class() -> None:
    rule = _rule("shelf_tamper", 0.600)
    assert compute_severity_score(
        {"is_suspicious": True, "detection_class": "loitering", "confidence_score": 0.9},
        [rule],
    ) == 0


def test_rule_rejects_low_confidence() -> None:
    rule = _rule("shelf_tamper", 0.600)
    assert compute_severity_score(
        {"is_suspicious": True, "detection_class": "shelf_tamper", "confidence_score": 0.4},
        [rule],
    ) == 0


def test_rule_with_null_class_matches_any_detection() -> None:
    rule = _rule(None, 0.500)
    assert compute_severity_score(
        {"is_suspicious": True, "detection_class": "loitering", "confidence_score": 0.7},
        [rule],
    ) == 2
