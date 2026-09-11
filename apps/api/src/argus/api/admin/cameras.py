"""Camera management routes nested under establishments."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from argus.api.deps import get_company_db, require_role
from argus.core.auth import AuthContext
from argus.domain.enums import UserRole
from argus.domain.models import Camera, Establishment
from argus.domain.schemas.admin import (
    CameraResponse,
    CreateCameraRequest,
    UpdateCameraRequest,
)

router = APIRouter(prefix="/companies/{company_id}", tags=["admin-cameras"])

_MANAGER_PLUS = (UserRole.MANAGER, UserRole.ROOT, UserRole.ADMIN)


@router.post(
    "/establishments/{establishment_id}/cameras",
    response_model=CameraResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_camera(
    company_id: UUID,
    establishment_id: UUID,
    body: CreateCameraRequest,
    session: AsyncSession = Depends(get_company_db),
    _auth: AuthContext = Depends(require_role(*_MANAGER_PLUS)),
) -> Camera:
    establishment = await session.get(Establishment, establishment_id)
    if establishment is None or establishment.company_id != company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Establishment not found")
    camera = Camera(
        company_id=company_id,
        establishment_id=establishment_id,
        name=body.name,
        stream_url=body.stream_url,
        stream_username=body.stream_username,
        stream_password=body.stream_password,
        is_active=body.is_active,
    )
    session.add(camera)
    await session.flush()
    return camera


@router.get("/cameras", response_model=list[CameraResponse])
async def list_cameras(
    session: AsyncSession = Depends(get_company_db),
    _auth: AuthContext = Depends(require_role(*_MANAGER_PLUS)),
) -> list[Camera]:
    return list(
        (
            await session.scalars(
                select(Camera).where(
                    Camera.is_active.is_(True),
                    Camera.deleted_at.is_(None),
                )
            )
        ).all()
    )


@router.get(
    "/establishments/{establishment_id}/cameras",
    response_model=list[CameraResponse],
)
async def list_establishment_cameras(
    company_id: UUID,
    establishment_id: UUID,
    session: AsyncSession = Depends(get_company_db),
    _auth: AuthContext = Depends(require_role(*_MANAGER_PLUS)),
) -> list[Camera]:
    return list(
        (
            await session.scalars(
                select(Camera).where(
                    Camera.establishment_id == establishment_id,
                    Camera.company_id == company_id,
                    Camera.is_active.is_(True),
                    Camera.deleted_at.is_(None),
                )
            )
        ).all()
    )


@router.patch("/cameras/{camera_id}", response_model=CameraResponse)
async def update_camera(
    company_id: UUID,
    camera_id: UUID,
    body: UpdateCameraRequest,
    session: AsyncSession = Depends(get_company_db),
    _auth: AuthContext = Depends(require_role(*_MANAGER_PLUS)),
) -> Camera:
    camera = await session.scalar(
        select(Camera).where(Camera.id == camera_id, Camera.company_id == company_id)
    )
    if camera is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found")
    for field in ("name", "stream_url", "stream_username", "stream_password", "is_active"):
        value = getattr(body, field)
        if value is not None:
            setattr(camera, field, value)
    await session.flush()
    return camera


@router.delete("/cameras/{camera_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_camera(
    company_id: UUID,
    camera_id: UUID,
    session: AsyncSession = Depends(get_company_db),
    _auth: AuthContext = Depends(require_role(*_MANAGER_PLUS)),
) -> None:
    camera = await session.scalar(
        select(Camera).where(Camera.id == camera_id, Camera.company_id == company_id)
    )
    if camera is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found")
    camera.is_active = False
    camera.deleted_at = datetime.now(UTC)
