"""Untrusted-content fencing for LLM prompts."""

from __future__ import annotations

import re

from argus.guardrails.registry import get_registry

FENCE_PROMPT_ID = "context.fence"

# The payload must never be able to emit the fence markers itself: a webhook
# ContextEvent containing END_UNTRUSTED_VLM_CONTEXT would otherwise close the
# data block early and have its remaining text read as instructions (LLM01).
_FENCE_MARKERS = re.compile(r"(BEGIN|END)_UNTRUSTED_VLM_CONTEXT")

# Invisible to a human reviewer, visible to the model: Unicode tag block
# (smuggled ASCII), zero-width characters, and bidi overrides. These are the
# encoding axis of prompt injection in OWASP LLM01.
_INVISIBLE = re.compile(
    "[\u200b-\u200f\u202a-\u202e\u2060-\u2064\u2066-\u2069\ufeff"
    "\U000e0000-\U000e007f]"
)


def neutralize(payload: str) -> str:
    """Strip invisible characters and defang fence markers in untrusted text."""
    return _FENCE_MARKERS.sub(
        r"\1_UNTRUSTED_VLM_CONTEXT_NEUTRALIZED", _INVISIBLE.sub("", payload)
    )


def fence(payload: str) -> str:
    """Wrap untrusted payload in the registry fence so it is marked as data."""
    template = get_registry().get_prompt(FENCE_PROMPT_ID)
    return template.replace("{{payload}}", neutralize(payload))
