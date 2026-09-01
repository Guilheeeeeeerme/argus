"""Async Redis client for streams, pub/sub, and caching."""

from __future__ import annotations

import json
from typing import Any

from redis.asyncio import Redis

from argus.config import settings

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


async def ping() -> bool:
    return bool(await get_redis().ping())


async def get_key(key: str) -> str | None:
    return await get_redis().get(key)


async def set_key(key: str, value: str, *, ex: int | None = None) -> None:
    await get_redis().set(key, value, ex=ex)


async def set_key_nx(key: str, value: str, *, ex: int) -> bool:
    """Set key only if absent. Returns True when key was set."""
    return bool(await get_redis().set(key, value, nx=True, ex=ex))


async def delete_key(key: str) -> None:
    await get_redis().delete(key)


async def xadd(stream: str, fields: dict[str, Any], *, maxlen: int | None = None) -> str:
    payload = {k: json.dumps(v) if isinstance(v, (dict, list)) else str(v) for k, v in fields.items()}
    return await get_redis().xadd(stream, payload, maxlen=maxlen)


async def xreadgroup(
    group: str,
    consumer: str,
    streams: dict[str, str],
    *,
    count: int = 1,
    block_ms: int | None = 5000,
) -> list[tuple[str, list[tuple[str, dict[str, str]]]]]:
    return await get_redis().xreadgroup(
        groupname=group,
        consumername=consumer,
        streams=streams,
        count=count,
        block=block_ms,
    )


async def xack(stream: str, group: str, message_id: str) -> int:
    return await get_redis().xack(stream, group, message_id)


async def move_to_dlq(original_fields: dict[str, Any], *, error: str) -> str:
    from argus.services.stream import INGEST_DLQ_STREAM

    payload = {**original_fields, "error": error}
    return await xadd(INGEST_DLQ_STREAM, payload)


async def publish(channel: str, message: dict[str, Any]) -> int:
    return await get_redis().publish(channel, json.dumps(message))


async def subscribe(channel: str):
    pubsub = get_redis().pubsub()
    await pubsub.subscribe(channel)
    return pubsub
