"""Pure MVP contract tests for prompt-eval (no DB / API conftest)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from argus_prompt_eval.negative_discard import should_discard
from argus_prompt_eval.structured_output import (
    PromptEvalResult,
    PromptHit,
    parse_prompt_eval_result,
)
from argus_prompt_eval.temporal_window import TimeWindow, clamp_window


def test_negative_discard_when_no_match() -> None:
    result = PromptEvalResult(any_match=False, summary="clear", prompt_hits=[])
    assert should_discard(result) is True


def test_negative_discard_when_hits_fail() -> None:
    result = PromptEvalResult(
        any_match=True,
        summary="maybe",
        prompt_hits=[
            PromptHit(prompt_id="p1", matched=False, confidence=0.1, rationale="no"),
        ],
    )
    assert should_discard(result) is True


def test_keep_positive_hit() -> None:
    result = PromptEvalResult(
        any_match=True,
        summary="hit",
        prompt_hits=[
            PromptHit(prompt_id="p1", matched=True, confidence=0.9, rationale="yes"),
        ],
    )
    assert should_discard(result) is False


def test_parse_structured_output() -> None:
    parsed = parse_prompt_eval_result(
        {
            "any_match": True,
            "summary": "door open with person",
            "prompt_hits": [
                {
                    "prompt_id": "abc",
                    "matched": True,
                    "confidence": 0.82,
                    "rationale": "person visible",
                }
            ],
        }
    )
    assert parsed.any_match is True
    assert parsed.prompt_hits[0].confidence == pytest.approx(0.82)


def test_clip_window_max_10_minutes() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    end = start + timedelta(minutes=30)
    clamped = clamp_window(TimeWindow(start=start, end=end), max_seconds=600)
    assert (clamped.end - clamped.start).total_seconds() <= 600
