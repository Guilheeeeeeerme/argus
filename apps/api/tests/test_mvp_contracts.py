"""MVP contract unit tests for prompt-eval pure helpers.

Imports ``argus_prompt_eval`` via PYTHONPATH injected in conftest
(services/prompt-eval/src). Falls back to skip if the package is unavailable.
"""

from __future__ import annotations

import pytest

try:
    from argus_prompt_eval.negative_discard import should_discard
    from argus_prompt_eval.redis_io import parse_context_event, parse_frames_ready
    from argus_prompt_eval.structured_output import (
        PromptEvalResult,
        PromptHit,
        parse_prompt_eval_result,
    )

    _IMPORT_OK = True
except ImportError:  # pragma: no cover - env without prompt-eval on path
    _IMPORT_OK = False


pytestmark = pytest.mark.skipif(
    not _IMPORT_OK,
    reason="argus_prompt_eval not importable; ensure services/prompt-eval/src is on PYTHONPATH",
)


def test_should_discard_when_no_matches() -> None:
    result = PromptEvalResult(
        any_match=False,
        summary="clear",
        prompt_hits=[
            PromptHit(prompt_id="p1", matched=False, confidence=0.1, rationale="no"),
        ],
    )
    assert should_discard(result) is True


def test_should_not_discard_when_hit_matched() -> None:
    result = PromptEvalResult(
        any_match=True,
        summary="intrusion",
        prompt_hits=[
            PromptHit(prompt_id="p1", matched=True, confidence=0.9, rationale="yes"),
        ],
    )
    assert should_discard(result) is False


def test_parse_prompt_eval_result_rejects_invalid_shape() -> None:
    with pytest.raises(ValueError, match="Invalid prompt-eval"):
        parse_prompt_eval_result({"summary": "missing required fields"})


def test_parse_prompt_eval_result_clamps_confidence() -> None:
    parsed = parse_prompt_eval_result(
        {
            "any_match": True,
            "summary": "hit",
            "prompt_hits": [
                {
                    "prompt_id": "p1",
                    "matched": True,
                    "confidence": 4.2,
                    "rationale": "ok",
                }
            ],
        }
    )
    assert parsed.prompt_hits[0].confidence == 1.0


def test_parse_frames_ready_field_shape() -> None:
    parsed = parse_frames_ready(
        {
            "company_id": "c1",
            "establishment_id": "e1",
            "camera_id": "cam1",
            "sequence_id": "seq-1",
            "captured_at": "2026-09-11T12:00:00Z",
            "frame_uris": '["s3://bucket/a.bin","s3://bucket/b.bin"]',
            "preproc_meta": '{"motion":true}',
        }
    )
    assert set(parsed) >= {
        "company_id",
        "establishment_id",
        "camera_id",
        "sequence_id",
        "captured_at",
        "frame_uris",
        "preproc_meta",
    }
    assert parsed["frame_uris"] == ["s3://bucket/a.bin", "s3://bucket/b.bin"]
    assert parsed["preproc_meta"] == {"motion": True}


def test_parse_context_event_field_shape() -> None:
    parsed = parse_context_event(
        {
            "company_id": "c1",
            "establishment_id": "e1",
            "camera_id": "",
            "kind": "pos.sale",
            "payload": '{"sku":"X"}',
            "received_at": "2026-09-11T12:00:00Z",
            "webhook_id": "wh1",
        }
    )
    assert parsed["kind"] == "pos.sale"
    assert parsed["payload"] == {"sku": "X"}
    assert parsed["camera_id"] is None
    assert parsed["webhook_id"] == "wh1"
