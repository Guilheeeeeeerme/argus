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


async def xadd(stream: str, fields: dict[str, Any], *, maxlen: int | None = 10_000) -> str:
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
