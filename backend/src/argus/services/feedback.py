"""Feedback persistence and embedding generation for RAG loop."""

from __future__ import annotations

import hashlib
import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from argus.config import settings
from argus.domain.enums import FeedbackDisposition
from argus.domain.models import Feedback

logger = logging.getLogger(__name__)
EMBEDDING_DIM = 1536


async def create_feedback_with_embedding(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    decision_id: UUID,
    disposition: FeedbackDisposition,
    reasoning: str,
    submitted_by: str,
) -> Feedback:
    embedding = await generate_embedding(reasoning)
    feedback = Feedback(
        tenant_id=tenant_id,
        decision_id=decision_id,
        disposition=disposition,
        reasoning=reasoning,
        submitted_by=submitted_by,
        embedding=embedding,
    )
    session.add(feedback)
    await session.flush()
    return feedback


async def generate_embedding(text: str) -> list[float]:
    if settings.openai_api_key:
        try:
            from openai import OpenAI

            client = OpenAI(api_key=settings.openai_api_key)
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
