"""Unit tests for VLM result sanitization and confidence floor."""

from __future__ import annotations

from types import SimpleNamespace

from argus.services.recipe_builder import compute_severity_score, sanitize_vlm_result


def test_sanitize_drops_unknown_keys_and_clamps_confidence() -> None:
    cleaned = sanitize_vlm_result(
        {
            "is_suspicious": 1,
            "confidence_score": 4.2,
            "shell": "rm -rf /",
            "detection_class": "intrusion",
        }
    )
    assert "shell" not in cleaned
    assert cleaned["confidence_score"] == 1.0
    assert cleaned["is_suspicious"] is True


def test_hint_requires_min_confidence(monkeypatch) -> None:
    from argus import config

    monkeypatch.setattr(config.settings, "vlm_min_confidence_for_hint", 0.8)
    rules: list = []
    low = compute_severity_score(
        {"is_suspicious": True, "confidence_score": 0.2, "severity_hint": 3},
        rules,
    )
    assert low == 0
    high = compute_severity_score(
        {"is_suspicious": True, "confidence_score": 0.9, "severity_hint": 3},
        rules,
    )
    assert high == 3
