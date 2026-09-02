"""OpenAI VLM client tests."""

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
