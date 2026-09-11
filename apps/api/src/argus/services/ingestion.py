"""Legacy edge ingestion service — slimmed to frames:ready enqueue for tests."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from argus.services.stream import enqueue_frames_ready


class IngestionService:
    """Kept for import compatibility; prefer POST /v1/ingest/sequences inject route."""

    async def accept_frames_ready(
        self,
        *,
        company_id: UUID,
        establishment_id: UUID,
        camera_id: UUID,
        frame_uris: list[str] | None = None,
        sequence_id: str | None = None,
        preproc_meta: dict[str, Any] | None = None,
        captured_at: datetime | None = None,
    ) -> dict[str, str]:
        now = datetime.now(UTC)
        seq = sequence_id or str(uuid4())
        await enqueue_frames_ready(
            {
                "company_id": str(company_id),
                "establishment_id": str(establishment_id),
                "camera_id": str(camera_id),
                "sequence_id": seq,
                "captured_at": (captured_at or now).isoformat(),
                "frame_uris": frame_uris or [],
                "preproc_meta": preproc_meta or {},
            }
        )
        return {"sequence_id": seq, "status": "queued"}
