"""Triage case browsing and resolution routes."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from argus.api.deps import get_company_db, require_role
from argus.core.auth import AuthContext
from argus.domain.enums import FeedbackDisposition, TriageCaseState, UserRole
from argus.domain.models import Camera, Detection, Establishment, TriageCase
from argus.domain.schemas.triage import (
    DetectionSummary,
    ResolveTriageCaseRequest,
    ResolveTriageCaseResponse,
    TriageCaseDetail,
    TriageCaseSummary,
)
from argus.services.feedback import create_feedback_with_embedding
from argus.services.storage import download_bytes
from argus.services.ws_events import publish_ws_event
from argus.services.audit import write_audit_record

router = APIRouter(prefix="/companies/{company_id}/triage-cases", tags=["triage"])

_DISPOSITION_TO_STATE = {
    "confirmed": TriageCaseState.CONFIRMED,
    "dismissed": TriageCaseState.DISMISSED,
    "false_positive": TriageCaseState.FALSE_POSITIVE,
}


async def _resolve_names(
    session: AsyncSession, detections: list[Detection]
) -> tuple[dict[UUID, str], dict[UUID, str]]:
    """Camera and establishment names for a page of detections in two ``IN`` queries (no N+1)."""
    camera_ids = {d.camera_id for d in detections}
    establishment_ids = {d.establishment_id for d in detections}
    camera_names: dict[UUID, str] = {}
    establishment_names: dict[UUID, str] = {}
    if camera_ids:
        rows = await session.execute(select(Camera.id, Camera.name).where(Camera.id.in_(camera_ids)))
        camera_names = dict(rows.all())
    if establishment_ids:
        rows = await session.execute(
            select(Establishment.id, Establishment.name).where(Establishment.id.in_(establishment_ids))
        )
        establishment_names = dict(rows.all())
    return camera_names, establishment_names


def _detection_summary(
    detection: Detection | None,
    camera_names: dict[UUID, str] | None = None,
    establishment_names: dict[UUID, str] | None = None,
) -> DetectionSummary | None:
    if detection is None:
        return None
    return DetectionSummary(
        id=detection.id,
        camera_id=detection.camera_id,
        establishment_id=detection.establishment_id,
        camera_name=(camera_names or {}).get(detection.camera_id),
        establishment_name=(establishment_names or {}).get(detection.establishment_id),
        sequence_id=getattr(detection, "sequence_id", None),
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
    establishment_id: UUID | None = Query(default=None),
    camera_id: UUID | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    session: AsyncSession = Depends(get_company_db),
    _auth: AuthContext = Depends(
        require_role(UserRole.OPERATOR, UserRole.MANAGER, UserRole.ROOT, UserRole.ADMIN)
    ),
) -> list[TriageCaseSummary]:
    stmt = (
        select(TriageCase)
        .options(selectinload(TriageCase.detection))
        .order_by(TriageCase.updated_at.desc())
        .limit(limit)
    )
    if state:
        stmt = stmt.where(TriageCase.state == TriageCaseState(state))
    if establishment_id is not None or camera_id is not None:
        stmt = stmt.join(Detection, Detection.id == TriageCase.detection_id)
        if establishment_id is not None:
            stmt = stmt.where(Detection.establishment_id == establishment_id)
        if camera_id is not None:
            stmt = stmt.where(Detection.camera_id == camera_id)
    rows = list((await session.scalars(stmt)).all())
    camera_names, establishment_names = await _resolve_names(
        session, [case.detection for case in rows if case.detection is not None]
    )
    return [
        TriageCaseSummary(
            id=case.id,
            detection_id=case.detection_id,
            state=case.state,
            resolved_at=case.resolved_at,
            resolved_by=case.resolved_by,
            updated_at=case.updated_at,
            detection=_detection_summary(case.detection, camera_names, establishment_names),
        )
        for case in rows
    ]


@router.get("/{triage_case_id}", response_model=TriageCaseDetail)
async def get_triage_case(
    company_id: UUID,
    triage_case_id: UUID,
    session: AsyncSession = Depends(get_company_db),
    _auth: AuthContext = Depends(
        require_role(UserRole.OPERATOR, UserRole.MANAGER, UserRole.ROOT, UserRole.ADMIN)
    ),
) -> TriageCaseDetail:
    case = await session.scalar(
        select(TriageCase)
        .where(TriageCase.id == triage_case_id, TriageCase.company_id == company_id)
        .options(selectinload(TriageCase.detection))
    )
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Triage case not found")

    clip_playback_url = None
    detection = case.detection
    if detection is not None and detection.clip_uri and detection.clip_uri.startswith("s3://"):
        clip_playback_url = f"/v1/companies/{company_id}/triage-cases/{triage_case_id}/clip"
    camera_names, establishment_names = await _resolve_names(
        session, [detection] if detection is not None else []
    )

    return TriageCaseDetail(
        id=case.id,
        detection_id=case.detection_id,
        state=case.state,
        resolved_at=case.resolved_at,
        resolved_by=case.resolved_by,
        updated_at=case.updated_at,
        detection=_detection_summary(detection, camera_names, establishment_names),
        clip_playback_url=clip_playback_url,
    )


@router.get("/{triage_case_id}/clip")
async def get_triage_clip(
    company_id: UUID,
    triage_case_id: UUID,
    session: AsyncSession = Depends(get_company_db),
    _auth: AuthContext = Depends(
        require_role(UserRole.OPERATOR, UserRole.MANAGER, UserRole.ROOT, UserRole.ADMIN)
    ),
) -> Response:
    case = await session.scalar(
        select(TriageCase)
        .where(TriageCase.id == triage_case_id, TriageCase.company_id == company_id)
        .options(selectinload(TriageCase.detection))
    )
    if case is None or case.detection is None or not case.detection.clip_uri:
        raise HTTPException(status_code=404, detail="Evidence clip not found")
    try:
        payload, content_type = await download_bytes(case.detection.clip_uri)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Evidence clip not found") from exc
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code")
        if code in {"NoSuchKey", "NoSuchBucket", "404"}:
            raise HTTPException(status_code=404, detail="Evidence clip not found") from exc
        raise HTTPException(status_code=502, detail="Evidence storage unavailable") from exc
    return Response(
        content=payload,
        media_type=content_type,
        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
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
