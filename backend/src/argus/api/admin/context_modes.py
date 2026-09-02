"""Context mode, schedule, and lens routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from argus.api.deps import get_tenant_db, require_role
from argus.core.auth import AuthContext
from argus.domain.enums import UserRole
from argus.domain.models import ContextMode, ContextModeSchedule, Lens
from argus.domain.schemas.admin import (
    ContextModeResponse,
    CreateContextModeRequest,
    CreateLensRequest,
    CreateScheduleRequest,
    LensResponse,
    ScheduleResponse,
)

router = APIRouter(prefix="/tenants/{tenant_id}", tags=["admin-context"])


@router.post(
    "/context-modes",
    response_model=ContextModeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_context_mode(
    tenant_id: UUID,
    body: CreateContextModeRequest,
    session: AsyncSession = Depends(get_tenant_db),
    _auth: AuthContext = Depends(require_role(UserRole.TENANT_ADMIN, UserRole.ROOT_ADMIN)),
) -> ContextMode:
    mode = ContextMode(
        tenant_id=tenant_id,
        name=body.name,
        description=body.description,
    )
    session.add(mode)
    await session.flush()
    return mode


@router.get("/context-modes", response_model=list[ContextModeResponse])
async def list_context_modes(
    session: AsyncSession = Depends(get_tenant_db),
    _auth: AuthContext = Depends(require_role(UserRole.TENANT_ADMIN, UserRole.ROOT_ADMIN)),
) -> list[ContextMode]:
    return list((await session.scalars(select(ContextMode))).all())


@router.post(
    "/context-modes/{mode_id}/schedules",
    response_model=ScheduleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_schedule(
    tenant_id: UUID,
    mode_id: UUID,
    body: CreateScheduleRequest,
    session: AsyncSession = Depends(get_tenant_db),
    _auth: AuthContext = Depends(require_role(UserRole.TENANT_ADMIN, UserRole.ROOT_ADMIN)),
) -> ContextModeSchedule:
    mode = await session.get(ContextMode, mode_id)
    if mode is None or mode.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Context mode not found")
    schedule = ContextModeSchedule(
        tenant_id=tenant_id,
        context_mode_id=mode_id,
        day_of_week=body.day_of_week,
        start_time=body.start_time,
        end_time=body.end_time,
        market_id=body.market_id,
    )
    session.add(schedule)
    await session.flush()
    return schedule


@router.post(
    "/context-modes/{mode_id}/lenses",
    response_model=LensResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_lens(
    tenant_id: UUID,
    mode_id: UUID,
    body: CreateLensRequest,
    session: AsyncSession = Depends(get_tenant_db),
    _auth: AuthContext = Depends(require_role(UserRole.TENANT_ADMIN, UserRole.ROOT_ADMIN)),
) -> Lens:
    mode = await session.get(ContextMode, mode_id)
    if mode is None or mode.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Context mode not found")
    lens = Lens(
        tenant_id=tenant_id,
        context_mode_id=mode_id,
        name=body.name,
        system_prompt=body.system_prompt,
        output_schema=body.output_schema,
    )
    session.add(lens)
    await session.flush()
    return lens
