"""Resolve Gemini/OpenAI base URLs under LLM_USE_HEADROOM."""

from __future__ import annotations

import re

_HEADROOM_HINT = re.compile(r"headroom|:8787\b", re.I)

DEFAULT_GEMINI_BASE_URL = "https://generativelanguage.googleapis.com"
DEFAULT_OPENAI_BASE_URL = ""  # empty → OpenAI SDK default
HEADROOM_GEMINI_BASE_URL = "http://headroom:8787"
HEADROOM_OPENAI_BASE_URL = "http://headroom:8787/v1"


def llm_use_headroom(raw: str | None, *, default: bool = True) -> bool:
    if raw is None or raw == "":
        return default
    return raw not in ("false", "0", "False", "FALSE")


def looks_like_headroom(url: str) -> bool:
    return bool(_HEADROOM_HINT.search(url or ""))


def resolve_gemini_base_url(use_flag: str | None, configured: str | None) -> str:
    on = llm_use_headroom(use_flag, default=True)
    raw = (configured or "").strip().rstrip("/")
    if not on:
        if not raw or looks_like_headroom(raw):
            return DEFAULT_GEMINI_BASE_URL
        return raw
    return raw or HEADROOM_GEMINI_BASE_URL


def resolve_openai_base_url(use_flag: str | None, configured: str | None) -> str:
    on = llm_use_headroom(use_flag, default=True)
    raw = (configured or "").strip().rstrip("/")
    if not on:
        if not raw or looks_like_headroom(raw):
            return DEFAULT_OPENAI_BASE_URL
        return raw
    return raw or HEADROOM_OPENAI_BASE_URL
