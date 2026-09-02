"""Shared FastAPI dependencies for admin and triage APIs."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from argus.core.auth import AuthContext, get_auth_context, set_tenant_context
from argus.domain.enums import UserRole
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


def require_tenant_access(
    tenant_id: Annotated[UUID, Path(alias="tenant_id")],
    auth: Annotated[AuthContext, Depends(get_auth_context)],
) -> AuthContext:
    if auth.role == UserRole.ROOT_ADMIN:
        return auth
    if auth.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant access denied",
        )
    return auth


async def get_tenant_db(
    tenant_id: Annotated[UUID, Path(alias="tenant_id")],
    auth: Annotated[AuthContext, Depends(require_tenant_access)],
) -> AsyncGenerator[AsyncSession, None]:
    async for session in _get_db():
        if auth.role == UserRole.ROOT_ADMIN:
            await set_session_context(
                session,
                tenant_id=tenant_id,
                role=UserRole.TENANT_ADMIN.value,
            )
        else:
            await set_tenant_context(session, auth)
        yield session


async def get_root_admin_db(
    auth: Annotated[AuthContext, Depends(require_role(UserRole.ROOT_ADMIN))],
) -> AsyncGenerator[AsyncSession, None]:
    async for session in _get_db():
        await set_session_context(session, tenant_id=None, role=UserRole.ROOT_ADMIN.value)
        yield session
