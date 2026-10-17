"""JEV (TypeSafe) System One client — closed Choice decisions only.

Direct transport to TypeSafe; never via Headroom. Post-VLM verify uses a
compact text state (prompt_hits / summary / edge signals) — not raw frames.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from argus_prompt_eval.config import settings

logger = logging.getLogger(__name__)

JEV_INPUT_USD_PER_MILLION = 0.042
DEFAULT_JEV_MODEL = "jev-1.13.0"
DEFAULT_JEV_BASE_URL = "https://api.typesafe.ai"
JEV_MODES = frozenset({"off", "shadow", "active"})


def parse_jev_mode(raw: str | None, has_key: bool) -> str:
    value = (raw or "").strip().lower()
    if not value:
        return "active" if has_key else "off"
    if value not in JEV_MODES:
        raise ValueError(f'invalid JEV mode "{value}" (expected off | shadow | active)')
    return value


def estimate_jev_usd(input_tokens: int | None) -> float | None:
    if input_tokens is None:
        return None
    return (input_tokens / 1_000_000) * JEV_INPUT_USD_PER_MILLION


class JevClient:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout_seconds: float | None = None,
        mode: str | None = None,
    ) -> None:
        self.api_key = (api_key if api_key is not None else settings.jev_api_key).strip()
        self.base_url = (
            base_url if base_url is not None else settings.jev_base_url
        ).rstrip("/")
        self.model = model if model is not None else settings.jev_model
        self.timeout_seconds = (
            timeout_seconds
            if timeout_seconds is not None
            else settings.jev_timeout_seconds
        )
        try:
            resolved = parse_jev_mode(
                mode if mode is not None else settings.jev_verify_mode,
                bool(self.api_key),
            )
        except ValueError:
            logger.error("invalid JEV_VERIFY_MODE; forcing off")
            resolved = "off"
        if resolved in {"shadow", "active"} and not self.api_key:
            logger.error("jev_key_missing:verify — forcing off")
            resolved = "off"
        self.mode = resolved

    def configured(self) -> bool:
        return bool(self.api_key)

    def decide_choice(
        self,
        state: Any,
        questions: dict[str, dict[str, Any]],
        *,
        mode: str | None = None,
    ) -> dict[str, Any]:
        use_mode = mode or self.mode
        if use_mode == "off":
            raise RuntimeError("jev_off: verify mode is off")
        if not self.api_key:
            raise RuntimeError("jev_unavailable: JEV_API_KEY not set")

        url = f"{self.base_url}/v1/systemone"
        payload = {"model": self.model, "state": state, "questions": questions}
        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.post(
                url,
                headers={
                    "content-type": "application/json",
                    "authorization": f"Bearer {self.api_key}",
                },
                json=payload,
            )
        if response.status_code >= 400:
            # Never log response body (may echo state).
            raise RuntimeError(f"JEV {response.status_code}: upstream error")
        data = response.json()
        answers = data.get("answers")
        if not isinstance(answers, dict):
            raise RuntimeError("jev answers: not an object")
        usage = data.get("usage") or {}
        input_tokens = usage.get("input_tokens")
        if not isinstance(input_tokens, int):
            input_tokens = None
        return {
            "answers": answers,
            "meta": {
                "provider": "jev",
                "mode": use_mode,
                "requested_model": self.model,
                "returned_model": data.get("model")
                if isinstance(data.get("model"), str)
                else None,
                "input_tokens": input_tokens,
                "estimated_usd": estimate_jev_usd(input_tokens),
            },
        }
