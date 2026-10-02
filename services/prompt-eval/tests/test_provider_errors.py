import asyncio
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import httpx
import pytest
from argus_prompt_eval import provider_router as router


def test_provider_failure_excludes_sensitive_payloads(monkeypatch, caplog):
    request = httpx.Request("POST", "https://provider.invalid?key=secret-test-key")
    response = httpx.Response(401, request=request)
    error = httpx.HTTPStatusError(
        "secret-test-key raw-frame-payload", request=request, response=response
    )
    client = Mock()
    client.analyze.side_effect = error
    monkeypatch.setattr(router, "resolve_llm_chain", lambda: [("gemini", client)])
    monkeypatch.setattr(router, "check_llm_allowance", AsyncMock(return_value=None))
    with pytest.raises(RuntimeError) as failure:
        asyncio.run(
            router.analyze_with_failover(
                redis=Mock(),
                company_id=uuid4(),
                system_prompt="private prompt",
                frame_uris=["private frame"],
                output_schema={},
            )
        )
    output = str(failure.value) + caplog.text
    assert "secret-test-key" not in output
    assert "raw-frame-payload" not in output
    assert "provider.invalid" not in output
    assert "401" in output
    assert "HTTPStatusError" in output
