"""Pydantic schemas for triage API."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from argus.domain.enums import TriageCaseState


class DetectionSummary(BaseModel):
    id: UUID
    camera_id: UUID
    establishment_id: UUID
    sequence_id: str | None = None
    summary: str | None = None
    confidence: float | None = None
    prompt_hits: list[dict[str, Any]] = Field(default_factory=list)
    clip_uri: str | None = None
    window_started_at: datetime | None = None
    window_ended_at: datetime | None = None
    frame_uris: list[str] | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class TriageCaseSummary(BaseModel):
    id: UUID
    detection_id: UUID
    state: TriageCaseState
    resolved_at: datetime | None = None
    resolved_by: str | None = None
    updated_at: datetime | None = None
    detection: DetectionSummary | None = None

    model_config = {"from_attributes": True}


class TriageCaseDetail(BaseModel):
    id: UUID
    detection_id: UUID
    state: TriageCaseState
    resolved_at: datetime | None = None
    resolved_by: str | None = None
    updated_at: datetime | None = None
    detection: DetectionSummary | None = None
    clip_playback_url: str | None = None

    model_config = {"from_attributes": True}


ResolveDisposition = Literal["confirmed", "dismissed", "false_positive"]


class ResolveTriageCaseRequest(BaseModel):
    disposition: ResolveDisposition
    reasoning: str | None = None

    @model_validator(mode="after")
    def require_reasoning_for_fp(self) -> ResolveTriageCaseRequest:
        if self.disposition == "false_positive" and not (self.reasoning or "").strip():
            raise ValueError("reasoning required for false_positive")
        return self


class ResolveTriageCaseResponse(BaseModel):
    triage_case_id: UUID
    state: TriageCaseState
    resolved_at: datetime
    resolved_by: str


class FeedbackResponse(BaseModel):
    id: UUID
    triage_case_id: UUID
    disposition: str
    reasoning: str
    created_at: datetime

    model_config = {"from_attributes": True}
