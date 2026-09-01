"""WebSocket connection manager with per-sub connection limits."""

from __future__ import annotations

import asyncio
import json
from collections import defaultdict

from fastapi import WebSocket
from starlette.websockets import WebSocketState

MAX_CONNECTIONS_PER_SUB = 5


class ConnectionManager:
    def __init__(self) -> None:
        self._rooms: dict[str, set[WebSocket]] = defaultdict(set)
        self._subs: dict[str, int] = defaultdict(int)
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, *, tenant_id: str, sub: str) -> bool:
        async with self._lock:
            if self._subs[sub] >= MAX_CONNECTIONS_PER_SUB:
                return False
            await websocket.accept()
            self._rooms[tenant_id].add(websocket)
            self._subs[sub] += 1
            websocket.state.tenant_id = tenant_id
            websocket.state.sub = sub
            return True

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            tenant_id = getattr(websocket.state, "tenant_id", None)
            sub = getattr(websocket.state, "sub", None)
            if tenant_id and websocket in self._rooms[tenant_id]:
                self._rooms[tenant_id].remove(websocket)
            if sub and self._subs[sub] > 0:
                self._subs[sub] -= 1

    async def broadcast(self, tenant_id: str, message: dict) -> None:
        payload = json.dumps(message)
        dead: list[WebSocket] = []
        for ws in list(self._rooms.get(tenant_id, set())):
            if ws.client_state != WebSocketState.CONNECTED:
                dead.append(ws)
                continue
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            await self.disconnect(ws)


manager = ConnectionManager()
