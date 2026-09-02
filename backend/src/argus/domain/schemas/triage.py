"""Pydantic schemas for triage API."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from argus.domain.enums import DecisionState, FeedbackDisposition


class DecisionSummary(BaseModel):
    id: UUID
    camera_id: UUID
    region_id: UUID | None
    state: DecisionState
    cumulative_severity: int
    evidence_count: int
    window_start: datetime
    window_end: datetime
    updated_at: datetime
    last_evidence_at: datetime | None

    model_config = {"from_attributes": True}


class EvidenceDetail(BaseModel):
    id: UUID
    captured_at: datetime
    severity_score: int
    vlm_result: dict
    playback_url: str | None = None

    model_config = {"from_attributes": True}


class DecisionDetail(BaseModel):
    id: UUID
    camera_id: UUID
    region_id: UUID | None
    state: DecisionState
    cumulative_severity: int
    evidence_count: int
    window_start: datetime
    window_end: datetime
    evidences: list[EvidenceDetail] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class ResolveDecisionRequest(BaseModel):
    disposition: FeedbackDisposition
    reasoning: str = ""
    updated_at: datetime

    @model_validator(mode="after")
    def require_reasoning_for_fp_fn(self) -> ResolveDecisionRequest:
        if self.disposition in {
            FeedbackDisposition.FALSE_POSITIVE,
            FeedbackDisposition.FALSE_NEGATIVE,
        } and not self.reasoning.strip():
            raise ValueError("reasoning required for false_positive/false_negative")
        return self


class ResolveDecisionResponse(BaseModel):
    decision_id: UUID
    state: DecisionState
    resolved_at: datetime
    resolved_by: str
