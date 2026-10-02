"""Inbound webhook ingestion — Bearer token auth, no user session."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, status

from argus.core.passwords import verify_password
from argus.domain.enums import UserRole
from argus.domain.models import Camera, ContextEvent, Unit, WebhookEndpoint
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

    response: ContextEventResponse | None = None
    async for session in get_db():
        await set_session_context(session, account_id=None, role=UserRole.ROOT.value)
        endpoint = await session.get(WebhookEndpoint, endpoint_id)
        if endpoint is None or not endpoint.active:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook endpoint not found")
        if not verify_password(raw_token, endpoint.token_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

        await set_session_context(
            session, account_id=endpoint.account_id, role=UserRole.MANAGER.value
        )

        unit_id = body.unit_id or endpoint.unit_id
        if unit_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="unit_id required",
            )
        unit = await session.get(Unit, unit_id)
        if unit is None or unit.account_id != endpoint.account_id:
            raise HTTPException(status_code=404, detail="Unit not found")

        camera_id = body.camera_id
        if camera_id is not None:
            camera = await session.get(Camera, camera_id)
            if (
                camera is None
                or camera.account_id != endpoint.account_id
                or camera.unit_id != unit_id
            ):
                raise HTTPException(status_code=404, detail="Camera not found")

        now = datetime.now(UTC)
        event = ContextEvent(
            account_id=endpoint.account_id,
            webhook_id=endpoint.id,
            unit_id=unit_id,
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
                "account_id": str(endpoint.account_id),
                "unit_id": str(unit_id),
                "camera_id": str(camera_id) if camera_id else "",
                "kind": body.kind,
                "payload": body.payload,
                "received_at": now.isoformat(),
                "occurred_at": (body.occurred_at or now).isoformat(),
                "role": body.role,
                **({"confidence": body.confidence} if body.confidence is not None else {}),
                "webhook_id": str(endpoint.id),
                "context_event_id": str(event.id),
            },
        )
        # Do not return inside the loop: get_db() commits after the yield.
        response = ContextEventResponse(
            id=event.id,
            webhook_id=event.webhook_id,
            unit_id=event.unit_id,
            camera_id=event.camera_id,
            kind=event.kind,
            payload=event.payload,
            received_at=event.received_at,
        )

    if response is None:
        raise HTTPException(status_code=500, detail="Database unavailable")
    return response
