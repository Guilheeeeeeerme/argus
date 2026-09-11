"""Internal routes for companion microservices (stream gateway, etc.)."""

from __future__ import annotations

import hmac
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select

from argus.config import settings
from argus.domain.enums import UserRole
from argus.domain.models import Camera, Establishment
from argus.services.database import get_db, set_session_context

router = APIRouter(prefix="/v1/internal", tags=["internal"])


def require_gateway_token(
    x_stream_gateway_token: str | None = Header(default=None, alias="X-Stream-Gateway-Token"),
) -> None:
    if not x_stream_gateway_token or not hmac.compare_digest(
        x_stream_gateway_token, settings.stream_gateway_token
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid gateway token")


class StreamConfig(BaseModel):
    camera_id: UUID
    company_id: UUID
    establishment_id: UUID
    name: str
    establishment_name: str
    stream_url: str | None
    username: str | None
    password: str | None


@router.get(
    "/stream-configs",
    response_model=list[StreamConfig],
    dependencies=[Depends(require_gateway_token)],
)
async def stream_configs() -> list[StreamConfig]:
    """All active cameras with their industry-standard stream config (for go2rtc sync)."""
    configs: list[StreamConfig] = []
    async for session in get_db():
        await set_session_context(session, company_id=None, role=UserRole.ROOT.value)
        rows = (
            await session.execute(
                select(Camera, Establishment)
                .join(Establishment, Camera.establishment_id == Establishment.id)
                .where(Camera.is_active.is_(True), Camera.deleted_at.is_(None))
            )
        ).all()
        for camera, establishment in rows:
            if not camera.stream_url:
                continue
            configs.append(
                StreamConfig(
                    camera_id=camera.id,
                    company_id=camera.company_id,
                    establishment_id=establishment.id,
                    name=camera.name,
                    establishment_name=establishment.name,
                    stream_url=camera.stream_url,
                    username=camera.stream_username,
                    password=camera.stream_password,
                )
            )
    return configs
