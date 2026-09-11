"""RAG (pgvector) — retrieve prior false-positive feedback for grounding.

AI Engineering pattern: RAG (pgvector).
Joins Feedback → TriageCase → Detection to optionally scope by camera.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from argus_prompt_eval.config import settings
from argus_prompt_eval.db import Detection, Feedback, FeedbackDisposition, TriageCase


async def retrieve_fp_feedback(
    session: AsyncSession,
    *,
    company_id: UUID,
    camera_id: UUID | None = None,
    query_embedding: list[float] | None = None,
    limit: int | None = None,
) -> list[Feedback]:
    """Top false-positive feedback rows (cosine distance when embedding given)."""
    cap = limit if limit is not None else settings.rag_limit
    stmt = (
        select(Feedback)
        .join(TriageCase, Feedback.triage_case_id == TriageCase.id)
        .join(Detection, TriageCase.detection_id == Detection.id)
        .where(
            Feedback.company_id == company_id,
            Feedback.disposition == FeedbackDisposition.FALSE_POSITIVE,
        )
    )
    if camera_id is not None:
        stmt = stmt.where(Detection.camera_id == camera_id)

    if query_embedding is not None:
        stmt = (
            stmt.where(Feedback.embedding.is_not(None))
            .order_by(Feedback.embedding.cosine_distance(query_embedding))
            .limit(cap)
        )
    else:
        stmt = stmt.order_by(Feedback.created_at.desc()).limit(cap)

    result = await session.scalars(stmt)
    return list(result.all())
