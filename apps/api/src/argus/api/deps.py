"""Shared FastAPI dependencies for admin and triage APIs."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from argus.core.auth import AuthContext, get_auth_context, set_account_context
from argus.domain.enums import PLATFORM_ROLES, UserRole
from argus.services.database import get_db as _get_db, set_session_context


def require_role(*roles: UserRole):
    allowed = set(roles)

    async def _dependency(
        auth: Annotated[AuthContext, Depends(get_auth_context)],
    ) -> AuthContext:
        if auth.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return auth

    return _dependency


def require_platform(auth: Annotated[AuthContext, Depends(get_auth_context)]) -> AuthContext:
    if auth.role not in PLATFORM_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Platform role required",
        )
    return auth


def require_account_access(
    account_id: Annotated[UUID, Path(alias="account_id")],
    auth: Annotated[AuthContext, Depends(get_auth_context)],
) -> AuthContext:
    if auth.role in PLATFORM_ROLES:
        return auth
    if auth.account_id != account_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account access denied",
        )
    return auth


async def get_account_db(
    account_id: Annotated[UUID, Path(alias="account_id")],
    auth: Annotated[AuthContext, Depends(require_account_access)],
) -> AsyncGenerator[AsyncSession, None]:
    async for session in _get_db():
        if auth.role in PLATFORM_ROLES:
            await set_session_context(
                session,
                account_id=account_id,
                role=UserRole.MANAGER.value,
            )
        else:
            await set_account_context(session, auth)
        yield session


async def get_platform_db(
    auth: Annotated[AuthContext, Depends(require_platform)],
) -> AsyncGenerator[AsyncSession, None]:
    async for session in _get_db():
        await set_session_context(session, account_id=None, role=auth.role.value)
        yield session


# Deprecated aliases (one release).
require_company_access = require_account_access
get_company_db = get_account_db
