"""HTTP application CORS contract tests."""

from __future__ import annotations

import os

import pytest
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("AUTH0_USE_MOCK", "true")

from argus.apps.http import create_admin_app
from argus.config import get_settings

get_settings.cache_clear()


@pytest.mark.parametrize(
    "origin",
    [
        "http://localhost:8180",
        "http://localhost:8181",
        "http://127.0.0.1:8180",
        "http://127.0.0.1:8181",
    ],
)
@pytest.mark.asyncio
async def test_browser_origins_are_allowed_for_preflight(origin: str) -> None:
    """Admin and triage origins must be allowed for browser API calls."""
    transport = ASGITransport(app=create_admin_app())

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.options(
            "/health",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "GET",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
    assert "access-control-allow-credentials" not in response.headers or response.headers["access-control-allow-credentials"] == "false"
