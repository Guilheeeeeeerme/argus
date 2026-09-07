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

from argus.config import settings
from argus.domain.enums import UserRole
from argus.integrations.auth0 import validate_jwt
from argus.services.database import get_db as _get_db, set_session_context
from argus.services.sessions import SessionData, get_session

_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True, slots=True)
class EdgeAuthContext:
    sub: str
    company_id: UUID
    camera_id: UUID
    token: str


@dataclass(frozen=True, slots=True)
class AuthContext:
    sub: str
    email: str
    role: UserRole
    company_id: UUID | None
    token: str
    location_id: UUID | None = None
    camera_id: UUID | None = None


def _auth_context_from_session(token: str, session: SessionData) -> AuthContext:
    try:
        role = UserRole(session.role)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid session role: {session.role}",
        ) from exc

    def _uuid_or_none(value: str | None) -> UUID | None:
        if not value:
            return None
        try:
            return UUID(value)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid session company/location reference",
            ) from exc

    return AuthContext(
        sub=session.user_id,
        email=session.email,
        role=role,
        company_id=_uuid_or_none(session.company_id),
        location_id=_uuid_or_none(session.location_id),
        token=token,
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

    tenant_raw = claims.get("company_id")
    camera_raw = claims.get("camera_id")
    if not tenant_raw or not camera_raw:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing company_id or camera_id claim",
        )

    try:
        company_id = UUID(tenant_raw)
        camera_id = UUID(camera_raw)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid company_id or camera_id claim",
        ) from exc

    auth = EdgeAuthContext(
        sub=claims.get("sub", ""),
        company_id=company_id,
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
    session = await get_session(credentials.credentials)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    auth = _auth_context_from_session(credentials.credentials, session)
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


async def set_company_context(session: AsyncSession, auth: AuthContext) -> None:
    await set_session_context(
        session,
        company_id=auth.company_id,
        role=auth.role.value,
    )


async def get_authenticated_db(
    auth: Annotated[AuthContext, Depends(get_auth_context)],
) -> AsyncGenerator[AsyncSession, None]:
    """Session with the Redis-session-derived RLS context applied."""
    async for session in _get_db():
        await set_company_context(session, auth)
        yield session
