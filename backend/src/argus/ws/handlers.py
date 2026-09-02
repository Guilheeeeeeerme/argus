"""WebSocket handshake, heartbeat, and message handling."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime

import jwt
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from argus.core.auth import _auth_context_from_token
from argus.domain.enums import UserRole
from argus.integrations.auth0 import validate_jwt
from argus.ws.gateway import manager

logger = logging.getLogger(__name__)
router = APIRouter(tags=["ws"])


@router.websocket("/v1/ws")
async def triage_websocket(websocket: WebSocket, token: str | None = None) -> None:
    if not token:
        await websocket.close(code=4001, reason="Missing token")
        return

    try:
        claims = validate_jwt(token)
        role = claims.get("role")
        if role not in {UserRole.WATCHER.value, UserRole.TENANT_ADMIN.value}:
            await websocket.close(code=4003, reason="Insufficient role")
            return
        auth = _auth_context_from_token(token)
        if auth.tenant_id is None:
            await websocket.close(code=4003, reason="Missing tenant_id")
            return
    except jwt.InvalidTokenError:
        await websocket.close(code=4001, reason="Invalid token")
        return

    tenant_id = str(auth.tenant_id)
    connected = await manager.connect(websocket, tenant_id=tenant_id, sub=auth.sub)
    if not connected:
        await websocket.close(code=4008, reason="Connection limit exceeded")
        return

    heartbeat_task = asyncio.create_task(_heartbeat_loop(websocket, tenant_id))
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
                payload_tid = msg.get("payload", {}).get("tenant_id")
                if payload_tid and payload_tid != tenant_id:
                    await websocket.close(code=4003, reason="Tenant mismatch")
                    break
    except WebSocketDisconnect:
        pass
    finally:
        heartbeat_task.cancel()
        await manager.disconnect(websocket)


async def _heartbeat_loop(websocket: WebSocket, tenant_id: str) -> None:
    while True:
        await asyncio.sleep(30)
        envelope = {
            "type": "heartbeat",
            "tenant_id": tenant_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "payload": {},
        }
        try:
            await websocket.send_text(json.dumps(envelope))
        except Exception:
            break
