"""WebSocket handshake, heartbeat, and message handling.

Emits/forwards room events including:
- ready / heartbeat
- detection.created
- triage.updated
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from argus.domain.enums import UserRole
from argus.services.sessions import get_session
from argus.services.memberships import has_account_membership
from argus.services.ws_events import EVENT_DETECTION_CREATED, EVENT_TRIAGE_UPDATED
from argus.ws.gateway import manager

logger = logging.getLogger(__name__)
router = APIRouter(tags=["ws"])

# Re-export for OpenAPI / client docs awareness.
WS_EVENT_TYPES = (EVENT_DETECTION_CREATED, EVENT_TRIAGE_UPDATED, "ready", "heartbeat")


@router.websocket("/v1/ws")
async def triage_websocket(websocket: WebSocket, token: str | None = None) -> None:
    if not token:
        await websocket.close(code=4001, reason="Missing token")
        return

    session = await get_session(token)
    if session is None:
        await websocket.close(code=4001, reason="Invalid token")
        return
    if session.role not in {UserRole.MANAGER.value, UserRole.OPERATOR.value}:
        await websocket.close(code=4003, reason="Insufficient role")
        return
    if not session.account_id:
        await websocket.close(code=4003, reason="Missing account_id")
        return

    if not await has_account_membership(session.user_id, session.account_id):
        await websocket.close(code=4003, reason="Account access denied")
        return
    websocket.state.token = token
    account_id = session.account_id
    connected = await manager.connect(websocket, account_id=account_id, sub=session.user_id)
    if not connected:
        await websocket.close(code=4008, reason="Connection limit exceeded")
        return

    await websocket.send_text(
        json.dumps(
            {
                "type": "ready",
                "account_id": account_id,
                "timestamp": datetime.now(UTC).isoformat(),
                "payload": {
                    "role": session.role,
                    "email": session.email,
                    "event_types": list(WS_EVENT_TYPES),
                },
            }
        )
    )

    heartbeat_task = asyncio.create_task(_heartbeat_loop(websocket, account_id))
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if msg.get("type") == "pong":
                continue
            if msg.get("type") == "subscribe":
                payload_tid = msg.get("payload", {}).get("account_id")
                if payload_tid and payload_tid != account_id:
                    await websocket.close(code=4003, reason="Account mismatch")
                    break
    except WebSocketDisconnect:
        pass
    finally:
        heartbeat_task.cancel()
        await manager.disconnect(websocket)


async def _heartbeat_loop(websocket: WebSocket, account_id: str) -> None:
    while True:
        await asyncio.sleep(30)
        envelope = {
            "type": "heartbeat",
            "account_id": account_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "payload": {},
        }
        try:
            await websocket.send_text(json.dumps(envelope))
        except Exception:
            break
