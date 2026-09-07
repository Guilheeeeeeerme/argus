"""WebSocket gateway tests."""

from __future__ import annotations

import asyncio
import os

import pytest
from httpx import ASGITransport, AsyncClient
from starlette.testclient import TestClient

os.environ.setdefault("AUTH0_USE_MOCK", "true")

from argus.apps.http import create_ws_app
from argus.config import get_settings
from argus.domain.enums import UserRole
from tests.helpers import session_token
from argus.ws.gateway import manager

get_settings.cache_clear()

SEED_TENANT_ID = "11111111-1111-4111-8111-111111111111"


import argus.ws.handlers as ws_handlers
from argus.services.sessions import SessionData


def _fake_get_session(token: str):
    async def _get(t: str | None = None) -> SessionData | None:
        if t == "good-token":
            return SessionData(
                user_id="test-operator-user",
                email="operator@test.local",
                role=UserRole.OPERATOR.value,
                company_id=SEED_TENANT_ID,
            )
        return None
    return _get


def test_ws_rejects_missing_token() -> None:
    client = TestClient(create_ws_app())
    with pytest.raises(Exception):
        with client.websocket_connect("/v1/ws"):
            pass


def test_ws_accepts_valid_token(monkeypatch) -> None:
    monkeypatch.setattr(ws_handlers, "get_session", _fake_get_session("good-token"))
    client = TestClient(create_ws_app())
    with client.websocket_connect("/v1/ws?token=good-token") as ws:
        msg = ws.receive_json()
        assert msg["type"] == "ready"


@pytest.mark.asyncio
async def test_connection_limit_per_sub() -> None:
    sub = "test-operator-user"
    company_id = SEED_TENANT_ID

    class FakeWebSocket:
        def __init__(self, idx: int) -> None:
            self.state = type("S", (), {"company_id": company_id, "sub": sub})()
            self.client_state = type("C", (), {"CONNECTED": 1})()
            self.idx = idx
            self.accepted = False

        async def accept(self) -> None:
            self.accepted = True

    sockets = [FakeWebSocket(i) for i in range(6)]
    results = []
    for ws in sockets:
        ok = await manager.connect(ws, company_id=company_id, sub=sub)  # type: ignore[arg-type]
        results.append(ok)
    assert results.count(True) == 5
    assert results.count(False) == 1
