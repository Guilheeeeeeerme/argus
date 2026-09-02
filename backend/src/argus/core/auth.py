"""Authentication context, FastAPI dependencies, and RLS session wiring."""

from __future__ import annotations

from collections.abc import AsyncGenerator, Callable
from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from argus.domain.enums import UserRole
from argus.integrations.auth0 import validate_jwt
from argus.services.database import get_db as _get_db, set_session_context

_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True, slots=True)
class EdgeAuthContext:
    sub: str
    tenant_id: UUID
    camera_id: UUID
    token: str


@dataclass(frozen=True, slots=True)
class AuthContext:
    sub: str
    tenant_id: UUID | None
    role: UserRole
    token: str
    camera_id: UUID | None = None


def _parse_role(value: str | None) -> UserRole:
    if value is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing role claim",
        )
    try:
        return UserRole(value)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid role claim: {value}",
        ) from exc


def _parse_tenant_id(value: str | None, role: UserRole) -> UUID | None:
    if role == UserRole.ROOT_ADMIN:
        return UUID(value) if value else None
    if not value:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing tenant_id claim",
        )
    try:
        return UUID(value)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid tenant_id claim",
        ) from exc


def _auth_context_from_token(token: str) -> AuthContext:
    try:
        claims = validate_jwt(token)
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        ) from exc

    role = _parse_role(claims.get("role"))
    tenant_id = _parse_tenant_id(claims.get("tenant_id"), role)
    camera_raw = claims.get("camera_id")
    camera_id = UUID(camera_raw) if camera_raw else None

    return AuthContext(
        sub=claims.get("sub", ""),
        tenant_id=tenant_id,
        role=role,
        token=token,
        camera_id=camera_id,
    )


async def get_edge_auth_context(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> EdgeAuthContext:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        claims = validate_jwt(credentials.credentials)
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        ) from exc

    if claims.get("gty") != "client-credentials":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="M2M client credentials token required",
        )

    tenant_raw = claims.get("tenant_id")
    camera_raw = claims.get("camera_id")
    if not tenant_raw or not camera_raw:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing tenant_id or camera_id claim",
        )

    try:
        tenant_id = UUID(tenant_raw)
        camera_id = UUID(camera_raw)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid tenant_id or camera_id claim",
        ) from exc

    auth = EdgeAuthContext(
        sub=claims.get("sub", ""),
        tenant_id=tenant_id,
        camera_id=camera_id,
        token=credentials.credentials,
    )
    request.state.edge_auth = auth
    return auth


async def get_auth_context(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> AuthContext:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    auth = _auth_context_from_token(credentials.credentials)
    request.state.auth = auth
    return auth


def require_role(*roles: UserRole) -> Callable:
    allowed = set(roles)

    async def _dependency(auth: Annotated[AuthContext, Depends(get_auth_context)]) -> AuthContext:
        if auth.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return auth

    return _dependency


async def set_tenant_context(session: AsyncSession, auth: AuthContext) -> None:
    await set_session_context(
        session,
        tenant_id=auth.tenant_id,
        role=auth.role.value,
    )


async def get_authenticated_db(
    auth: Annotated[AuthContext, Depends(get_auth_context)],
) -> AsyncGenerator[AsyncSession, None]:
    """Session with JWT-derived RLS context applied."""
    async for session in _get_db():
        await set_tenant_context(session, auth)
        yield session
