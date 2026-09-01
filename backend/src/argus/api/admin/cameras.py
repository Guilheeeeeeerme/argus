"""Camera and region management routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from argus.api.deps import get_tenant_db, require_role
from argus.core.auth import AuthContext
from argus.domain.enums import UserRole
from argus.domain.models import Camera, Market, RegionOfInterest
from argus.domain.schemas.admin import (
    CameraResponse,
    CreateCameraRequest,
    CreateRegionRequest,
    RegionResponse,
)

router = APIRouter(prefix="/tenants/{tenant_id}", tags=["admin-cameras"])


@router.post(
    "/markets/{market_id}/cameras",
    response_model=CameraResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_camera(
    tenant_id: UUID,
    market_id: UUID,
    body: CreateCameraRequest,
    session: AsyncSession = Depends(get_tenant_db),
    _auth: AuthContext = Depends(require_role(UserRole.TENANT_ADMIN, UserRole.ROOT_ADMIN)),
) -> Camera:
    market = await session.get(Market, market_id)
    if market is None or market.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Market not found")
    camera = Camera(
        tenant_id=tenant_id,
        market_id=market_id,
        name=body.name,
        edge_device_id=body.edge_device_id,
    )
    session.add(camera)
    await session.flush()
    return camera


@router.get("/cameras", response_model=list[CameraResponse])
async def list_cameras(
    session: AsyncSession = Depends(get_tenant_db),
    _auth: AuthContext = Depends(require_role(UserRole.TENANT_ADMIN, UserRole.ROOT_ADMIN)),
) -> list[Camera]:
    return list((await session.scalars(select(Camera).where(Camera.deleted_at.is_(None)))).all())


@router.post(
    "/cameras/{camera_id}/regions",
    response_model=RegionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_region(
    tenant_id: UUID,
    camera_id: UUID,
    body: CreateRegionRequest,
    session: AsyncSession = Depends(get_tenant_db),
    _auth: AuthContext = Depends(require_role(UserRole.TENANT_ADMIN, UserRole.ROOT_ADMIN)),
) -> RegionOfInterest:
    camera = await session.get(Camera, camera_id)
    if camera is None or camera.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found")
    region = RegionOfInterest(
        tenant_id=tenant_id,
        camera_id=camera_id,
        name=body.name,
        polygon=body.polygon,
    )
    session.add(region)
    await session.flush()
    return region
