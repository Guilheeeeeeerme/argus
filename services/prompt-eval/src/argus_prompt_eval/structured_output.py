"""Structured output — force allowlisted JSON schemas from the VLM.

AI Engineering pattern: Structured output.
Schema for prompt hits; invalid shapes are rejected, never stored as detections.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, ValidationError, field_validator


PROMPT_HITS_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["any_match", "summary", "prompt_hits"],
    "properties": {
        "any_match": {"type": "boolean"},
        "summary": {"type": "string"},
        "prompt_hits": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["prompt_id", "matched", "confidence", "rationale"],
                "properties": {
                    "prompt_id": {"type": "string"},
                    "matched": {"type": "boolean"},
                    "confidence": {"type": "number"},
                    "rationale": {"type": "string"},
                },
            },
        },
    },
}


class PromptHit(BaseModel):
    prompt_id: str
    matched: bool
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str = ""

    @field_validator("confidence", mode="before")
    @classmethod
    def _clamp_confidence(cls, value: Any) -> float:
        try:
            return max(0.0, min(1.0, float(value)))
        except (TypeError, ValueError):
            return 0.0


class PromptEvalResult(BaseModel):
    any_match: bool
    summary: str = ""
    prompt_hits: list[PromptHit] = Field(default_factory=list)


def parse_prompt_eval_result(raw: dict[str, Any]) -> PromptEvalResult:
    """Validate and normalize VLM JSON; raises ValueError on invalid shape."""
    try:
        return PromptEvalResult.model_validate(raw)
    except ValidationError as exc:
        raise ValueError(f"Invalid prompt-eval structured output: {exc}") from exc


def output_schema() -> dict[str, Any]:
    return dict(PROMPT_HITS_JSON_SCHEMA)
