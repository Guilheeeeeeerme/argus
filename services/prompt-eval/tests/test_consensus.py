import math

import pytest
from argus_prompt_eval.consensus import ConsensusEngine
from argus_prompt_eval.structured_output import parse_prompt_eval_result


def test_weighted_and_override_paths():
    engine = ConsensusEngine()
    assert engine.evaluate(
        sensor_score=1, edge_score=1, gemini_score=0, prompt_hit=False
    ).is_positive
    assert engine.evaluate(
        sensor_score=0, edge_score=0.4, gemini_score=0.1, prompt_hit=True
    ).is_positive
    assert not engine.evaluate(
        sensor_score=0, edge_score=0.1, gemini_score=0.1, prompt_hit=False
    ).is_positive
    assert not engine.evaluate(
        sensor_score=1, edge_score=1, gemini_score=1, prompt_hit=True, veto=True
    ).is_positive


@pytest.mark.parametrize("value", [math.nan, math.inf, -1, 2, "bad", True])
def test_bad_scores_fail_closed(value):
    assert (
        not ConsensusEngine()
        .evaluate(sensor_score=1, edge_score=value, gemini_score=1, prompt_hit=True)
        .is_positive
    )


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_nonfinite_model_confidence_rejected(value):
    with pytest.raises(ValueError):
        parse_prompt_eval_result(
            {
                "any_match": True,
                "prompt_hits": [
                    {"prompt_id": "p", "matched": True, "confidence": value}
                ],
            }
        )


@pytest.mark.parametrize(
    "field,value", [("any_match", "false"), ("matched", "true"), ("confidence", True)]
)
def test_malformed_model_fields_rejected(field, value):
    raw = {
        "any_match": True,
        "prompt_hits": [{"prompt_id": "p", "matched": True, "confidence": 0.8}],
    }
    if field == "any_match":
        raw[field] = value
    else:
        raw["prompt_hits"][0][field] = value
    with pytest.raises(ValueError):
        parse_prompt_eval_result(raw)
