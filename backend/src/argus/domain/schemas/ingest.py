"""Pydantic schemas for edge ingestion API."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class FramePayload(BaseModel):
    index: int = Field(ge=0)
    content: str = Field(description="Base64-encoded JPEG or PNG frame")
    captured_at: datetime | None = None


class IngestSequenceRequest(BaseModel):
    ingestion_id: UUID
    tenant_id: UUID
    camera_id: UUID
    captured_at: datetime
    context_mode_id: UUID
    region_id: UUID | None = None
    edge_trigger_metadata: dict[str, Any] | None = None
    frames: list[FramePayload] = Field(min_length=1, max_length=30)


class IngestAcceptedResponse(BaseModel):
    ingestion_id: UUID
    status: Literal["queued", "duplicate"]
    queued_at: datetime
