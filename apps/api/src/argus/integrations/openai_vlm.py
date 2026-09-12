"""OpenAI VLM integration with structured JSON output."""

from __future__ import annotations

import json
from typing import Any, Protocol, runtime_checkable

from argus.config import settings
from argus.integrations.gemini_vlm import inline_frame

BIOMETRICS_PROHIBITION = "NEVER identify individuals"

# Hard ceilings on a single provider call; without them one request can hang a
# worker and emit unbounded output tokens (OWASP LLM06).
REQUEST_TIMEOUT_SECONDS = 60
MAX_OUTPUT_TOKENS = 2_048


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


class OpenAIVLMClient:
    def analyze(
        self,
        *,
        system_prompt: str,
        frame_uris: list[str],
        output_schema: dict[str, Any],
        model: str | None = None,
        user_context: str = "",
    ) -> dict[str, Any]:
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured")

        from openai import OpenAI

        client = OpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url or None,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        user_content: list[dict[str, Any]] = []
        if user_context:
            user_content.append({"type": "text", "text": user_context})
        user_content.append(
            {
                "type": "text",
                "text": (
                    "Analyze the frame sequence and respond with JSON only. "
                    f"Schema: {json.dumps(output_schema)}"
                ),
            }
        )
        for uri in frame_uris:
            # Always inline. Handing a raw URL to the provider would make its
            # fetcher a confused deputy for any host we did not allowlist, and
            # would leak which frames we request to that host (LLM01/LLM10).
            if uri.startswith("data:"):
                image_url = uri
            else:
                mime_type, data = inline_frame(uri)
                image_url = f"data:{mime_type};base64,{data}"
            user_content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": image_url},
                }
            )

        response = client.chat.completions.create(
            model=model or settings.openai_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            response_format={"type": "json_object"},
            max_completion_tokens=MAX_OUTPUT_TOKENS,
        )
        raw = response.choices[0].message.content or "{}"
        return json.loads(raw)


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
