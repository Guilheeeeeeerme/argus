"""GET /v1/dev/session/{persona} must stay off unless explicitly opted in."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from argus.apps.http import create_admin_app
from argus.config import Settings, get_settings


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_dev_session_route_absent_when_opt_in_off(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AUTH0_USE_MOCK", "true")
    monkeypatch.setenv("DEV_SESSION_ENABLED", "false")
    get_settings.cache_clear()
    async with AsyncClient(
        transport=ASGITransport(app=create_admin_app()), base_url="http://test"
    ) as client:
        response = await client.get("/v1/dev/session/root")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_dev_session_route_absent_when_mock_off(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AUTH0_USE_MOCK", "false")
    monkeypatch.setenv("DEV_SESSION_ENABLED", "true")
    get_settings.cache_clear()
    async with AsyncClient(
        transport=ASGITransport(app=create_admin_app()), base_url="http://test"
    ) as client:
        response = await client.get("/v1/dev/session/root")
    assert response.status_code == 404


def test_dev_sessions_allowed_requires_both_flags():
    assert Settings(AUTH0_USE_MOCK=True, DEV_SESSION_ENABLED=False).dev_session_enabled is False
    assert Settings(AUTH0_USE_MOCK=False, DEV_SESSION_ENABLED=True).auth0_use_mock is False
    both = Settings(AUTH0_USE_MOCK=True, DEV_SESSION_ENABLED=True)
    assert both.auth0_use_mock and both.dev_session_enabled
