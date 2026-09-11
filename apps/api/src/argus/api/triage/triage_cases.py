"""Triage case browsing and resolution routes."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from argus.api.deps import get_company_db, require_role
from argus.core.auth import AuthContext
from argus.domain.enums import FeedbackDisposition, TriageCaseState, UserRole
from argus.domain.models import Detection, TriageCase
from argus.domain.schemas.triage import (
    DetectionSummary,
    ResolveTriageCaseRequest,
    ResolveTriageCaseResponse,
    TriageCaseDetail,
    TriageCaseSummary,
)
from argus.services.feedback import create_feedback_with_embedding
from argus.services.storage import generate_presigned_get_url
from argus.services.ws_events import publish_ws_event
from argus.services.audit import write_audit_record

router = APIRouter(prefix="/companies/{company_id}/triage-cases", tags=["triage"])

_DISPOSITION_TO_STATE = {
    "confirmed": TriageCaseState.CONFIRMED,
    "dismissed": TriageCaseState.DISMISSED,
    "false_positive": TriageCaseState.FALSE_POSITIVE,
}


def _detection_summary(detection: Detection | None) -> DetectionSummary | None:
    if detection is None:
        return None
    return DetectionSummary(
        id=detection.id,
        camera_id=detection.camera_id,
        establishment_id=detection.establishment_id,
        summary=detection.summary,
        confidence=float(detection.confidence) if detection.confidence is not None else None,
        prompt_hits=list(detection.prompt_hits or []),
        clip_uri=detection.clip_uri,
        window_started_at=detection.window_started_at,
        window_ended_at=detection.window_ended_at,
        created_at=getattr(detection, "created_at", None),
    )


@router.get("", response_model=list[TriageCaseSummary])
async def list_open_triage_cases(
    state: str | None = Query(default="open"),
    session: AsyncSession = Depends(get_company_db),
    _auth: AuthContext = Depends(
        require_role(UserRole.OPERATOR, UserRole.MANAGER, UserRole.ROOT, UserRole.ADMIN)
    ),
) -> list[TriageCaseSummary]:
    stmt = (
        select(TriageCase)
        .options(selectinload(TriageCase.detection))
        .order_by(TriageCase.updated_at.desc())
    )
    if state:
        stmt = stmt.where(TriageCase.state == TriageCaseState(state))
    rows = list((await session.scalars(stmt)).all())
    return [
        TriageCaseSummary(
            id=case.id,
            detection_id=case.detection_id,
            state=case.state,
            resolved_at=case.resolved_at,
            resolved_by=case.resolved_by,
            updated_at=case.updated_at,
            detection=_detection_summary(case.detection),
        )
        for case in rows
    ]


@router.get("/{triage_case_id}", response_model=TriageCaseDetail)
async def get_triage_case(
    triage_case_id: UUID,
    session: AsyncSession = Depends(get_company_db),
    _auth: AuthContext = Depends(
        require_role(UserRole.OPERATOR, UserRole.MANAGER, UserRole.ROOT, UserRole.ADMIN)
    ),
) -> TriageCaseDetail:
    case = await session.scalar(
        select(TriageCase)
        .where(TriageCase.id == triage_case_id)
        .options(selectinload(TriageCase.detection))
    )
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Triage case not found")

    clip_playback_url = None
    detection = case.detection
    if detection is not None and detection.clip_uri and detection.clip_uri.startswith("s3://"):
        key = detection.clip_uri.split("/", 3)[-1]
        clip_playback_url = await generate_presigned_get_url(key)

    return TriageCaseDetail(
        id=case.id,
        detection_id=case.detection_id,
        state=case.state,
        resolved_at=case.resolved_at,
        resolved_by=case.resolved_by,
        updated_at=case.updated_at,
        detection=_detection_summary(detection),
        clip_playback_url=clip_playback_url,
    )


@router.post("/{triage_case_id}/resolve", response_model=ResolveTriageCaseResponse)
async def resolve_triage_case(
    company_id: UUID,
    triage_case_id: UUID,
    body: ResolveTriageCaseRequest,
    session: AsyncSession = Depends(get_company_db),
    auth: AuthContext = Depends(require_role(UserRole.OPERATOR, UserRole.MANAGER)),
) -> ResolveTriageCaseResponse:
    case = await session.get(TriageCase, triage_case_id)
    if case is None or case.company_id != company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Triage case not found")

    if case.state != TriageCaseState.OPEN:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Triage case already resolved",
        )

    new_state = _DISPOSITION_TO_STATE[body.disposition]
    now = datetime.now(UTC)
    case.state = new_state
    case.resolved_at = now
    case.resolved_by = auth.sub

    if body.disposition == "false_positive":
        await create_feedback_with_embedding(
            session,
            company_id=company_id,
            triage_case_id=case.id,
            disposition=FeedbackDisposition.FALSE_POSITIVE,
            reasoning=body.reasoning or body.disposition,
            submitted_by=auth.sub,
        )

    await write_audit_record(
        session,
        company_id=company_id,
        triage_case_id=case.id,
        event_type="triage.resolved",
        payload={"disposition": body.disposition, "reasoning": body.reasoning},
        actor=auth.sub,
    )

    await session.flush()

    await publish_ws_event(
        company_id=company_id,
        event_type="triage.updated",
        payload={
            "triage_case_id": str(case.id),
            "detection_id": str(case.detection_id),
            "state": new_state.value,
            "resolved_by": auth.sub,
            "resolved_at": now.isoformat(),
        },
    )

    return ResolveTriageCaseResponse(
        triage_case_id=case.id,
        state=new_state,
        resolved_at=now,
        resolved_by=auth.sub,
    )
