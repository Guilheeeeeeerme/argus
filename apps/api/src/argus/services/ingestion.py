"""Edge sequence ingestion — S3 upload + Redis Stream enqueue (no DB hot path)."""

from __future__ import annotations

import asyncio
import base64
import binascii
from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status

from argus.core.auth import EdgeAuthContext
from argus.domain.schemas.ingest import IngestAcceptedResponse, IngestSequenceRequest
from argus.services.redis import delete_key, get_key, set_key_nx
from argus.services.storage import upload_bytes
from argus.services.stream import enqueue_ingest_event

IDEMPOTENCY_TTL_SECS = 86_400
ACTIVE_MODE_TTL_SECS = 86_400
ACTIVE_MODE_KEY = "camera:active_mode:{camera_id}"
IDEMPOTENCY_KEY = "ingest:idem:{company_id}:{ingestion_id}"


class IngestionService:
    async def accept_sequence(
        self,
        auth: EdgeAuthContext,
        request: IngestSequenceRequest,
    ) -> IngestAcceptedResponse:
        self._validate_claims(auth, request)
        now = datetime.now(UTC)

        idem_key = IDEMPOTENCY_KEY.format(
            company_id=request.company_id,
            ingestion_id=request.ingestion_id,
        )
        if not await set_key_nx(idem_key, "1", ex=IDEMPOTENCY_TTL_SECS):
            return IngestAcceptedResponse(
                ingestion_id=request.ingestion_id,
                status="duplicate",
                queued_at=now,
            )

        try:
            await self._validate_active_mode(request)
            frame_uris = await self._upload_frames(request)
            await enqueue_ingest_event(
                {
                    "ingestion_id": str(request.ingestion_id),
                    "company_id": str(request.company_id),
                    "camera_id": str(request.camera_id),
                    "captured_at": request.captured_at.isoformat(),
                    "rule_set_id": str(request.rule_set_id),
                    "region_id": str(request.region_id) if request.region_id else "",
                    "edge_trigger_metadata": request.edge_trigger_metadata or {},
                    "frame_uris": frame_uris,
                }
            )
        except Exception:
            await delete_key(idem_key)
            raise

        return IngestAcceptedResponse(
            ingestion_id=request.ingestion_id,
            status="queued",
            queued_at=now,
        )

    def _validate_claims(
        self,
        auth: EdgeAuthContext,
        request: IngestSequenceRequest,
    ) -> None:
        if request.company_id != auth.company_id or request.camera_id != auth.camera_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "message": "company_id/camera_id mismatch with token claims",
                    "details": {
                        "token_company_id": str(auth.company_id),
                        "token_camera_id": str(auth.camera_id),
                    },
                },
            )

    async def _validate_active_mode(self, request: IngestSequenceRequest) -> None:
        key = ACTIVE_MODE_KEY.format(camera_id=request.camera_id)
        active_mode = await get_key(key)
        if not active_mode:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "Camera has no active context mode",
                    "details": {"camera_id": str(request.camera_id)},
                },
            )
        if UUID(active_mode) != request.rule_set_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "rule_set_id does not match active mode for camera",
                    "details": {
                        "camera_id": str(request.camera_id),
                        "active_rule_set_id": active_mode,
                        "requested_rule_set_id": str(request.rule_set_id),
                    },
                },
            )

    async def _upload_frames(self, request: IngestSequenceRequest) -> list[str]:
        prefix = f"{request.company_id}/{request.camera_id}/{request.ingestion_id}"

        async def _upload_one(frame_index: int, content_b64: str) -> str:
            try:
                data = base64.b64decode(content_b64, validate=True)
            except (binascii.Error, ValueError) as exc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "message": "Invalid base64 frame content",
                        "details": {"frame_index": frame_index},
                    },
                ) from exc
            key = f"{prefix}/{frame_index}.bin"
            return await upload_bytes(key, data, content_type="application/octet-stream")

        uris = await asyncio.gather(
            *(_upload_one(frame.index, frame.content) for frame in request.frames)
        )
        return list(uris)
