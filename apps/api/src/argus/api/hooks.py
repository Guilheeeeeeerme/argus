"""Inbound webhook ingestion — Bearer token auth, no user session."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, status

from argus.core.passwords import verify_password
from argus.domain.enums import UserRole
from argus.domain.models import Camera, ContextEvent, Establishment, WebhookEndpoint
from argus.domain.schemas.admin import ContextEventResponse, InboundWebhookRequest
from argus.services.database import get_db, set_session_context
from argus.services.redis import xadd

router = APIRouter(prefix="/v1/hooks", tags=["inbound-webhooks"])

CONTEXT_EVENTS_STREAM = "context:events"


@router.post("/{endpoint_id}", response_model=ContextEventResponse, status_code=status.HTTP_202_ACCEPTED)
async def ingest_webhook(
    endpoint_id: UUID,
    body: InboundWebhookRequest,
    authorization: str | None = Header(default=None),
) -> ContextEventResponse:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    raw_token = authorization.split(" ", 1)[1].strip()
    if not raw_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")

    async for session in get_db():
        await set_session_context(session, company_id=None, role=UserRole.ROOT.value)
        endpoint = await session.get(WebhookEndpoint, endpoint_id)
        if endpoint is None or not endpoint.active:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook endpoint not found")
        if not verify_password(raw_token, endpoint.token_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

        await set_session_context(
            session, company_id=endpoint.company_id, role=UserRole.MANAGER.value
        )

        establishment_id = body.establishment_id or endpoint.establishment_id
        if establishment_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="establishment_id required",
            )
        establishment = await session.get(Establishment, establishment_id)
        if establishment is None or establishment.company_id != endpoint.company_id:
            raise HTTPException(status_code=404, detail="Establishment not found")

        camera_id = body.camera_id
        if camera_id is not None:
            camera = await session.get(Camera, camera_id)
            if (
                camera is None
                or camera.company_id != endpoint.company_id
                or camera.establishment_id != establishment_id
            ):
                raise HTTPException(status_code=404, detail="Camera not found")

        now = datetime.now(UTC)
        event = ContextEvent(
            company_id=endpoint.company_id,
            webhook_id=endpoint.id,
            establishment_id=establishment_id,
            camera_id=camera_id,
            kind=body.kind,
            payload=body.payload,
            received_at=now,
        )
        session.add(event)
        await session.flush()

        await xadd(
            CONTEXT_EVENTS_STREAM,
            {
                "company_id": str(endpoint.company_id),
                "establishment_id": str(establishment_id),
                "camera_id": str(camera_id) if camera_id else "",
                "kind": body.kind,
                "payload": body.payload,
                "received_at": now.isoformat(),
                "webhook_id": str(endpoint.id),
                "context_event_id": str(event.id),
            },
        )
        return ContextEventResponse(
            id=event.id,
            webhook_id=event.webhook_id,
            establishment_id=event.establishment_id,
            camera_id=event.camera_id,
            kind=event.kind,
            payload=event.payload,
            received_at=event.received_at,
        )

    raise HTTPException(status_code=500, detail="Database unavailable")
