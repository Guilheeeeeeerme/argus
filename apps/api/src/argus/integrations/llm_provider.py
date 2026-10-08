"""LLM provider chain resolution. Fails closed when no provider is usable."""

from __future__ import annotations

from argus.config import Settings, settings
from argus.integrations.gemini_vlm import GeminiVLMClient
from argus.integrations.mock_vlm import MockVLMClient, VLMClient

_KNOWN_PROVIDERS = ("gemini",)


def _provider_chain(names: list[str], s: Settings) -> list[tuple[str, VLMClient]]:
    chain: list[tuple[str, VLMClient]] = []
    for name in names:
        if name == "gemini" and s.gemini_api_key:
            chain.append(("gemini", GeminiVLMClient()))
    return chain


def resolve_llm_chain(
    s: Settings | None = None,
) -> list[tuple[str, VLMClient]]:
    """Ordered (provider_name, client) chain; unknown names and keyless providers skipped."""
    target = s or settings
    names = [n.strip().lower() for n in target.llm_provider_order.split(",") if n.strip()]
    chain = _provider_chain(names, target)
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
    names = [n.strip().lower() for n in target.llm_provider_order.split(",") if n.strip()]
    for name in names:
        if name in _KNOWN_PROVIDERS and target.gemini_api_key:
            return name
    return "mock"
