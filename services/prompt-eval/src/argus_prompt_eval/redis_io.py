"""Redis stream I/O for frames:ready, context:events, detections:positive.

Consumes with XREADGROUP; publishes positives with XADD.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from redis.asyncio import Redis
from redis.exceptions import ResponseError

from argus_prompt_eval.config import settings

logger = logging.getLogger(__name__)

_client: Redis | None = None


def get_redis() -> Redis:
    global _client
    if _client is None:
        _client = Redis.from_url(settings.redis_url, decode_responses=True)
    return _client


async def close_redis() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


async def ensure_consumer_group(stream: str, group: str) -> None:
    redis = get_redis()
    try:
        await redis.xgroup_create(stream, group, id="0", mkstream=True)
        logger.info("Created consumer group %s on %s", group, stream)
    except ResponseError as exc:
        if "BUSYGROUP" not in str(exc):
            raise


async def xadd(
    stream: str, fields: dict[str, Any], *, maxlen: int | None = 10_000
) -> str:
    payload = {
        k: json.dumps(v) if isinstance(v, (dict, list)) else str(v)
        for k, v in fields.items()
    }
    return await get_redis().xadd(stream, payload, maxlen=maxlen)


async def xreadgroup(
    group: str,
    consumer: str,
    streams: dict[str, str],
    *,
    count: int | None = None,
    block_ms: int | None = None,
) -> list[tuple[str, list[tuple[str, dict[str, str]]]]]:
    return await get_redis().xreadgroup(
        groupname=group,
        consumername=consumer,
        streams=streams,
        count=count if count is not None else settings.consumer_batch_size,
        block=block_ms if block_ms is not None else settings.consumer_block_ms,
    )


async def claim_pending(
    stream: str, group: str, consumer: str, cursor: str
) -> tuple[str, list[tuple[str, dict[str, str]]]]:
    """Reclaim stale work from any consumer, scanning fairly across the PEL."""
    result = await get_redis().xautoclaim(
        stream,
        group,
        consumer,
        min_idle_time=settings.consumer_retry_idle_ms,
        start_id=cursor,
        count=settings.consumer_batch_size,
    )
    # Redis 7 also returns IDs already trimmed from the stream.
    return result[0], result[1]


async def xack(stream: str, group: str, message_id: str) -> int:
    return await get_redis().xack(stream, group, message_id)


def decode_json_field(value: str | None, default: Any = None) -> Any:
    if value is None or value == "":
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def parse_frames_ready(fields: dict[str, str]) -> dict[str, Any]:
    frame_uris = decode_json_field(fields.get("frame_uris"), [])
    if isinstance(frame_uris, str):
        frame_uris = [frame_uris]
    preproc_meta = decode_json_field(fields.get("preproc_meta"), {})
    if not isinstance(preproc_meta, dict):
        preproc_meta = {}
    return {
        "company_id": fields.get("company_id", ""),
        "establishment_id": fields.get("establishment_id", ""),
        "camera_id": fields.get("camera_id", ""),
        "sequence_id": fields.get("sequence_id", ""),
        "captured_at": fields.get("captured_at", ""),
        "frame_uris": list(frame_uris) if isinstance(frame_uris, list) else [],
        "preproc_meta": preproc_meta,
    }


def parse_context_event(fields: dict[str, str]) -> dict[str, Any]:
    payload = decode_json_field(fields.get("payload"), {})
    if not isinstance(payload, dict):
        payload = {"raw": payload}
    return {
        "company_id": fields.get("company_id", ""),
        "establishment_id": fields.get("establishment_id", ""),
        "camera_id": fields.get("camera_id") or None,
        "kind": fields.get("kind", "unknown"),
        "payload": payload,
        "received_at": fields.get("received_at", ""),
        "webhook_id": fields.get("webhook_id") or None,
    }


async def publish_detection_positive(fields: dict[str, Any]) -> str:
    return await xadd(settings.detections_stream, fields)


def parse_candidates_ready(fields: dict[str, str]) -> dict[str, Any]:
    """Strict edge wire contract; tenant-mismatched or malformed evidence is rejected."""
    import math
    from datetime import datetime
    from uuid import UUID

    from argus_prompt_eval.consensus import probability

    payload = parse_frames_ready(fields)
    for key in ("company_id", "establishment_id", "camera_id"):
        UUID(payload[key])
    if not payload["sequence_id"] or not payload["captured_at"]:
        raise ValueError("missing sequence metadata")
    captured = datetime.fromisoformat(payload["captured_at"].replace("Z", "+00:00"))
    if captured.tzinfo is None:
        raise ValueError("timestamp requires timezone")
    for key in ("frame_uris", "tracks", "sensors", "sensor_ids"):
        value = json.loads(fields[key])
        if not isinstance(value, list):
            raise TypeError("candidate field must be an array")
        payload[key] = value
    if not 1 <= len(payload["frame_uris"]) <= 3 or not all(
        isinstance(uri, str) and uri for uri in payload["frame_uris"]
    ):
        raise ValueError("invalid keyframes")
    if not all(isinstance(value, str) for value in payload["sensor_ids"]):
        raise ValueError("invalid sensor ids")
    payload["edge_score"] = probability(fields["edge_score"])
    payload["motion_score"] = probability(fields["motion_score"])
    span = float(fields["temporal_span_seconds"])
    if not math.isfinite(span) or span < 0:
        raise ValueError("invalid temporal span")
    payload["temporal_span_seconds"] = span
    if not payload["tracks"]:
        raise ValueError("missing tracks")
    for track in payload["tracks"]:
        if not isinstance(track, dict) or not isinstance(track.get("class_name"), str):
            raise TypeError("invalid track")
        probability(track.get("confidence"))
        bbox = track.get("bbox")
        if (
            not isinstance(bbox, list)
            or len(bbox) != 4
            or not all(
                isinstance(v, (int, float))
                and not isinstance(v, bool)
                and math.isfinite(v)
                for v in bbox
            )
        ):
            raise ValueError("invalid track box")
    frame_times = [captured]
    metadata = payload["preproc_meta"].get("frames")
    if metadata is not None:
        if not isinstance(metadata, list) or len(metadata) != len(
            payload["frame_uris"]
        ):
            raise ValueError("invalid frame metadata")
        frame_times = []
        for frame in metadata:
            if not isinstance(frame, dict) or not isinstance(
                frame.get("captured_at"), str
            ):
                raise TypeError("invalid frame timestamp")
            frame_time = datetime.fromisoformat(
                frame["captured_at"].replace("Z", "+00:00")
            )
            if frame_time.tzinfo is None:
                raise ValueError("frame timestamp requires timezone")
            frame_times.append(frame_time)
    sensor_score, veto = 0.0, False
    for sensor in payload["sensors"]:
        if not isinstance(sensor, dict):
            raise TypeError("invalid sensor")
        if (
            sensor.get("company_id") != payload["company_id"]
            or sensor.get("establishment_id") != payload["establishment_id"]
        ):
            raise ValueError("sensor tenant mismatch")
        if sensor.get("camera_id") not in (None, "", payload["camera_id"]):
            raise ValueError("sensor camera mismatch")
        role = sensor.get("role", "context")
        if role not in ("trigger", "filter", "context") or not isinstance(
            sensor.get("payload"), dict
        ):
            raise ValueError("invalid sensor role or payload")
        event_time = sensor.get("occurred_at", sensor.get("received_at"))
        if not isinstance(event_time, str):
            raise TypeError("missing sensor timestamp")
        occurred = datetime.fromisoformat(event_time.replace("Z", "+00:00"))
        if occurred.tzinfo is None or not any(
            abs((occurred - frame_time).total_seconds())
            <= settings.sensor_fusion_window_seconds
            for frame_time in frame_times
        ):
            raise ValueError("sensor outside candidate time window")
        confidence = (
            probability(sensor["confidence"])
            if sensor.get("confidence") is not None
            else 0.0
        )
        if role == "trigger":
            sensor_score = max(sensor_score, confidence)
        if role == "filter":
            data = sensor["payload"]
            for key in ("reject", "accepted"):
                if key in data and type(data[key]) is not bool:
                    raise ValueError("invalid filter decision")
            veto = veto or data.get("reject") is True or data.get("accepted") is False
    payload["sensor_score"], payload["sensor_veto"] = sensor_score, veto
    return payload
