"""/version release probe (no DB required)."""

from httpx import ASGITransport, AsyncClient

from argus.apps.http import create_admin_app


async def test_version_returns_git_sha() -> None:
    app = create_admin_app()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/version")
    assert response.status_code == 200
    payload = response.json()
    assert payload["service"] == "argus-api"
    assert "gitsha" in payload


async def test_version_is_rate_limit_exempt() -> None:
    from argus.apps.http import is_rate_limit_exempt

    assert is_rate_limit_exempt("/version") is True
