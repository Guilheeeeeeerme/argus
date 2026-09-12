"""OpenAI VLM client tests."""

import pytest

from argus.config import settings
from argus.integrations import openai_vlm
from argus.integrations.openai_vlm import MockVLMClient


def test_mock_vlm_returns_structured_output() -> None:
    client = MockVLMClient()
    result = client.analyze(
        system_prompt="test",
        frame_uris=["s3://bucket/frame.bin"],
        output_schema={"type": "object"},
    )
    assert result["is_suspicious"] is True
    assert "confidence_score" in result
    assert "reasoning" in result


@pytest.fixture
def no_allowlist(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "openai_api_key", "test-key", raising=False)
    monkeypatch.setattr(settings, "s3_endpoint_url", "", raising=False)
    monkeypatch.setattr(settings, "s3_public_endpoint_url", "", raising=False)
    monkeypatch.setattr(settings, "frame_http_allowlist", "", raising=False)


def _analyze(uri: str) -> None:
    openai_vlm.OpenAIVLMClient().analyze(
        system_prompt="test",
        frame_uris=[uri],
        output_schema={"type": "object"},
    )


@pytest.mark.usefixtures("no_allowlist")
def test_link_local_frame_is_rejected() -> None:
    """Cloud metadata must not be reachable through the provider (LLM01)."""
    with pytest.raises(ValueError, match="blocked address"):
        _analyze("http://169.254.169.254/latest/meta-data/")


@pytest.mark.usefixtures("no_allowlist")
def test_non_allowlisted_host_is_rejected() -> None:
    """A raw URL must never be handed to the provider's fetcher (LLM01)."""
    with pytest.raises(ValueError, match="not allowlisted"):
        _analyze("https://attacker.example/frame.jpg")
