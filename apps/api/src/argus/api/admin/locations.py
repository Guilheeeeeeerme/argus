"""Location management routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from argus.api.deps import get_company_db, require_role
from argus.core.auth import AuthContext
from argus.domain.enums import UserRole
from argus.domain.models import Location
from argus.domain.schemas.admin import CreateLocationRequest, LocationResponse

router = APIRouter(prefix="/companies/{company_id}/locations", tags=["admin-locations"])


@router.get("", response_model=list[LocationResponse])
async def list_locations(
    session: AsyncSession = Depends(get_company_db),
    _auth: AuthContext = Depends(require_role(UserRole.MANAGER, UserRole.ROOT, UserRole.ADMIN)),
) -> list[Location]:
    return list(
        (
            await session.scalars(
                select(Location).where(Location.deleted_at.is_(None)).order_by(Location.name)
            )
        ).all()
    )


@router.post("", response_model=LocationResponse, status_code=status.HTTP_201_CREATED)
async def create_location(
    company_id: UUID,
    body: CreateLocationRequest,
    session: AsyncSession = Depends(get_company_db),
    _auth: AuthContext = Depends(require_role(UserRole.MANAGER, UserRole.ROOT, UserRole.ADMIN)),
) -> Location:
    location = Location(company_id=company_id, name=body.name, address=body.address, timezone=body.timezone)
    session.add(location)
    await session.flush()
    return location


@router.patch("/{location_id}", response_model=LocationResponse)
async def update_location(
    company_id: UUID,
    location_id: UUID,
    body: CreateLocationRequest,
    session: AsyncSession = Depends(get_company_db),
    _auth: AuthContext = Depends(require_role(UserRole.MANAGER, UserRole.ROOT, UserRole.ADMIN)),
) -> Location:
    location = await session.scalar(
        select(Location).where(Location.id == location_id, Location.company_id == company_id)
    )
    if location is None:
        raise HTTPException(status_code=404, detail="Location not found")
    location.name = body.name
    location.address = body.address
    location.timezone = body.timezone
    await session.flush()
    return location


@router.delete("/{location_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_location(
    company_id: UUID,
    location_id: UUID,
    session: AsyncSession = Depends(get_company_db),
    _auth: AuthContext = Depends(require_role(UserRole.MANAGER, UserRole.ROOT, UserRole.ADMIN)),
) -> None:
    location = await session.scalar(
        select(Location).where(Location.id == location_id, Location.company_id == company_id)
    )
    if location is None:
        raise HTTPException(status_code=404, detail="Location not found")
    location.deleted_at = func.now()

class SketchUpdateRequest(BaseModel):
    sketch: str


@router.put("/{location_id}/sketch", response_model=LocationResponse)
async def upload_sketch(
    company_id: UUID,
    location_id: UUID,
    body: SketchUpdateRequest,
    session: AsyncSession = Depends(get_company_db),
    _auth: AuthContext = Depends(require_role(UserRole.MANAGER, UserRole.ROOT, UserRole.ADMIN)),
) -> Location:
    location = await session.scalar(
        select(Location).where(Location.id == location_id, Location.company_id == company_id)
    )
    if location is None:
        raise HTTPException(status_code=404, detail="Location not found")
    location.sketch = body.sketch
    await session.flush()
    return location
