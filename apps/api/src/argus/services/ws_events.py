"""WebSocket event publishing helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from argus.services.redis import publish

WS_ROOM_CHANNEL = "ws:room:{account_id}"

EVENT_DETECTION_CREATED = "detection.created"
EVENT_TRIAGE_UPDATED = "triage.updated"


async def publish_ws_event(
    *,
    account_id: UUID,
    event_type: str,
    payload: dict[str, Any],
) -> None:
    envelope = {
        "type": event_type,
        "account_id": str(account_id),
        "timestamp": datetime.now(UTC).isoformat(),
        "payload": payload,
    }
    await publish(WS_ROOM_CHANNEL.format(account_id=account_id), envelope)


async def publish_detection_created(
    *,
    account_id: UUID,
    detection_id: UUID,
    triage_case_id: UUID,
    payload: dict[str, Any] | None = None,
) -> None:
    body = {
        "detection_id": str(detection_id),
        "triage_case_id": str(triage_case_id),
        **(payload or {}),
    }
    await publish_ws_event(
        account_id=account_id,
        event_type=EVENT_DETECTION_CREATED,
        payload=body,
    )


async def publish_triage_updated(
    *,
    account_id: UUID,
    triage_case_id: UUID,
    payload: dict[str, Any] | None = None,
) -> None:
    body = {"triage_case_id": str(triage_case_id), **(payload or {})}
    await publish_ws_event(
        account_id=account_id,
        event_type=EVENT_TRIAGE_UPDATED,
        payload=body,
    )
