"""Persist Detection + open TriageCase to Postgres."""

from __future__ import annotations

from datetime import datetime
from hashlib import sha256
from typing import Any
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from argus_prompt_eval.db import Detection, TriageCase, TriageCaseState
from argus_prompt_eval.evidence_retention import EvidenceClip
from argus_prompt_eval.structured_output import PromptEvalResult


async def find_positive(
    session: AsyncSession, *, company_id: UUID, camera_id: UUID, sequence_id: str
) -> tuple[Detection, TriageCase] | None:
    """Serialize a sequence and reuse a committed positive on stream redelivery.

    The transaction-scoped lock covers evaluation and persistence in the caller,
    so reclaiming a slow in-flight message cannot create a second detection.
    """
    key = f"prompt-eval:{company_id}:{camera_id}:{sequence_id}"
    lock_id = int.from_bytes(sha256(key.encode()).digest()[:8], "big", signed=True)
    await session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": lock_id})
    rows = await session.execute(
        select(Detection, TriageCase)
        .join(TriageCase, TriageCase.detection_id == Detection.id)
        .where(
            Detection.company_id == company_id,
            Detection.camera_id == camera_id,
            Detection.sequence_id == sequence_id,
            TriageCase.company_id == company_id,
        )
        .limit(1)
    )
    row = rows.first()
    return (row[0], row[1]) if row is not None else None


async def persist_positive(
    session: AsyncSession,
    *,
    company_id: UUID,
    establishment_id: UUID,
    camera_id: UUID,
    sequence_id: str,
    result: PromptEvalResult,
    evidence: EvidenceClip,
    captured_at: datetime | None = None,
) -> tuple[Detection, TriageCase]:
    del captured_at  # window bounds come from evidence retention
    matched = [h for h in result.prompt_hits if h.matched]
    confidence = max((h.confidence for h in matched), default=0.0)
    prompt_hits: list[dict[str, Any]] = [
        h.model_dump() for h in result.prompt_hits if h.matched
    ]

    detection = Detection(
        company_id=company_id,
        establishment_id=establishment_id,
        camera_id=camera_id,
        sequence_id=sequence_id,
        prompt_hits=prompt_hits,
        confidence=confidence,
        summary=result.summary or "Positive prompt match",
        clip_uri=evidence.clip_uri,
        frame_uris=list(evidence.frame_uris),
        window_started_at=evidence.window.start,
        window_ended_at=evidence.window.end,
    )
    session.add(detection)
    await session.flush()

    triage = TriageCase(
        company_id=company_id,
        detection_id=detection.id,
        state=TriageCaseState.OPEN,
    )
    session.add(triage)
    await session.flush()
    return detection, triage
