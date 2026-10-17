"""LLM provider chain resolution. Fails closed when no provider is usable."""

from __future__ import annotations

from argus.config import Settings, settings
from argus.integrations.gemini_vlm import GeminiVLMClient
from argus.integrations.mock_vlm import MockVLMClient, VLMClient


def _provider_chain(names: list[str], s: Settings) -> list[tuple[str, VLMClient]]:
    chain: list[tuple[str, VLMClient]] = []
    for name in names:
        if name == "gemini" and s.gemini_api_key:
            chain.append(("gemini", GeminiVLMClient()))
    return chain


def resolve_llm_chain(
    s: Settings | None = None,
) -> list[tuple[str, VLMClient]]:
    """Gemini when a key is set; mock only when AUTH0_USE_MOCK is on."""
    target = s or settings
    chain = _provider_chain(["gemini"], target)
    if chain:
        return chain
    if target.auth0_use_mock:
        return [("mock", MockVLMClient())]
    raise RuntimeError(
        "No LLM provider configured: set GEMINI_API_KEY "
        "(mock fallback requires AUTH0_USE_MOCK)"
    )


def primary_provider_name(s: Settings | None = None) -> str:
    target = s or settings
    if target.gemini_api_key:
        return "gemini"
    return "mock"
