"""Camera grid routes for the triage workspace: overview per unit + latest frame bytes."""

from __future__ import annotations

from uuid import UUID

from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from argus.api.deps import get_company_db, require_role
from argus.core.auth import AuthContext
from argus.domain.enums import TriageCaseState, UserRole
from argus.domain.models import Camera, Detection, TriageCase
from argus.domain.schemas.triage import CameraOverviewItem
from argus.services.latest_frames import get_latest_frame, get_latest_frames
from argus.services.storage import download_bytes

router = APIRouter(prefix="/companies/{company_id}", tags=["triage-cameras"])

_TRIAGE_ROLES = (UserRole.OPERATOR, UserRole.MANAGER, UserRole.ROOT, UserRole.ADMIN)


@router.get(
    "/establishments/{establishment_id}/cameras/overview",
    response_model=list[CameraOverviewItem],
)
async def camera_overview(
    company_id: UUID,
    establishment_id: UUID,
    session: AsyncSession = Depends(get_company_db),
    _auth: AuthContext = Depends(require_role(*_TRIAGE_ROLES)),
) -> list[CameraOverviewItem]:
    cameras = list(
        (
            await session.scalars(
                select(Camera)
                .where(
                    Camera.establishment_id == establishment_id,
                    Camera.company_id == company_id,
                    Camera.deleted_at.is_(None),
                    Camera.is_active.is_(True),
                )
                .order_by(Camera.name, Camera.id)
            )
        ).all()
    )
    if not cameras:
        return []

    open_counts = dict(
        (
            await session.execute(
                select(Detection.camera_id, func.count(TriageCase.id))
                .join(TriageCase, TriageCase.detection_id == Detection.id)
                .where(
                    Detection.establishment_id == establishment_id,
                    Detection.company_id == company_id,
                    TriageCase.state == TriageCaseState.OPEN,
                )
                .group_by(Detection.camera_id)
            )
        ).all()
    )
    latest = await get_latest_frames(camera.id for camera in cameras)

    items: list[CameraOverviewItem] = []
    for camera in cameras:
        frame = latest.get(str(camera.id))
        items.append(
            CameraOverviewItem(
                id=camera.id,
                name=camera.name,
                is_active=camera.is_active,
                last_frame_at=frame.captured_at_datetime() if frame else None,
                open_case_count=int(open_counts.get(camera.id, 0)),
            )
        )
    return items


@router.get("/cameras/{camera_id}/latest-frame")
async def camera_latest_frame(
    company_id: UUID,
    camera_id: UUID,
    request: Request,
    session: AsyncSession = Depends(get_company_db),
    _auth: AuthContext = Depends(require_role(*_TRIAGE_ROLES)),
) -> Response:
    """Newest JPEG for a camera, proxied from object storage.

    ``ETag`` is the frame's ``captured_at``; ``If-None-Match`` → 304 so a 2 s
    poll costs nothing while the frame has not changed. 404 when stream-prep has
    not published a frame recently (TTL) or the camera is not in this company.
    """
    owned = await session.scalar(
        select(Camera.id).where(
            Camera.id == camera_id,
            Camera.company_id == company_id,
            Camera.deleted_at.is_(None),
        )
    )
    if owned is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found")

    frame = await get_latest_frame(camera_id)
    if frame is None or (frame.company_id and frame.company_id != str(company_id)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Latest frame not found")

    etag = f'W/"{frame.captured_at}"'
    base_headers = {
        "ETag": etag,
        "Cache-Control": "private, no-store",
        "X-Captured-At": frame.captured_at,
    }
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=status.HTTP_304_NOT_MODIFIED, headers=base_headers)

    try:
        payload, content_type = await download_bytes(frame.uri)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Latest frame not found") from exc
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code")
        if code in {"NoSuchKey", "NoSuchBucket", "404"}:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Latest frame not found") from exc
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Evidence storage unavailable") from exc

    return Response(
        content=payload,
        media_type=content_type if content_type.startswith("image/") else "image/jpeg",
        headers={**base_headers, "X-Content-Type-Options": "nosniff"},
    )
