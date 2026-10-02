"""Pydantic schemas for edge/test ingestion API."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import AliasChoices, BaseModel, Field


class InjectFrameReadyRequest(BaseModel):
    account_id: UUID = Field(validation_alias=AliasChoices("account_id", "company_id"))
    unit_id: UUID = Field(validation_alias=AliasChoices("unit_id", "establishment_id"))
    camera_id: UUID
    sequence_id: str | None = None
    captured_at: datetime | None = None
    frame_uris: list[str] = Field(default_factory=list)
    preproc_meta: dict[str, Any] = Field(default_factory=dict)


class InjectAcceptedResponse(BaseModel):
    sequence_id: str
    status: str = "queued"
    queued_at: datetime


# Legacy aliases kept so older tests importing these names still resolve.
IngestSequenceRequest = InjectFrameReadyRequest
IngestAcceptedResponse = InjectAcceptedResponse
