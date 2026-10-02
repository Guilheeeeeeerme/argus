"""Pre-rename URLs answer 410 Gone so stale clients fail loudly."""

from __future__ import annotations

import os

import pytest
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("AUTH0_USE_MOCK", "true")

from argus.apps.http import create_admin_app
from argus.config import get_settings

get_settings.cache_clear()


@pytest.mark.parametrize(
    "method,path",
    [
        ("GET", "/v1/companies/11111111-1111-4111-8111-111111111111/establishments"),
        ("POST", "/v1/companies/11111111-1111-4111-8111-111111111111/triage-cases/x/resolve"),
        ("GET", "/v1/admin/companies"),
        ("DELETE", "/v1/admin/companies/11111111-1111-4111-8111-111111111111"),
        ("GET", "/v1/auth/companies"),
    ],
)
@pytest.mark.asyncio
async def test_legacy_paths_are_gone(method: str, path: str) -> None:
    transport = ASGITransport(app=create_admin_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.request(method, path)
    assert response.status_code == 410
    assert "accounts" in response.json()["error"]["message"]
