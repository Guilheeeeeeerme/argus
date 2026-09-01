"""Auth0 JWKS fetch/cache and JWT validation."""

from __future__ import annotations

import time
from typing import Any

import httpx
import jwt
from jwt import PyJWKClient

from argus.config import settings

_jwks_client: PyJWKClient | None = None
_mock_keys: dict[str, Any] | None = None


def _get_jwks_client() -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        _jwks_client = PyJWKClient(settings.auth0_jwks_url, cache_keys=True)
    return _jwks_client


def _claim(payload: dict[str, Any], name: str) -> Any:
    ns = settings.auth0_claims_namespace.rstrip("/")
    if name in payload:
        return payload[name]
    return payload.get(f"{ns}/{name}")


def extract_standard_claims(payload: dict[str, Any]) -> dict[str, Any]:
    tenant_id = _claim(payload, "tenant_id")
    role = _claim(payload, "role")
    camera_id = _claim(payload, "camera_id")
    return {
        "sub": payload.get("sub", ""),
        "tenant_id": tenant_id,
        "role": role,
        "camera_id": camera_id,
        "gty": payload.get("gty"),
    }


def validate_jwt(token: str) -> dict[str, Any]:
    """Validate Bearer token and return decoded claims."""
    if settings.auth0_use_mock:
        return _validate_mock_jwt(token)

    algorithms = [a.strip() for a in settings.auth0_algorithms.split(",") if a.strip()]
    signing_key = _get_jwks_client().get_signing_key_from_jwt(token)
    payload = jwt.decode(
        token,
        signing_key.key,
        algorithms=algorithms,
        audience=settings.auth0_api_audience,
        issuer=settings.auth0_issuer,
        options={"require": ["exp", "sub"]},
    )
    return extract_standard_claims(payload)


def _validate_mock_jwt(token: str) -> dict[str, Any]:
    algorithms = ["HS256"]
    payload = jwt.decode(
        token,
        settings.dev_jwt_secret,
        algorithms=algorithms,
        audience=settings.auth0_api_audience,
        issuer=settings.auth0_issuer,
        options={"require": ["exp", "sub"]},
    )
    return extract_standard_claims(payload)


def create_mock_m2m_token(
    *,
    sub: str,
    tenant_id: str,
    camera_id: str,
    expires_in: int = 3600,
) -> str:
    """Issue a local M2M HS256 token when AUTH0_USE_MOCK=true."""
    now = int(time.time())
    payload: dict[str, Any] = {
        "sub": sub,
        "iss": settings.auth0_issuer,
        "aud": settings.auth0_api_audience,
        "iat": now,
        "exp": now + expires_in,
        "tenant_id": tenant_id,
        "camera_id": camera_id,
        "gty": "client-credentials",
    }
    return jwt.encode(payload, settings.dev_jwt_secret, algorithm="HS256")


def create_mock_token(
    *,
    sub: str,
    tenant_id: str,
    role: str,
    expires_in: int = 3600,
    camera_id: str | None = None,
) -> str:
    """Issue a local HS256 token when AUTH0_USE_MOCK=true."""
    now = int(time.time())
    payload: dict[str, Any] = {
        "sub": sub,
        "iss": settings.auth0_issuer,
        "aud": settings.auth0_api_audience,
        "iat": now,
        "exp": now + expires_in,
        "tenant_id": tenant_id,
        "role": role,
    }
    if camera_id:
        payload["camera_id"] = camera_id
    return jwt.encode(payload, settings.dev_jwt_secret, algorithm="HS256")


async def warm_jwks_cache() -> None:
    if settings.auth0_use_mock:
        return
    async with httpx.AsyncClient() as client:
        await client.get(settings.auth0_jwks_url)
