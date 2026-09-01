"""Lens prompt construction and RAG feedback retrieval."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from argus.domain.enums import FeedbackDisposition
from argus.domain.models import Decision, Feedback, Lens, Rule
from argus.integrations.openai_vlm import BIOMETRICS_PROHIBITION

RAG_LIMIT = 5


def build_prompt(
    lens: Lens,
    rules: list[Rule],
    rag_feedback: list[Feedback],
) -> str:
    """Build VLM system prompt with rules, RAG examples, and biometrics constraint."""
    rules_block = "\n".join(
        f"- {rule.name}: {json_dumps_safe(rule.condition)} (weight={rule.severity_weight})"
        for rule in rules
    ) or "- No explicit rules configured."

    rag_block = "\n".join(
        f"- FALSE POSITIVE example: {fb.reasoning}"
        for fb in rag_feedback
    ) or "- No prior false-positive feedback for this camera."

    return (
        f"{lens.system_prompt.strip()}\n\n"
        f"Rules to evaluate:\n{rules_block}\n\n"
        f"Historical false-positive feedback (avoid repeating these mistakes):\n{rag_block}\n\n"
        f"Constraint: {BIOMETRICS_PROHIBITION} or infer biometric attributes.\n"
        "Respond in JSON with fields including is_suspicious, confidence_score, reasoning."
    )


async def retrieve_rag_feedback(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    camera_id: UUID,
    query_embedding: list[float] | None = None,
) -> list[Feedback]:
    """Top false-positive feedback rows for tenant+camera (pgvector when embedding provided)."""
    base = (
        select(Feedback)
        .join(Decision, Feedback.decision_id == Decision.id)
        .where(
            Feedback.tenant_id == tenant_id,
            Decision.camera_id == camera_id,
            Feedback.disposition == FeedbackDisposition.FALSE_POSITIVE,
        )
    )

    if query_embedding is not None:
        stmt = (
            base.where(Feedback.embedding.is_not(None))
            .order_by(Feedback.embedding.cosine_distance(query_embedding))
            .limit(RAG_LIMIT)
        )
    else:
        stmt = base.order_by(Feedback.created_at.desc()).limit(RAG_LIMIT)

    result = await session.scalars(stmt)
    return list(result.all())


def compute_severity_score(vlm_result: dict[str, Any], rules: list[Rule]) -> int:
    score = 0
    for rule in rules:
        if _matches_condition(rule.condition, vlm_result):
            score += rule.severity_weight
    if score == 0 and vlm_result.get("is_suspicious"):
        hint = vlm_result.get("severity_hint") or vlm_result.get("confidence_score", 1)
        if isinstance(hint, float):
            score = max(1, int(hint * 3))
        else:
            score = int(hint)
    return score


def _matches_condition(condition: dict[str, Any], vlm_result: dict[str, Any]) -> bool:
    field = condition.get("field")
    op = condition.get("op")
    expected = condition.get("value")
    if field == "suspicious":
        actual = vlm_result.get("is_suspicious")
    else:
        actual = vlm_result.get(field)
    if op == "eq":
        return actual == expected
    if op == "gte":
        return actual is not None and actual >= expected
    return False


def json_dumps_safe(value: Any) -> str:
    import json

    return json.dumps(value, default=str)
