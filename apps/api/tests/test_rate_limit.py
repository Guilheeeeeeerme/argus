"""API rate limiting tests (slowapi config and 429 behavior)."""

from __future__ import annotations

import os

import pytest
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("AUTH0_USE_MOCK", "true")

from argus.apps.http import (  # noqa: E402
    RATE_LIMIT_EXEMPT_PATHS,
    build_limiter,
    create_admin_app,
)
from argus.config import get_settings, settings  # noqa: E402

get_settings.cache_clear()


def test_limiter_config_defaults() -> None:
    limiter = build_limiter(settings)
    assert limiter.enabled
    assert "/health" in RATE_LIMIT_EXEMPT_PATHS
    assert "/docs" in RATE_LIMIT_EXEMPT_PATHS


@pytest.mark.asyncio
async def test_limit_returns_429_and_health_exempt(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "rate_limit_per_minute", 2)
    monkeypatch.setattr(settings, "redis_url", "")

    app = create_admin_app()
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        first = await client.get("/debug/auth")
        second = await client.get("/debug/auth")
        limited = await client.get("/debug/auth")
        health = await client.get("/health")

    assert first.status_code == 401
    assert second.status_code == 401
    assert limited.status_code == 429
    assert health.status_code == 200
