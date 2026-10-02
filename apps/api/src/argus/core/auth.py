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
from argus.domain.enums import PLATFORM_ROLES, UserRole
from argus.integrations.auth0 import validate_jwt
from argus.services.database import get_db as _get_db, set_session_context
from argus.services.memberships import has_account_membership
from argus.services.sessions import SessionData, get_session, update_session

_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True, slots=True)
class EdgeAuthContext:
    sub: str
    account_id: UUID
    camera_id: UUID
    token: str

    @property
    def company_id(self) -> UUID:  # deprecated alias (one release)
        return self.account_id


@dataclass(frozen=True, slots=True)
class AuthContext:
    sub: str
    email: str
    role: UserRole
    account_id: UUID | None
    token: str
    unit_id: UUID | None = None
    camera_id: UUID | None = None

    @property
    def company_id(self) -> UUID | None:  # deprecated alias (one release)
        return self.account_id

    @property
    def establishment_id(self) -> UUID | None:  # deprecated alias (one release)
        return self.unit_id


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
                detail="Invalid session account/unit reference",
            ) from exc

    unit_raw = session.unit_id
    return AuthContext(
        sub=session.user_id,
        email=session.email,
        role=role,
        account_id=_uuid_or_none(session.account_id),
        unit_id=_uuid_or_none(unit_raw),
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

    # Edge tokens minted before the rename still carry company_id.
    tenant_raw = claims.get("account_id") or claims.get("company_id")
    camera_raw = claims.get("camera_id")
    if not tenant_raw or not camera_raw:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing account_id or camera_id claim",
        )

    try:
        account_id = UUID(tenant_raw)
        camera_id = UUID(camera_raw)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid account_id or camera_id claim",
        ) from exc

    auth = EdgeAuthContext(
        sub=claims.get("sub", ""),
        account_id=account_id,
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
    if auth.role not in PLATFORM_ROLES and auth.account_id is not None:
        if not await has_account_membership(auth.sub, str(auth.account_id)):
            # Revocation takes effect immediately, while allowing selection of remaining memberships.
            session.account_id = None
            session.unit_id = None
            await update_session(credentials.credentials, session)
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


async def set_account_context(session: AsyncSession, auth: AuthContext) -> None:
    await set_session_context(
        session,
        account_id=auth.account_id,
        role=auth.role.value,
    )


set_company_context = set_account_context  # deprecated alias (one release)


async def get_authenticated_db(
    auth: Annotated[AuthContext, Depends(get_auth_context)],
) -> AsyncGenerator[AsyncSession, None]:
    """Session with the Redis-session-derived RLS context applied."""
    async for session in _get_db():
        await set_account_context(session, auth)
        yield session
