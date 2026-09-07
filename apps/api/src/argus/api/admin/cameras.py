"""Camera and region management routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from argus.api.deps import get_company_db, require_role
from argus.core.auth import AuthContext
from argus.domain.enums import UserRole
from argus.domain.models import Camera, Location, RegionOfInterest
from argus.domain.schemas.admin import (
    CameraResponse,
    CreateCameraRequest,
    UpdateCameraRequest,
    CreateRegionRequest,
    RegionResponse,
)

router = APIRouter(prefix="/companies/{company_id}", tags=["admin-cameras"])


@router.post(
    "/locations/{location_id}/cameras",
    response_model=CameraResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_camera(
    company_id: UUID,
    location_id: UUID,
    body: CreateCameraRequest,
    session: AsyncSession = Depends(get_company_db),
    _auth: AuthContext = Depends(require_role(UserRole.MANAGER, UserRole.ROOT, UserRole.ADMIN)),
) -> Camera:
    location = await session.get(Location, location_id)
    if location is None or location.company_id != company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location not found")
    camera = Camera(
        company_id=company_id,
        location_id=location_id,
        name=body.name,
        stream_url=body.stream_url,
        stream_username=body.stream_username,
        stream_password=body.stream_password,
        placement_x=body.placement_x,
        placement_y=body.placement_y,
    )
    session.add(camera)
    await session.flush()
    return camera


@router.get("/cameras", response_model=list[CameraResponse])
async def list_cameras(
    session: AsyncSession = Depends(get_company_db),
    _auth: AuthContext = Depends(require_role(UserRole.MANAGER, UserRole.ROOT, UserRole.ADMIN)),
) -> list[Camera]:
    return list((await session.scalars(select(Camera).where(Camera.deleted_at.is_(None)))).all())


@router.post(
    "/cameras/{camera_id}/regions",
    response_model=RegionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_region(
    company_id: UUID,
    camera_id: UUID,
    body: CreateRegionRequest,
    session: AsyncSession = Depends(get_company_db),
    _auth: AuthContext = Depends(require_role(UserRole.MANAGER, UserRole.ROOT, UserRole.ADMIN)),
) -> RegionOfInterest:
    camera = await session.get(Camera, camera_id)
    if camera is None or camera.company_id != company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found")
    region = RegionOfInterest(
        company_id=company_id,
        camera_id=camera_id,
        name=body.name,
        polygon=body.polygon,
    )
    session.add(region)
    await session.flush()
    return region


@router.patch("/cameras/{camera_id}", response_model=CameraResponse)
async def update_camera(
    company_id: UUID,
    camera_id: UUID,
    body: UpdateCameraRequest,
    session: AsyncSession = Depends(get_company_db),
    _auth: AuthContext = Depends(require_role(UserRole.MANAGER, UserRole.ROOT, UserRole.ADMIN)),
) -> Camera:
    camera = await session.scalar(
        select(Camera).where(Camera.id == camera_id, Camera.company_id == company_id)
    )
    if camera is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found")
    for field in ("name", "stream_url", "stream_username", "stream_password", "placement_x", "placement_y"):
        value = getattr(body, field)
        if value is not None:
            setattr(camera, field, value)
    await session.flush()
    return camera
