"""Camera management routes nested under units."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from argus.api.deps import get_account_db, require_role
from argus.core.auth import AuthContext
from argus.domain.enums import UserRole
from argus.domain.models import Camera, Unit
from argus.domain.schemas.admin import (
    CameraResponse,
    CreateCameraRequest,
    UpdateCameraRequest,
)

router = APIRouter(prefix="/accounts/{account_id}", tags=["admin-cameras"])

_MANAGER_PLUS = (UserRole.MANAGER, UserRole.ROOT, UserRole.ADMIN)


@router.post(
    "/units/{unit_id}/cameras",
    response_model=CameraResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_camera(
    account_id: UUID,
    unit_id: UUID,
    body: CreateCameraRequest,
    session: AsyncSession = Depends(get_account_db),
    _auth: AuthContext = Depends(require_role(*_MANAGER_PLUS)),
) -> Camera:
    unit = await session.get(Unit, unit_id)
    if unit is None or unit.account_id != account_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unit not found")
    camera = Camera(
        account_id=account_id,
        unit_id=unit_id,
        name=body.name,
        stream_url=body.stream_url,
        stream_username=body.stream_username,
        stream_password=body.stream_password,
        is_active=body.is_active,
    )
    session.add(camera)
    await session.flush()
    return camera


def _camera_query(*, include_inactive: bool):
    query = select(Camera).where(Camera.deleted_at.is_(None))
    if not include_inactive:
        query = query.where(Camera.is_active.is_(True))
    return query.order_by(Camera.name, Camera.id)


@router.get("/cameras", response_model=list[CameraResponse])
async def list_cameras(
    include_inactive: bool = Query(default=False),
    session: AsyncSession = Depends(get_account_db),
    _auth: AuthContext = Depends(require_role(*_MANAGER_PLUS)),
) -> list[Camera]:
    return list((await session.scalars(_camera_query(include_inactive=include_inactive))).all())


@router.get(
    "/units/{unit_id}/cameras",
    response_model=list[CameraResponse],
)
async def list_unit_cameras(
    account_id: UUID,
    unit_id: UUID,
    include_inactive: bool = Query(default=False),
    session: AsyncSession = Depends(get_account_db),
    _auth: AuthContext = Depends(require_role(*_MANAGER_PLUS)),
) -> list[Camera]:
    query = _camera_query(include_inactive=include_inactive).where(
        Camera.unit_id == unit_id,
        Camera.account_id == account_id,
    )
    return list((await session.scalars(query)).all())


@router.patch("/cameras/{camera_id}", response_model=CameraResponse)
async def update_camera(
    account_id: UUID,
    camera_id: UUID,
    body: UpdateCameraRequest,
    session: AsyncSession = Depends(get_account_db),
    _auth: AuthContext = Depends(require_role(*_MANAGER_PLUS)),
) -> Camera:
    camera = await session.scalar(
        select(Camera).where(Camera.id == camera_id, Camera.account_id == account_id)
    )
    if camera is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found")
    for field in ("name", "is_active"):
        value = getattr(body, field)
        if value is not None:
            setattr(camera, field, value)
    # Credentials: omitted/None keeps the stored value, "" clears it.
    for field in ("stream_url", "stream_username", "stream_password"):
        value = getattr(body, field)
        if value is not None:
            setattr(camera, field, value or None)
    await session.flush()
    return camera


@router.delete("/cameras/{camera_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_camera(
    account_id: UUID,
    camera_id: UUID,
    session: AsyncSession = Depends(get_account_db),
    _auth: AuthContext = Depends(require_role(*_MANAGER_PLUS)),
) -> None:
    camera = await session.scalar(
        select(Camera).where(Camera.id == camera_id, Camera.account_id == account_id)
    )
    if camera is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found")
    camera.is_active = False
    camera.deleted_at = datetime.now(UTC)
