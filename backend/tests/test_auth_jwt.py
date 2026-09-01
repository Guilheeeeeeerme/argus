"""JWT validation and RBAC dependency tests."""

from __future__ import annotations

import os
import time

import jwt
import pytest
from fastapi import HTTPException

os.environ.setdefault("AUTH0_USE_MOCK", "true")

from argus.config import get_settings
from argus.core.auth import _auth_context_from_token, require_role
from argus.domain.enums import UserRole
from argus.integrations.auth0 import create_mock_token, validate_jwt

get_settings.cache_clear()


def test_valid_mock_token_passes() -> None:
    token = create_mock_token(
        sub="auth0|test",
        tenant_id="11111111-1111-4111-8111-111111111111",
        role=UserRole.TENANT_ADMIN.value,
    )
    claims = validate_jwt(token)
    assert claims["role"] == UserRole.TENANT_ADMIN.value


def test_expired_token_raises_401() -> None:
    settings = get_settings()
    now = int(time.time())
    payload = {
        "sub": "auth0|expired",
        "iss": settings.auth0_issuer,
        "aud": settings.auth0_api_audience,
        "iat": now - 7200,
        "exp": now - 3600,
        "tenant_id": "11111111-1111-4111-8111-111111111111",
        "role": UserRole.WATCHER.value,
    }
    token = jwt.encode(payload, settings.dev_jwt_secret, algorithm="HS256")
    with pytest.raises(HTTPException) as exc:
        _auth_context_from_token(token)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_require_role_rejects_watcher() -> None:
    token = create_mock_token(
        sub="auth0|watcher",
        tenant_id="11111111-1111-4111-8111-111111111111",
        role=UserRole.WATCHER.value,
    )
    auth = _auth_context_from_token(token)
    dep = require_role(UserRole.TENANT_ADMIN)
    with pytest.raises(HTTPException) as exc:
        await dep(auth)
    assert exc.value.status_code == 403
