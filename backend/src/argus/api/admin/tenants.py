"""Root admin tenant management routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from argus.api.deps import get_root_admin_db, require_role
from argus.core.auth import AuthContext
from argus.domain.enums import UserRole
from argus.domain.models import Tenant, TenantUser
from argus.domain.schemas.admin import (
    AssignTenantAdminRequest,
    CreateTenantRequest,
    TenantResponse,
    TenantUserResponse,
)

router = APIRouter(prefix="/admin", tags=["admin-tenants"])


@router.post("/tenants", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    body: CreateTenantRequest,
    session: AsyncSession = Depends(get_root_admin_db),
    _auth: AuthContext = Depends(require_role(UserRole.ROOT_ADMIN)),
) -> Tenant:
    tenant = Tenant(
        name=body.name,
        slug=body.slug,
        aggregation_window_secs=body.aggregation_window_secs,
    )
    session.add(tenant)
    await session.flush()
    return tenant


@router.get("/tenants", response_model=list[TenantResponse])
async def list_tenants(
    session: AsyncSession = Depends(get_root_admin_db),
    _auth: AuthContext = Depends(require_role(UserRole.ROOT_ADMIN)),
) -> list[Tenant]:
    return list((await session.scalars(select(Tenant).order_by(Tenant.name))).all())


@router.post(
    "/tenants/{tenant_id}/admins",
    response_model=TenantUserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def assign_tenant_admin(
    tenant_id: UUID,
    body: AssignTenantAdminRequest,
    session: AsyncSession = Depends(get_root_admin_db),
    _auth: AuthContext = Depends(require_role(UserRole.ROOT_ADMIN)),
) -> TenantUser:
    user = TenantUser(
        tenant_id=tenant_id,
        idp_subject=body.idp_subject,
        email=body.email,
        role=UserRole.TENANT_ADMIN,
    )
    session.add(user)
    await session.flush()
    return user
