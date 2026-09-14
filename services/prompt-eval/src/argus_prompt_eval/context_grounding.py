"""Context grounding — merge ContextEvents + RAG feedback into eval context.

AI Engineering pattern: Context grounding.
Untrusted text is screened then fenced before inclusion in the VLM user message.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from argus_prompt_eval.config import settings
from argus_prompt_eval.db import ContextEvent, Feedback
from argus_prompt_eval.guardrails import fence, is_blocked, neutralize, screen
from argus_prompt_eval.rag import retrieve_fp_feedback
from argus_prompt_eval.temporal_window import ensure_aware

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GroundedContext:
    events: list[ContextEvent]
    feedback: list[Feedback]
    user_context: str
    blocked_policy: str | None = None


async def load_recent_context_events(
    session: AsyncSession,
    *,
    company_id: UUID,
    establishment_id: UUID,
    camera_id: UUID | None = None,
    lookback_seconds: int | None = None,
) -> list[ContextEvent]:
    lookback = lookback_seconds if lookback_seconds is not None else settings.context_lookback_seconds
    since = datetime.now(UTC) - timedelta(seconds=lookback)
    conditions = [
        ContextEvent.company_id == company_id,
        or_(
            ContextEvent.establishment_id.is_(None),
            ContextEvent.establishment_id == establishment_id,
        ),
        ContextEvent.received_at >= since,
    ]
    if camera_id is not None:
        conditions.append(
            or_(ContextEvent.camera_id.is_(None), ContextEvent.camera_id == camera_id)
        )
    stmt = (
        select(ContextEvent)
        .where(*conditions)
        .order_by(ContextEvent.received_at.desc())
        .limit(50)
    )
    result = await session.scalars(stmt)
    return list(result.all())


def _format_events(events: list[ContextEvent]) -> str:
    if not events:
        return "- No recent context events."
    lines: list[str] = []
    for event in events:
        received = ensure_aware(event.received_at).isoformat()
        payload = json.dumps(event.payload, default=str)[:500]
        cam = str(event.camera_id) if event.camera_id else "establishment"
        lines.append(f"- [{received}] kind={event.kind} scope={cam} payload={payload}")
    return "\n".join(lines)


def _format_feedback(feedback: list[Feedback]) -> str:
    if not feedback:
        return "- No prior false-positive feedback."
    return "\n".join(f"- FALSE POSITIVE example: {fb.reasoning}" for fb in feedback)


async def ground_context(
    session: AsyncSession,
    *,
    company_id: UUID,
    establishment_id: UUID,
    camera_id: UUID,
    query_embedding: list[float] | None = None,
) -> GroundedContext:
    """Load recent events + RAG FP feedback; screen then fence for the VLM."""
    events = await load_recent_context_events(
        session,
        company_id=company_id,
        establishment_id=establishment_id,
        camera_id=camera_id,
    )
    feedback = await retrieve_fp_feedback(
        session,
        company_id=company_id,
        camera_id=camera_id,
        query_embedding=query_embedding,
    )

    # Neutralize before screening so invisible-character obfuscation cannot
    # carry a payload past the policy patterns (LLM01 encoding axis).
    raw_block = neutralize(
        "Context events:\n"
        f"{_format_events(events)}\n"
        "Prior operator feedback:\n"
        f"{_format_feedback(feedback)}"
    )
    hits = screen(raw_block)
    blocked = next((h.policy_id for h in hits if h.action == "block"), None)
    if blocked is not None or is_blocked(raw_block):
        logger.warning("Grounding context blocked by policy %s", blocked)
        return GroundedContext(
            events=events,
            feedback=feedback,
            user_context="",
            blocked_policy=blocked or "unknown",
        )

    return GroundedContext(
        events=events,
        feedback=feedback,
        user_context=fence(raw_block),
        blocked_policy=None,
    )
