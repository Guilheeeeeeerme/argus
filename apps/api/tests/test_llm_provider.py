"""LLM provider chain tests (Gemini-only; model pinned via GEMINI_MODEL)."""

from __future__ import annotations

import pytest
import pytest_asyncio

from argus.config import Settings
from argus.integrations.gemini_vlm import GeminiVLMClient
from argus.integrations.llm_provider import primary_provider_name, resolve_llm_chain
from argus.integrations.mock_vlm import MockVLMClient
from argus.services.database import dispose_engine
from argus.services.redis import close_redis


@pytest_asyncio.fixture(autouse=True)
async def _cleanup():
    yield
    await close_redis()
    await dispose_engine()


def _settings(**overrides) -> Settings:
    values = {
        "GEMINI_API_KEY": "gem-key",
        "LLM_PROVIDER_ORDER": "gemini",
        "AUTH0_USE_MOCK": False,
    }
    values.update(overrides)
    return Settings(**values)


def test_chain_returns_gemini_only() -> None:
    chain = resolve_llm_chain(_settings())
    names = [name for name, _client in chain]
    assert names == ["gemini"]
    assert isinstance(chain[0][1], GeminiVLMClient)


def test_chain_skips_unknown_and_keyless_providers() -> None:
    chain = resolve_llm_chain(
        _settings(LLM_PROVIDER_ORDER="openai,gossip,gemini", GEMINI_API_KEY="gem-key")
    )
    assert [name for name, _client in chain] == ["gemini"]


def test_chain_ignores_retired_openai_name() -> None:
    with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
        resolve_llm_chain(
            _settings(LLM_PROVIDER_ORDER="openai", GEMINI_API_KEY="", AUTH0_USE_MOCK=False)
        )


def test_chain_falls_back_to_mock_when_enabled() -> None:
    chain = resolve_llm_chain(
        _settings(GEMINI_API_KEY="", AUTH0_USE_MOCK=True)
    )
    assert [name for name, _client in chain] == ["mock"]
    assert isinstance(chain[0][1], MockVLMClient)


def test_chain_raises_when_no_provider_and_not_mock() -> None:
    with pytest.raises(RuntimeError):
        resolve_llm_chain(_settings(GEMINI_API_KEY=""))


def test_primary_provider_name_matches_chain_head() -> None:
    assert primary_provider_name(_settings()) == "gemini"
    assert primary_provider_name(_settings(GEMINI_API_KEY="")) == "mock"


def test_gemini_model_defaults_to_pinned_flash_lite() -> None:
    assert _settings().gemini_model == "gemini-3.5-flash-lite"
