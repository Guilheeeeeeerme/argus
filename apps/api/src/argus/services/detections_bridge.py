"""Bridge Redis ``detections:positive`` → WebSocket ``detection.created``.

Runs inside the API process so triage MFE gets near-realtime fan-out without
polling Postgres.
"""

from __future__ import annotations

import asyncio
import json
import logging
from uuid import UUID

from redis.exceptions import ResponseError

from argus.services.redis import get_redis
from argus.services.stream import DETECTIONS_POSITIVE_GROUP, DETECTIONS_POSITIVE_STREAM
from argus.services.ws_events import publish_detection_created

logger = logging.getLogger(__name__)


def _decode(value: str | None, default=None):
    if value is None or value == "":
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


async def ensure_detections_group() -> None:
    redis = get_redis()
    try:
        await redis.xgroup_create(
            DETECTIONS_POSITIVE_STREAM,
            DETECTIONS_POSITIVE_GROUP,
            id="0",
            mkstream=True,
        )
    except ResponseError as exc:
        if "BUSYGROUP" not in str(exc):
            raise


async def run_detections_bridge(stop_event: asyncio.Event | None = None) -> None:
    await ensure_detections_group()
    redis = get_redis()
    consumer = "api-bridge-1"
    logger.info("detections bridge listening on %s", DETECTIONS_POSITIVE_STREAM)

    while True:
        if stop_event is not None and stop_event.is_set():
            return
        try:
            batches = await redis.xreadgroup(
                groupname=DETECTIONS_POSITIVE_GROUP,
                consumername=consumer,
                streams={DETECTIONS_POSITIVE_STREAM: ">"},
                count=10,
                block=2000,
            )
        except Exception:  # noqa: BLE001
            logger.exception("detections bridge xreadgroup failed")
            await asyncio.sleep(1)
            continue

        if not batches:
            continue

        for _stream, messages in batches:
            for message_id, fields in messages:
                try:
                    company_id = UUID(fields["company_id"])
                    detection_id = UUID(fields["detection_id"])
                    triage_case_id = UUID(fields["triage_case_id"])
                    await publish_detection_created(
                        company_id=company_id,
                        detection_id=detection_id,
                        triage_case_id=triage_case_id,
                        payload={
                            "clip_uri": fields.get("clip_uri"),
                            "summary": fields.get("summary"),
                            "confidence": _decode(fields.get("confidence")),
                            "prompt_hits": _decode(fields.get("prompt_hits"), []),
                            "establishment_id": fields.get("establishment_id"),
                            "camera_id": fields.get("camera_id"),
                        },
                    )
                    await redis.xack(
                        DETECTIONS_POSITIVE_STREAM,
                        DETECTIONS_POSITIVE_GROUP,
                        message_id,
                    )
                except Exception:  # noqa: BLE001
                    logger.exception("failed bridging detection message %s", message_id)
