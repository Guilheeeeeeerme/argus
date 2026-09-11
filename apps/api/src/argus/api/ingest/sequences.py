"""Simplified test/back-compat inject path — XADD frames:ready."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, status

from argus.domain.schemas.ingest import InjectAcceptedResponse, InjectFrameReadyRequest
from argus.services.stream import enqueue_frames_ready

router = APIRouter(tags=["ingest"])


@router.post(
    "/ingest/sequences",
    response_model=InjectAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def inject_frames_ready(body: InjectFrameReadyRequest) -> InjectAcceptedResponse:
    """Test inject: publish a frames:ready event (no Celery / Recipe dependency)."""
    now = datetime.now(UTC)
    sequence_id = body.sequence_id or str(uuid4())
    await enqueue_frames_ready(
        {
            "company_id": str(body.company_id),
            "establishment_id": str(body.establishment_id),
            "camera_id": str(body.camera_id),
            "sequence_id": sequence_id,
            "captured_at": (body.captured_at or now).isoformat(),
            "frame_uris": body.frame_uris,
            "preproc_meta": body.preproc_meta,
        }
    )
    return InjectAcceptedResponse(sequence_id=sequence_id, queued_at=now)
