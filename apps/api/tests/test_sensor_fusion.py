"""Sensor validation and tenant-scoped temporal correlation."""

from datetime import datetime

import pytest
from argus.domain.schemas.admin import InboundWebhookRequest
from pydantic import ValidationError


def test_legacy_webhook_defaults():
    event = InboundWebhookRequest(kind="door")
    assert event.role == "context"
    assert event.confidence is None
    assert event.occurred_at is None


@pytest.mark.parametrize(
    "fields",
    [
        {"confidence": -0.1},
        {"confidence": 1.1},
        {"confidence": float("nan")},
        {"confidence": float("inf")},
        {"role": "ignore"},
        {"occurred_at": "2026-01-01T12:00:00"},
    ],
)
def test_invalid_sensor_fields_rejected(fields):
    with pytest.raises(ValidationError):
        InboundWebhookRequest(kind="door", **fields)


def event(**fields):
    return {
        "account_id": "tenant",
        "unit_id": "site",
        "camera_id": "cam",
        "occurred_at": "2026-01-01T12:00:00+00:00",
        "kind": "door",
        **fields,
    }


def buffer(**kwargs):
    from argus.services.sensor_fusion import SensorFusionBuffer

    return SensorFusionBuffer(**kwargs)


def match(buf, **kwargs):
    return buf.match(
        account_id="tenant",
        unit_id="site",
        camera_id="cam",
        timestamp=kwargs.pop("timestamp", "2026-01-01T12:00:00Z"),
        **kwargs,
    )


def test_matches_time_boundaries_and_scopes():
    buf = buffer()
    for fields in [
        {},
        {"camera_id": ""},
        {"account_id": "other"},
        {"unit_id": "other"},
        {"camera_id": "other"},
        {"occurred_at": "2026-01-01T11:59:55Z"},
        {"occurred_at": "2026-01-01T12:00:05Z"},
        {"occurred_at": "2026-01-01T12:00:05.001Z"},
    ]:
        buf.add(event(**fields))
    assert len(match(buf)) == 4
    assert match(buf, timestamp="bad") == []
    assert match(buf, timestamp=datetime(2026, 1, 1)) == []  # noqa: DTZ001 - reject naive timestamps


def test_legacy_received_time_and_bounded_retention():
    buf = buffer(max_events=2)
    for index in range(3):
        item = event(context_event_id=str(index), received_at="2026-01-01T12:00:00Z")
        item.pop("occurred_at")
        buf.add(item)
    assert [item["context_event_id"] for item in match(buf)] == ["1", "2"]


@pytest.mark.parametrize(
    "fields",
    [
        {"account_id": ""},
        {"unit_id": ""},
        {"occurred_at": "bad"},
        {"occurred_at": "2026-01-01T12:00:00"},
        {"confidence": "nan"},
        {"confidence": 2},
        {"role": "wrong"},
        {"camera_id": []},
    ],
)
def test_malformed_sensor_events_fail_closed(fields):
    buf = buffer()
    buf.add(event(**fields))
    assert match(buf) == []


def test_buffer_does_not_leak_mutation():
    buf = buffer()
    item = event(payload={"value": 1})
    buf.add(item)
    item["payload"]["value"] = 2
    found = match(buf)
    assert found[0]["payload"]["value"] == 1
    found[0]["payload"]["value"] = 3
    assert match(buf)[0]["payload"]["value"] == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("explicit", [False, True])
async def test_ingestion_publishes_sensor_fields_with_authenticated_scope(
    monkeypatch, explicit
):
    from types import SimpleNamespace
    from unittest.mock import AsyncMock
    from uuid import uuid4

    from argus.api import hooks
    from argus.domain.models import Camera, Unit, WebhookEndpoint

    account, site, camera, endpoint_id = [uuid4() for _ in range(4)]
    endpoint = SimpleNamespace(
        id=endpoint_id,
        account_id=account,
        unit_id=site,
        token_hash="hash",
        active=True,
    )
    rows = {
        WebhookEndpoint: endpoint,
        Unit: SimpleNamespace(account_id=account),
        Camera: SimpleNamespace(account_id=account, unit_id=site),
    }

    class Session:
        async def get(self, model, key):
            return rows[model]

        def add(self, item):
            item.id = uuid4()

        async def flush(self):
            pass

    async def database():
        yield Session()

    published = []

    async def publish(stream, fields):
        published.append((stream, fields))

    monkeypatch.setattr(hooks, "get_db", database)
    monkeypatch.setattr(hooks, "set_session_context", AsyncMock())
    monkeypatch.setattr(hooks, "verify_password", lambda token, hashed: True)
    monkeypatch.setattr(hooks, "xadd", publish)
    extra = (
        {"confidence": 0.8, "role": "trigger", "occurred_at": "2026-01-01T12:00:00Z"}
        if explicit
        else {}
    )
    result = await hooks.ingest_webhook(
        endpoint_id,
        InboundWebhookRequest(kind="door", camera_id=camera, **extra),
        "Bearer secret",
    )
    stream, fields = published[0]
    assert stream == "context:events"
    assert fields["account_id"] == str(account)
    assert fields["unit_id"] == str(site)
    assert fields["camera_id"] == str(camera)
    assert fields["context_event_id"] == str(result.id)
    assert fields["role"] == ("trigger" if explicit else "context")
    assert fields.get("confidence") == (0.8 if explicit else None)
    assert fields["occurred_at"] == (
        "2026-01-01T12:00:00+00:00" if explicit else fields["received_at"]
    )


def test_stream_groups_include_edge_and_candidates():
    import runpy
    from pathlib import Path

    from argus.services import stream

    setup = runpy.run_path(
        str(Path(__file__).resolve().parents[1] / "scripts/init_redis_streams.py")
    )
    assert ("frames:ready", "edge-cv") in setup["STREAMS"]
    assert ("context:events", "edge-cv") in setup["STREAMS"]
    assert ("candidates:ready", "prompt-eval") in setup["STREAMS"]
    assert stream.CANDIDATES_READY_STREAM == "candidates:ready"
