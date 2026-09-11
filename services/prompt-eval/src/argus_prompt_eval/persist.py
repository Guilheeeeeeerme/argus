"""Persist Detection + open TriageCase to Postgres."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from argus_prompt_eval.db import Detection, TriageCase, TriageCaseState
from argus_prompt_eval.evidence_retention import EvidenceClip
from argus_prompt_eval.structured_output import PromptEvalResult


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
