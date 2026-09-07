"""LLM provider chain and model rank tests."""

from __future__ import annotations

import pytest
import pytest_asyncio

from argus.config import Settings
from argus.integrations.gemini_vlm import GeminiVLMClient
from argus.integrations.llm_provider import primary_provider_name, resolve_llm_chain
from argus.integrations.model_rank import compute_rank, rank_for
from argus.integrations.openai_vlm import MockVLMClient, OpenAIVLMClient
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
        "OPENAI_API_KEY": "oai-key",
        "LLM_PROVIDER_ORDER": "gemini,openai",
        "AUTH0_USE_MOCK": False,
    }
    values.update(overrides)
    return Settings(**values)


def test_chain_orders_gemini_first_openai_fallback() -> None:
    chain = resolve_llm_chain(_settings())
    names = [name for name, _client in chain]
    assert names == ["gemini", "openai"]
    assert isinstance(chain[0][1], GeminiVLMClient)
    assert isinstance(chain[1][1], OpenAIVLMClient)


def test_chain_skips_keyless_providers() -> None:
    chain = resolve_llm_chain(_settings(GEMINI_API_KEY=""))
    assert [name for name, _client in chain] == ["openai"]


def test_chain_respects_order_override_and_ignores_unknown() -> None:
    chain = resolve_llm_chain(
        _settings(LLM_PROVIDER_ORDER="openai,gossip,gemini")
    )
    assert [name for name, _client in chain] == ["openai", "gemini"]


def test_chain_falls_back_to_mock_when_enabled() -> None:
    chain = resolve_llm_chain(
        _settings(GEMINI_API_KEY="", OPENAI_API_KEY="", AUTH0_USE_MOCK=True)
    )
    assert [name for name, _client in chain] == ["mock"]
    assert isinstance(chain[0][1], MockVLMClient)


def test_chain_raises_when_no_provider_and_not_mock() -> None:
    with pytest.raises(RuntimeError):
        resolve_llm_chain(_settings(GEMINI_API_KEY="", OPENAI_API_KEY=""))


def test_primary_provider_name_matches_chain_head() -> None:
    assert primary_provider_name(_settings()) == "gemini"
    assert primary_provider_name(_settings(GEMINI_API_KEY="")) == "openai"
    assert primary_provider_name(_settings(GEMINI_API_KEY="", OPENAI_API_KEY="")) == "mock"


def test_compute_rank_is_cheapest_first_with_top_n(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("argus.integrations.model_rank.settings", _settings())
    monkeypatch.setattr("argus.integrations.model_rank.settings.model_rank_top_n", 2)
    assert compute_rank("openai") == ["gpt-5-nano", "gpt-4.1-nano"]
    assert compute_rank("gemini")[0] == "gemini-2.5-flash-lite"


@pytest.mark.asyncio
async def test_rank_for_falls_back_to_seed_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("argus.integrations.model_rank.settings", _settings())
    rank = await rank_for("gemini")
    assert rank[0] == "gemini-2.5-flash-lite"
    assert len(rank) >= 2
