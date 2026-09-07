import pytest
from fastapi import HTTPException

from argus.api.triage.decisions import get_evidence_playback


class FakeSession:
    def __init__(self, evidence, linked=True):
        self.evidence = evidence
        self.linked = linked

    async def get(self, _model, _identifier):
        return self.evidence

    async def scalar(self, _statement):
        return self.evidence if self.linked else None


@pytest.mark.asyncio
async def test_playback_rejects_evidence_not_linked_to_decision(monkeypatch) -> None:
    evidence = object()
    session = FakeSession(evidence, linked=False)

    async def fail_if_called(_key):
        raise AssertionError("presigned URL must not be generated")

    monkeypatch.setattr(
        "argus.api.triage.decisions.generate_presigned_get_url", fail_if_called
    )

    with pytest.raises(HTTPException) as exc:
        await get_evidence_playback(
            decision_id="decision-id",
            evidence_id="evidence-id",
            session=session,
            _auth=None,
        )
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_playback_returns_url_for_linked_evidence(monkeypatch) -> None:
    class LinkedEvidence:
        frame_storage_uri = "s3://argus-frames/tenant/camera/ingestion/0.bin"

    session = FakeSession(LinkedEvidence())
    monkeypatch.setattr(
        "argus.api.triage.decisions.generate_presigned_get_url",
        lambda key: __import__("asyncio").sleep(0, result=f"https://example.test/{key}"),
    )
    result = await get_evidence_playback(
        decision_id="decision-id",
        evidence_id="evidence-id",
        session=session,
        _auth=None,
    )
    assert result["playback_url"].startswith("https://example.test/")
