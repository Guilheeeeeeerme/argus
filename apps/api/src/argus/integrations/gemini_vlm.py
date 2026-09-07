"""Google Gemini VLM integration with structured JSON output."""

from __future__ import annotations

import base64
import json
from typing import Any

import httpx

from argus.config import settings

GEMINI_API_ROOT = "https://generativelanguage.googleapis.com/v1beta/models"
REQUEST_TIMEOUT_SECONDS = 60


class GeminiVLMClient:
    def analyze(
        self,
        *,
        system_prompt: str,
        frame_uris: list[str],
        output_schema: dict[str, Any],
        model: str | None = None,
        user_context: str = "",
    ) -> dict[str, Any]:
        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is not configured")

        used_model = model or settings.gemini_model
        user_parts: list[dict[str, Any]] = []
        if user_context:
            user_parts.append({"text": user_context})
        user_parts.append(
            {
                "text": (
                    "Analyze the frame sequence and respond with JSON only. "
                    f"Schema: {json.dumps(output_schema)}"
                )
            }
        )
        for uri in frame_uris:
            mime_type, data = _inline_frame(uri)
            user_parts.append({"inline_data": {"mime_type": mime_type, "data": data}})

        payload = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": user_parts}],
            "generationConfig": {"responseMimeType": "application/json"},
        }
        response = httpx.post(
            f"{GEMINI_API_ROOT}/{used_model}:generateContent",
            headers={"x-goog-api-key": settings.gemini_api_key},
            json=payload,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        body = response.json()
        parts = _response_text_parts(body)
        return json.loads(parts)


def _response_text_parts(body: dict[str, Any]) -> str:
    candidates = body.get("candidates") or []
    if not candidates:
        raise ValueError("Gemini response contained no candidates")
    content = candidates[0].get("content") or {}
    parts = content.get("parts") or []
    texts = [part.get("text", "") for part in parts if isinstance(part, dict)]
    joined = "".join(texts).strip()
    if not joined:
        raise ValueError("Gemini response contained no text parts")
    return joined


def _inline_frame(uri: str) -> tuple[str, str]:
    """Resolve a frame URI to inline (mime_type, base64) data."""
    if uri.startswith("data:"):
        header, _, data = uri.partition(",")
        mime_type = header.removeprefix("data:").split(";", 1)[0] or "image/jpeg"
        return mime_type, data
    if uri.startswith(("http://", "https://")):
        mime_type, payload = _download_frame(uri)
        return mime_type, base64.b64encode(payload).decode("ascii")
    raise ValueError(f"Unsupported frame URI scheme for Gemini: {uri[:15]}")


def _download_frame(url: str) -> tuple[str, bytes]:
    response = httpx.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()
    mime_type = response.headers.get("content-type", "").split(";", 1)[0]
    if not mime_type.startswith("image/"):
        mime_type = "image/jpeg"
    return mime_type, response.content
