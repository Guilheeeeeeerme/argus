"""Post-VLM JEV verify — publish / discard / review on compact text state.

Gemini owns vision. JEV only judges the structured Gemini draft + optional
edge/sensor scores. Low JEV confidence keeps the Gemini/code path (escalate).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from argus_prompt_eval.config import settings
from argus_prompt_eval.jev_client import JevClient
from argus_prompt_eval.structured_output import PromptEvalResult

logger = logging.getLogger(__name__)

VERIFY_RUBRIC = "argus-vlm-verify-jev-v1"
CONFIDENCE_FLOOR = 0.55

DISPOSITION_CRITERIA = {
    "publish": "Create a TriageCase — the VLM hits look like a real operator-relevant event.",
    "discard": "Drop as a false positive or noise — do not create a TriageCase.",
    "review": "Borderline — publish for human review with lower certainty.",
}


@dataclass(frozen=True)
class JevVerifyDecision:
    disposition: str  # publish | discard | review | passthrough
    confidence: float | None
    estimated_usd: float | None
    mode: str
    used_jev: bool


def build_verify_state(
    result: PromptEvalResult,
    *,
    sensor_score: float | None = None,
    edge_score: float | None = None,
    consensus_positive: bool | None = None,
) -> dict[str, Any]:
    return {
        "rubric": VERIFY_RUBRIC,
        "summary": result.summary,
        "any_match": result.any_match,
        "prompt_hits": [
            {
                "prompt_id": h.prompt_id,
                "matched": h.matched,
                "confidence": h.confidence,
                "rationale": (h.rationale or "")[:240],
            }
            for h in result.prompt_hits
        ],
        "sensor_score": sensor_score,
        "edge_score": edge_score,
        "consensus_positive": consensus_positive,
    }


def build_verify_questions() -> dict[str, dict[str, Any]]:
    return {
        "disposition": {
            "type": "choice",
            "instructions": (
                "Given the Gemini VLM draft in state (`summary`, `prompt_hits`) and "
                "optional edge/sensor scores, should Argus publish a TriageCase, "
                "discard as a false positive, or mark for review?"
            ),
            "criteria": DISPOSITION_CRITERIA,
        }
    }


def verify_after_vlm(
    result: PromptEvalResult,
    *,
    sensor_score: float | None = None,
    edge_score: float | None = None,
    consensus_positive: bool | None = None,
    client: JevClient | None = None,
) -> JevVerifyDecision:
    """Return disposition. `passthrough` means keep Gemini/code decision unchanged."""
    jev = client or JevClient()
    if jev.mode == "off" or not jev.configured():
        return JevVerifyDecision(
            disposition="passthrough",
            confidence=None,
            estimated_usd=None,
            mode=jev.mode,
            used_jev=False,
        )

    state = build_verify_state(
        result,
        sensor_score=sensor_score,
        edge_score=edge_score,
        consensus_positive=consensus_positive,
    )
    questions = build_verify_questions()

    if jev.mode == "shadow":
        try:
            decision = jev.decide_choice(state, questions, mode="shadow")
            ans = decision["answers"].get("disposition") or {}
            choice = ans.get("choice")
            confidence = ans.get("confidence")
            meta = decision["meta"]
            logger.info(
                "jev_shadow task=verify disposition=%s confidence=%s estimated_usd=%s "
                "gemini_any_match=%s",
                choice,
                confidence,
                meta.get("estimated_usd"),
                result.any_match,
            )
        except Exception as exc:  # noqa: BLE001 — shadow never blocks production
            logger.warning(
                "jev_shadow_error task=verify code=%s",
                type(exc).__name__,
            )
        return JevVerifyDecision(
            disposition="passthrough",
            confidence=None,
            estimated_usd=None,
            mode="shadow",
            used_jev=True,
        )

    # active
    decision = jev.decide_choice(state, questions, mode="active")
    ans = decision["answers"].get("disposition") or {}
    choice = ans.get("choice")
    confidence = float(ans.get("confidence") or 0)
    meta = decision["meta"]
    if choice not in DISPOSITION_CRITERIA:
        logger.warning("jev verify unknown choice; passthrough")
        return JevVerifyDecision(
            disposition="passthrough",
            confidence=confidence,
            estimated_usd=meta.get("estimated_usd"),
            mode="active",
            used_jev=True,
        )
    floor = settings.jev_verify_confidence_floor
    if confidence < floor:
        logger.info(
            "jev verify low confidence=%.3f floor=%.3f → escalate passthrough",
            confidence,
            floor,
        )
        return JevVerifyDecision(
            disposition="passthrough",
            confidence=confidence,
            estimated_usd=meta.get("estimated_usd"),
            mode="active",
            used_jev=True,
        )
    logger.info(
        "jev_verify disposition=%s confidence=%.3f estimated_usd=%s",
        choice,
        confidence,
        meta.get("estimated_usd"),
    )
    return JevVerifyDecision(
        disposition=choice,
        confidence=confidence,
        estimated_usd=meta.get("estimated_usd"),
        mode="active",
        used_jev=True,
    )
