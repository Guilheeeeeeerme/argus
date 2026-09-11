"""Unit tests formerly tied to recipe_builder VLM sanitize — now structured_output."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_PROMPT_EVAL_SRC = Path(__file__).resolve().parents[3] / "services" / "prompt-eval" / "src"
if _PROMPT_EVAL_SRC.is_dir() and str(_PROMPT_EVAL_SRC) not in sys.path:
    sys.path.insert(0, str(_PROMPT_EVAL_SRC))

try:
    from argus_prompt_eval.structured_output import parse_prompt_eval_result
except ImportError:  # pragma: no cover
    parse_prompt_eval_result = None  # type: ignore[assignment]


pytestmark = pytest.mark.skipif(
    parse_prompt_eval_result is None,
    reason="argus_prompt_eval not importable",
)


def test_structured_output_clamps_confidence_and_rejects_junk() -> None:
    parsed = parse_prompt_eval_result(
        {
            "any_match": True,
            "summary": "intrusion",
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

    with pytest.raises(ValueError):
        parse_prompt_eval_result({"shell": "rm -rf /", "confidence_score": 1})
