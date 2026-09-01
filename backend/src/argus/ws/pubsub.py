"""Redis Pub/Sub bridge to WebSocket rooms."""

from __future__ import annotations

import asyncio
import json
import logging

from argus.services.redis import get_redis
from argus.services.ws_events import WS_ROOM_CHANNEL
from argus.ws.gateway import manager

logger = logging.getLogger(__name__)


async def run_pubsub_listener() -> None:
    redis = get_redis()
    pubsub = redis.pubsub()
    await pubsub.psubscribe("ws:room:*")
    logger.info("WebSocket pub/sub listener started")

    while True:
        message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
        if message is None:
            await asyncio.sleep(0.05)
            continue
        if message.get("type") != "pmessage":
            continue
        try:
            channel = message.get("channel", "")
            if isinstance(channel, bytes):
                channel = channel.decode()
            tenant_id = channel.rsplit(":", 1)[-1]
            data = message.get("data")
            if isinstance(data, bytes):
                data = data.decode()
            envelope = json.loads(data)
            await manager.broadcast(tenant_id, envelope)
        except Exception:
            logger.exception("Failed to forward pub/sub message")
