"""Untrusted-content fencing for LLM prompts."""

from __future__ import annotations

from argus.guardrails.registry import get_registry

FENCE_PROMPT_ID = "context.fence"


def fence(payload: str) -> str:
    """Wrap untrusted payload in the registry fence so it is marked as data."""
    template = get_registry().get_prompt(FENCE_PROMPT_ID)
    return template.replace("{{payload}}", payload)
