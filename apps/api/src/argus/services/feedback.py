"""Feedback persistence and embedding generation for RAG loop."""

from __future__ import annotations

import hashlib
import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from argus.config import settings
from argus.domain.enums import FeedbackDisposition
from argus.domain.models import Feedback
from argus.guardrails.screening import is_blocked

logger = logging.getLogger(__name__)
EMBEDDING_DIM = 1536


async def create_feedback_with_embedding(
    session: AsyncSession,
    *,
    company_id: UUID,
    triage_case_id: UUID,
    disposition: FeedbackDisposition,
    reasoning: str,
    submitted_by: str | None = None,
) -> Feedback:
    # Screen at write so poisoned text is never embedded into the RAG store.
    if is_blocked(reasoning):
        raise ValueError("feedback_blocked_by_policy")
    embedding = await generate_embedding(reasoning)
    feedback = Feedback(
        company_id=company_id,
        triage_case_id=triage_case_id,
        disposition=disposition,
        reasoning=reasoning,
        embedding=embedding,
    )
    session.add(feedback)
    await session.flush()
    if submitted_by:
        logger.info(
            "feedback created triage_case_id=%s by=%s disposition=%s",
            triage_case_id,
            submitted_by,
            disposition.value,
        )
    return feedback


async def generate_embedding(text: str) -> list[float]:
    if settings.openai_api_key:
        try:
            from openai import OpenAI

            client = OpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url or None)
            response = client.embeddings.create(
                model="text-embedding-3-small",
                input=text,
            )
            return list(response.data[0].embedding)
        except Exception:
            logger.exception("OpenAI embedding failed; using deterministic fallback")

    digest = hashlib.sha256(text.encode()).digest()
    vec = [((digest[i % len(digest)] / 255.0) * 2 - 1) for i in range(EMBEDDING_DIM)]
    return vec
