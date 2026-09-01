"""WebSocket event publishing helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from argus.services.redis import publish

WS_ROOM_CHANNEL = "ws:room:{tenant_id}"


async def publish_ws_event(
    *,
    tenant_id: UUID,
    event_type: str,
    payload: dict[str, Any],
) -> None:
    envelope = {
        "type": event_type,
        "tenant_id": str(tenant_id),
        "timestamp": datetime.now(UTC).isoformat(),
        "payload": payload,
    }
    await publish(WS_ROOM_CHANNEL.format(tenant_id=tenant_id), envelope)
