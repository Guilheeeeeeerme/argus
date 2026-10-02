"""Unit management routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from argus.api.deps import get_account_db, require_role
from argus.core.auth import AuthContext
from argus.domain.enums import UserRole
from argus.domain.models import Unit
from argus.domain.schemas.admin import (
    CreateUnitRequest,
    UnitResponse,
    UpdateUnitRequest,
)

router = APIRouter(
    prefix="/accounts/{account_id}/units",
    tags=["admin-units"],
)

_MANAGER_PLUS = (UserRole.MANAGER, UserRole.ROOT, UserRole.ADMIN)
# Operators need the unit list for the triage grid picker (RLS already scopes to the account).
_READ_ROLES = (UserRole.OPERATOR, *_MANAGER_PLUS)


@router.get("", response_model=list[UnitResponse])
async def list_units(
    session: AsyncSession = Depends(get_account_db),
    _auth: AuthContext = Depends(require_role(*_READ_ROLES)),
) -> list[Unit]:
    return list(
        (
            await session.scalars(
                select(Unit)
                .where(Unit.active.is_(True))
                .order_by(Unit.name)
            )
        ).all()
    )


@router.get("/{unit_id}", response_model=UnitResponse)
async def get_unit(
    account_id: UUID,
    unit_id: UUID,
    session: AsyncSession = Depends(get_account_db),
    _auth: AuthContext = Depends(require_role(*_MANAGER_PLUS)),
) -> Unit:
    unit = await session.scalar(
        select(Unit).where(
            Unit.id == unit_id,
            Unit.account_id == account_id,
        )
    )
    if unit is None:
        raise HTTPException(status_code=404, detail="Unit not found")
    return unit


@router.post("", response_model=UnitResponse, status_code=status.HTTP_201_CREATED)
async def create_unit(
    account_id: UUID,
    body: CreateUnitRequest,
    session: AsyncSession = Depends(get_account_db),
    _auth: AuthContext = Depends(require_role(*_MANAGER_PLUS)),
) -> Unit:
    unit = Unit(
        account_id=account_id,
        name=body.name,
        address=body.address,
        timezone=body.timezone,
        active=body.active,
    )
    session.add(unit)
    await session.flush()
    return unit


@router.patch("/{unit_id}", response_model=UnitResponse)
async def update_unit(
    account_id: UUID,
    unit_id: UUID,
    body: UpdateUnitRequest,
    session: AsyncSession = Depends(get_account_db),
    _auth: AuthContext = Depends(require_role(*_MANAGER_PLUS)),
) -> Unit:
    unit = await session.scalar(
        select(Unit).where(
            Unit.id == unit_id,
            Unit.account_id == account_id,
        )
    )
    if unit is None:
        raise HTTPException(status_code=404, detail="Unit not found")
    for field in ("name", "address", "timezone", "active"):
        value = getattr(body, field)
        if value is not None:
            setattr(unit, field, value)
    await session.flush()
    return unit


@router.delete("/{unit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_unit(
    account_id: UUID,
    unit_id: UUID,
    session: AsyncSession = Depends(get_account_db),
    _auth: AuthContext = Depends(require_role(*_MANAGER_PLUS)),
) -> None:
    unit = await session.scalar(
        select(Unit).where(
            Unit.id == unit_id,
            Unit.account_id == account_id,
        )
    )
    if unit is None:
        raise HTTPException(status_code=404, detail="Unit not found")
    unit.active = False
