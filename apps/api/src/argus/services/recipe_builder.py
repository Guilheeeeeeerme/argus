"""Recipe prompt construction and RAG feedback retrieval."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from argus.domain.enums import FeedbackDisposition
from argus.domain.models import Decision, Feedback, Recipe, Rule
from argus.guardrails.fencing import fence
from argus.guardrails.registry import render_prompt

RAG_LIMIT = 5


def build_prompt(
    recipe: Recipe,
    rules: list[Rule],
    rag_feedback: list[Feedback],
) -> str:
    """Build the VLM system prompt from the guardrails registry (trusted content only)."""
    rules_block = "\n".join(
        f"- {rule.name}: class={rule.detection_class or 'any'} "
        f"min_confidence={rule.confidence_threshold} "
        f"condition={json_dumps_safe(rule.condition)} (weight={rule.severity_weight})"
        for rule in rules
    ) or "- No explicit rules configured."

    return render_prompt(
        "vlm.system",
        {
            "recipe_system_prompt": recipe.system_prompt.strip(),
            "rules_block": rules_block,
        },
    )


def build_user_context(rag_feedback: list[Feedback]) -> str:
    """Fenced untrusted block (feedback reasoning) for the VLM user message."""
    rag_block = "\n".join(
        f"- FALSE POSITIVE example: {fb.reasoning}"
        for fb in rag_feedback
    ) or "- No prior false-positive feedback for this camera."
    return fence(rag_block)


async def retrieve_rag_feedback(
    session: AsyncSession,
    *,
    company_id: UUID,
    camera_id: UUID,
    query_embedding: list[float] | None = None,
) -> list[Feedback]:
    """Top false-positive feedback rows for company+camera (pgvector when embedding provided)."""
    base = (
        select(Feedback)
        .join(Decision, Feedback.decision_id == Decision.id)
        .where(
            Feedback.company_id == company_id,
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
    detection_class = vlm_result.get("detection_class")
    confidence = vlm_result.get("confidence_score", vlm_result.get("confidence"))
    score = 0
    for rule in rules:
        if rule.detection_class and detection_class != rule.detection_class:
            continue
        if confidence is not None and float(confidence) < float(rule.confidence_threshold):
            continue
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
