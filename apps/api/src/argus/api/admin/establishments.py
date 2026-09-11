"""Establishment management routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from argus.api.deps import get_company_db, require_role
from argus.core.auth import AuthContext
from argus.domain.enums import UserRole
from argus.domain.models import Establishment
from argus.domain.schemas.admin import (
    CreateEstablishmentRequest,
    EstablishmentResponse,
    UpdateEstablishmentRequest,
)

router = APIRouter(
    prefix="/companies/{company_id}/establishments",
    tags=["admin-establishments"],
)

_MANAGER_PLUS = (UserRole.MANAGER, UserRole.ROOT, UserRole.ADMIN)


@router.get("", response_model=list[EstablishmentResponse])
async def list_establishments(
    session: AsyncSession = Depends(get_company_db),
    _auth: AuthContext = Depends(require_role(*_MANAGER_PLUS)),
) -> list[Establishment]:
    return list(
        (
            await session.scalars(
                select(Establishment)
                .where(Establishment.active.is_(True))
                .order_by(Establishment.name)
            )
        ).all()
    )


@router.post("", response_model=EstablishmentResponse, status_code=status.HTTP_201_CREATED)
async def create_establishment(
    company_id: UUID,
    body: CreateEstablishmentRequest,
    session: AsyncSession = Depends(get_company_db),
    _auth: AuthContext = Depends(require_role(*_MANAGER_PLUS)),
) -> Establishment:
    establishment = Establishment(
        company_id=company_id,
        name=body.name,
        address=body.address,
        timezone=body.timezone,
        active=body.active,
    )
    session.add(establishment)
    await session.flush()
    return establishment


@router.patch("/{establishment_id}", response_model=EstablishmentResponse)
async def update_establishment(
    company_id: UUID,
    establishment_id: UUID,
    body: UpdateEstablishmentRequest,
    session: AsyncSession = Depends(get_company_db),
    _auth: AuthContext = Depends(require_role(*_MANAGER_PLUS)),
) -> Establishment:
    establishment = await session.scalar(
        select(Establishment).where(
            Establishment.id == establishment_id,
            Establishment.company_id == company_id,
        )
    )
    if establishment is None:
        raise HTTPException(status_code=404, detail="Establishment not found")
    for field in ("name", "address", "timezone", "active"):
        value = getattr(body, field)
        if value is not None:
            setattr(establishment, field, value)
    await session.flush()
    return establishment


@router.delete("/{establishment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_establishment(
    company_id: UUID,
    establishment_id: UUID,
    session: AsyncSession = Depends(get_company_db),
    _auth: AuthContext = Depends(require_role(*_MANAGER_PLUS)),
) -> None:
    establishment = await session.scalar(
        select(Establishment).where(
            Establishment.id == establishment_id,
            Establishment.company_id == company_id,
        )
    )
    if establishment is None:
        raise HTTPException(status_code=404, detail="Establishment not found")
    establishment.active = False
