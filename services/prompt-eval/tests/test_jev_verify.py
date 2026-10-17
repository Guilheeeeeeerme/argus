"""Unit tests for post-VLM JEV verify (no network)."""

from __future__ import annotations

from argus_prompt_eval.jev_client import estimate_jev_usd, parse_jev_mode
from argus_prompt_eval.jev_verify import (
    build_verify_questions,
    build_verify_state,
    verify_after_vlm,
)
from argus_prompt_eval.structured_output import PromptEvalResult, PromptHit


def test_parse_jev_mode_defaults():
    assert parse_jev_mode(None, True) == "active"
    assert parse_jev_mode("", False) == "off"
    assert parse_jev_mode(" shadow ", True) == "shadow"


def test_estimate_jev_usd():
    assert estimate_jev_usd(1_000_000) == 0.042
    assert estimate_jev_usd(None) is None


def test_build_verify_state_compact():
    result = PromptEvalResult(
        any_match=True,
        summary="person near door",
        prompt_hits=[
            PromptHit(
                prompt_id="p1",
                matched=True,
                confidence=0.9,
                rationale="x" * 300,
            )
        ],
    )
    state = build_verify_state(result, sensor_score=0.2, edge_score=0.7)
    assert state["any_match"] is True
    assert len(state["prompt_hits"][0]["rationale"]) == 240
    q = build_verify_questions()
    assert set(q["disposition"]["criteria"]) == {"publish", "discard", "review"}


def test_verify_off_passthrough(monkeypatch):
    class OffClient:
        mode = "off"

        def configured(self):
            return False

    result = PromptEvalResult(any_match=True, summary="x", prompt_hits=[])
    decision = verify_after_vlm(result, client=OffClient())  # type: ignore[arg-type]
    assert decision.disposition == "passthrough"
    assert decision.used_jev is False


def test_verify_active_discard():
    class FakeClient:
        mode = "active"

        def configured(self):
            return True

        def decide_choice(self, state, questions, *, mode=None):
            return {
                "answers": {
                    "disposition": {
                        "type": "choice",
                        "choice": "discard",
                        "probabilities": {
                            "publish": 0.1,
                            "discard": 0.8,
                            "review": 0.1,
                        },
                        "confidence": 0.9,
                    }
                },
                "meta": {"estimated_usd": 0.0001, "mode": "active"},
            }

    result = PromptEvalResult(
        any_match=True,
        summary="noise",
        prompt_hits=[
            PromptHit(prompt_id="p", matched=True, confidence=0.6, rationale="maybe")
        ],
    )
    decision = verify_after_vlm(result, client=FakeClient())  # type: ignore[arg-type]
    assert decision.disposition == "discard"
    assert decision.used_jev is True


def test_verify_active_low_confidence_passthrough(monkeypatch):
    monkeypatch.setattr(
        "argus_prompt_eval.jev_verify.settings.jev_verify_confidence_floor",
        0.8,
    )

    class FakeClient:
        mode = "active"

        def configured(self):
            return True

        def decide_choice(self, state, questions, *, mode=None):
            return {
                "answers": {
                    "disposition": {
                        "type": "choice",
                        "choice": "discard",
                        "probabilities": {
                            "publish": 0.4,
                            "discard": 0.4,
                            "review": 0.2,
                        },
                        "confidence": 0.5,
                    }
                },
                "meta": {"estimated_usd": 0.0001, "mode": "active"},
            }

    result = PromptEvalResult(any_match=True, summary="x", prompt_hits=[])
    decision = verify_after_vlm(result, client=FakeClient())  # type: ignore[arg-type]
    assert decision.disposition == "passthrough"
