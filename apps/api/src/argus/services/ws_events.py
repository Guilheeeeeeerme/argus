"""WebSocket event publishing helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from argus.services.redis import publish

WS_ROOM_CHANNEL = "ws:room:{company_id}"


async def publish_ws_event(
    *,
    company_id: UUID,
    event_type: str,
    payload: dict[str, Any],
) -> None:
    envelope = {
        "type": event_type,
        "company_id": str(company_id),
        "timestamp": datetime.now(UTC).isoformat(),
        "payload": payload,
    }
    await publish(WS_ROOM_CHANNEL.format(company_id=company_id), envelope)
