"""Deterministic VLM client for tests and mock auth mode."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class VLMClient(Protocol):
    def analyze(
        self,
        *,
        system_prompt: str,
        frame_uris: list[str],
        output_schema: dict[str, Any],
    ) -> dict[str, Any]:
        """Return structured VLM analysis JSON."""


class MockVLMClient:
    """Deterministic VLM client for tests."""

    def __init__(self, response: dict[str, Any] | None = None) -> None:
        self.response = response or {
            "is_suspicious": True,
            "detection_class": "loitering",
            "confidence_score": 0.91,
            "reasoning": "Suspicious loitering detected near restricted shelf area.",
            "severity_hint": 3,
        }
        self.calls: list[dict[str, Any]] = []

    def analyze(
        self,
        *,
        system_prompt: str,
        frame_uris: list[str],
        output_schema: dict[str, Any],
        model: str | None = None,
        user_context: str = "",
    ) -> dict[str, Any]:
        self.calls.append(
            {
                "system_prompt": system_prompt,
                "frame_uris": frame_uris,
                "output_schema": output_schema,
                "model": model,
                "user_context": user_context,
            }
        )
        # Fixture names make the browser smoke test deterministic without a provider.
        joined_uris = " ".join(frame_uris).lower()
        signal = f"{joined_uris} {system_prompt}".lower()
        if "normal" in signal:
            return {**self.response, "is_suspicious": False, "severity_hint": 0}
        if "weird" in signal:
            return {**self.response, "is_suspicious": True, "severity_hint": 1}
        if "warning" in signal or "high" in signal:
            return {**self.response, "is_suspicious": True, "severity_hint": 4}
        return dict(self.response)
