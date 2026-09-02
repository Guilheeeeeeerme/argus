"""Triage decision browsing and resolution routes."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from argus.api.deps import get_tenant_db, require_role
from argus.core.auth import AuthContext
from argus.domain.enums import DecisionState, FeedbackDisposition, UserRole
from argus.domain.models import Decision, Evidence
from argus.domain.schemas.triage import (
    DecisionDetail,
    DecisionSummary,
    EvidenceDetail,
    ResolveDecisionRequest,
    ResolveDecisionResponse,
)
from argus.services.audit import write_audit_record
from argus.services.feedback import create_feedback_with_embedding
from argus.services.storage import generate_presigned_get_url
from argus.services.ws_events import publish_ws_event

router = APIRouter(prefix="/tenants/{tenant_id}/decisions", tags=["triage"])

_DISPOSITION_TO_STATE = {
    FeedbackDisposition.TRUE_POSITIVE: DecisionState.RESOLVED_TRUE_POSITIVE,
    FeedbackDisposition.FALSE_POSITIVE: DecisionState.RESOLVED_FALSE_POSITIVE,
    FeedbackDisposition.FALSE_NEGATIVE: DecisionState.RESOLVED_FALSE_NEGATIVE,
}


@router.get("", response_model=list[DecisionSummary])
async def list_decisions(
    state: str | None = Query(default=None),
    session: AsyncSession = Depends(get_tenant_db),
    _auth: AuthContext = Depends(
        require_role(UserRole.WATCHER, UserRole.TENANT_ADMIN, UserRole.ROOT_ADMIN)
    ),
) -> list[Decision]:
    stmt = select(Decision).order_by(Decision.updated_at.desc())
    if state:
        if state == "resolved":
            stmt = stmt.where(
                Decision.state.in_(
                    [
                        DecisionState.RESOLVED_TRUE_POSITIVE,
                        DecisionState.RESOLVED_FALSE_POSITIVE,
                        DecisionState.RESOLVED_FALSE_NEGATIVE,
                    ]
                )
            )
        else:
            stmt = stmt.where(Decision.state == DecisionState(state))
    return list((await session.scalars(stmt)).all())


@router.get("/{decision_id}", response_model=DecisionDetail)
async def get_decision(
    decision_id: UUID,
    session: AsyncSession = Depends(get_tenant_db),
    _auth: AuthContext = Depends(
        require_role(UserRole.WATCHER, UserRole.TENANT_ADMIN, UserRole.ROOT_ADMIN)
    ),
) -> DecisionDetail:
    decision = await session.scalar(
        select(Decision)
        .where(Decision.id == decision_id)
        .options(selectinload(Decision.evidences))
    )
    if decision is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Decision not found")

    evidence_details: list[EvidenceDetail] = []
    for evidence in decision.evidences:
        playback_url = None
        if evidence.frame_storage_uri.startswith("s3://"):
            key = evidence.frame_storage_uri.split("/", 3)[-1]
            playback_url = await generate_presigned_get_url(key)
        evidence_details.append(
            EvidenceDetail(
                id=evidence.id,
                captured_at=evidence.captured_at,
                severity_score=evidence.severity_score,
                vlm_result=evidence.vlm_result,
                playback_url=playback_url,
            )
        )

    return DecisionDetail(
        id=decision.id,
        camera_id=decision.camera_id,
        region_id=decision.region_id,
        state=decision.state,
        cumulative_severity=decision.cumulative_severity,
        evidence_count=decision.evidence_count,
        window_start=decision.window_start,
        window_end=decision.window_end,
        updated_at=decision.updated_at,
        evidences=evidence_details,
    )


@router.post("/{decision_id}/resolve", response_model=ResolveDecisionResponse)
async def resolve_decision(
    tenant_id: UUID,
    decision_id: UUID,
    body: ResolveDecisionRequest,
    session: AsyncSession = Depends(get_tenant_db),
    auth: AuthContext = Depends(require_role(UserRole.WATCHER, UserRole.TENANT_ADMIN)),
) -> ResolveDecisionResponse:
    decision = await session.get(Decision, decision_id)
    if decision is None or decision.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Decision not found")

    if decision.updated_at != body.updated_at:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Decision was updated by another watcher",
        )

    if decision.state in {
        DecisionState.RESOLVED_TRUE_POSITIVE,
        DecisionState.RESOLVED_FALSE_POSITIVE,
        DecisionState.RESOLVED_FALSE_NEGATIVE,
    }:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Decision already resolved",
        )

    new_state = _DISPOSITION_TO_STATE[body.disposition]
    now = datetime.now(UTC)
    decision.state = new_state
    decision.resolved_at = now
    decision.resolved_by = auth.sub

    await create_feedback_with_embedding(
        session,
        tenant_id=tenant_id,
        decision_id=decision.id,
        disposition=body.disposition,
        reasoning=body.reasoning or body.disposition.value,
        submitted_by=auth.sub,
    )
    await write_audit_record(
        session,
        decision=decision,
        event_type="resolved",
        payload={"disposition": body.disposition.value, "reasoning": body.reasoning},
        actor=auth.sub,
    )
    await session.flush()

    await publish_ws_event(
        tenant_id=tenant_id,
        event_type="decision.resolved",
        payload={
            "decision_id": str(decision.id),
            "state": new_state.value,
            "resolved_by": auth.sub,
            "resolved_at": now.isoformat(),
        },
    )

    return ResolveDecisionResponse(
        decision_id=decision.id,
        state=new_state,
        resolved_at=now,
        resolved_by=auth.sub,
    )


@router.get("/{decision_id}/evidences/{evidence_id}/playback")
async def get_evidence_playback(
    decision_id: UUID,
    evidence_id: UUID,
    session: AsyncSession = Depends(get_tenant_db),
    _auth: AuthContext = Depends(
        require_role(UserRole.WATCHER, UserRole.TENANT_ADMIN, UserRole.ROOT_ADMIN)
    ),
) -> dict[str, str]:
    evidence = await session.get(Evidence, evidence_id)
    if evidence is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found")
    key = evidence.frame_storage_uri.split("/", 3)[-1]
    url = await generate_presigned_get_url(key)
    return {"playback_url": url}
