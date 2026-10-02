"""Exercise the real edge producer and prompt consumer wire contract without ML."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "services/edge-cv/src"))

from argus.services.sensor_fusion import SensorFusionBuffer
from argus_edge_cv.pipeline import EdgeInferencePipeline, Settings
from argus_prompt_eval.consensus import ConsensusEngine
from argus_prompt_eval.redis_io import parse_candidates_ready

ACCOUNT = "11111111-1111-4111-8111-111111111111"
SITE = "22222222-2222-4222-8222-222222222222"
CAMERA = "33333333-3333-4333-8333-333333333333"
OTHER_ACCOUNT = "44444444-4444-4444-8444-444444444444"
TIME = "2026-10-01T12:00:00+00:00"


class SyntheticVision:
    def signature(self, frame):
        return frame

    def motion(self, previous, current):
        return float(previous != current)

    def novelty(self, previous, current):
        return float(previous != current)


class SyntheticDetector:
    def detect(self, frame, identity):
        assert identity == (ACCOUNT, SITE, CAMERA)
        return [
            {
                "track_id": frame,
                "class_name": "person",
                "confidence": 0.9,
                "bbox": [0.0, 0.0, 10.0, 20.0],
            }
        ]


def produce(role="trigger", payload=None, *, account=ACCOUNT):
    sensors = SensorFusionBuffer()
    sensors.add(
        {
            "account_id": account,
            "unit_id": SITE,
            "camera_id": CAMERA,
            "context_event_id": "sensor-1",
            "kind": "door",
            "role": role,
            "confidence": 0.8,
            "occurred_at": TIME,
            "payload": payload or {},
        }
    )
    pipeline = EdgeInferencePipeline(
        Settings(), SyntheticDetector(), int, vision=SyntheticVision()
    )
    fields = {
        "account_id": ACCOUNT,
        "unit_id": SITE,
        "camera_id": CAMERA,
        "sequence_id": "sequence-1",
        "captured_at": TIME,
        "frame_uris": json.dumps(["1", "2"]),
        "preproc_meta": json.dumps({"sample_interval_seconds": 1}),
    }
    candidate = pipeline.process(fields, sensor_buffer=sensors)
    assert candidate is not None
    # Redis exposes string-valued fields; pass the producer output unchanged.
    assert all(isinstance(value, str) for value in candidate.values())
    return parse_candidates_ready(candidate)


@pytest.mark.parametrize(
    "role,data,score,veto",
    [
        ("trigger", {}, 0.8, False),
        ("context", {}, 0.0, False),
        ("filter", {"reject": True}, 0.0, True),
        ("filter", {"accepted": False}, 0.0, True),
        ("filter", {"accepted": True}, 0.0, False),
    ],
)
def test_real_candidate_wire_preserves_sensor_role_and_consensus(
    role, data, score, veto
):
    parsed = produce(role, data)
    assert parsed["frame_uris"] == ["1", "2"]
    assert parsed["edge_score"] == 0.9
    assert parsed["motion_score"] == 1.0
    assert parsed["temporal_span_seconds"] == 1.0
    assert parsed["sensor_ids"] == ["sensor-1"]
    assert parsed["sensors"][0]["role"] == role
    assert parsed["sensors"][0]["occurred_at"] == TIME
    assert parsed["sensor_score"] == score
    assert parsed["sensor_veto"] is veto
    decision = ConsensusEngine().evaluate(
        sensor_score=parsed["sensor_score"],
        edge_score=parsed["edge_score"],
        gemini_score=0.9,
        prompt_hit=True,
        veto=parsed["sensor_veto"],
    )
    assert decision.is_positive is (not veto)
    assert decision.score == pytest.approx(0.25 * score + 0.35 * 0.9 + 0.40 * 0.9)
    if veto:
        assert decision.reason == "sensor_veto"


def test_other_tenant_filter_cannot_veto_candidate():
    parsed = produce("filter", {"reject": True}, account=OTHER_ACCOUNT)
    assert parsed["sensors"] == []
    assert parsed["sensor_ids"] == []
    assert parsed["sensor_veto"] is False
    assert parsed["sensor_score"] == 0.0
