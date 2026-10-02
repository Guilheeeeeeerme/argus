"""Public registration is unavailable in the demo MVP."""

import pytest


@pytest.mark.asyncio
async def test_public_registration_is_not_available(admin_client):
    response = await admin_client.post(
        "/v1/auth/register", json={"email": "new@example.com", "password": "Password123!"}
    )
    assert response.status_code == 404
