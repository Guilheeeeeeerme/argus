"""WebSocket gateway tests."""

from __future__ import annotations

import os

import pytest
from httpx import ASGITransport, AsyncClient
from starlette.testclient import TestClient

os.environ.setdefault("AUTH0_USE_MOCK", "true")

from argus.apps.http import create_ws_app
from argus.config import get_settings
from argus.domain.enums import UserRole
from argus.integrations.auth0 import create_mock_token
from argus.ws.gateway import manager

get_settings.cache_clear()

SEED_TENANT_ID = "11111111-1111-4111-8111-111111111111"


def _watcher_token() -> str:
    return create_mock_token(
        sub="auth0|watcher",
        tenant_id=SEED_TENANT_ID,
        role=UserRole.WATCHER.value,
    )


def test_ws_rejects_missing_token() -> None:
    client = TestClient(create_ws_app())
    with pytest.raises(Exception):
        with client.websocket_connect("/v1/ws"):
            pass


def test_ws_accepts_valid_token() -> None:
    client = TestClient(create_ws_app())
    with client.websocket_connect(f"/v1/ws?token={_watcher_token()}") as ws:
        msg = ws.receive_json()
        assert msg["type"] in {"heartbeat", "decision.state_changed"}


@pytest.mark.asyncio
async def test_connection_limit_per_sub() -> None:
    token = _watcher_token()
    sub = "auth0|watcher"
    tenant_id = SEED_TENANT_ID

    class FakeWebSocket:
        def __init__(self, idx: int) -> None:
            self.state = type("S", (), {"tenant_id": tenant_id, "sub": sub})()
            self.client_state = type("C", (), {"CONNECTED": 1})()
            self.idx = idx
            self.accepted = False

        async def accept(self) -> None:
            self.accepted = True

    sockets = [FakeWebSocket(i) for i in range(6)]
    results = []
    for ws in sockets:
        ok = await manager.connect(ws, tenant_id=tenant_id, sub=sub)  # type: ignore[arg-type]
        results.append(ok)
    assert results.count(True) == 5
    assert results.count(False) == 1
