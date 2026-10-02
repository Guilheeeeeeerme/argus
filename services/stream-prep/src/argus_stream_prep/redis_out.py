"""Publish completed frame sequences onto Redis stream ``frames:ready``."""

from __future__ import annotations

import json
import logging
from typing import Any

import redis

from argus_stream_prep.config import Settings, get_settings

logger = logging.getLogger(__name__)

FRAMES_READY_STREAM = "frames:ready"
LATEST_FRAME_KEY = "frame:latest:{camera_id}"


def latest_frame_key(camera_id: str) -> str:
    """Hash holding the newest frame pointer for one camera (``HSET`` + ``EXPIRE``)."""
    return LATEST_FRAME_KEY.format(camera_id=camera_id)


class RedisOut:
    """Thin wrapper around Redis ``XADD`` for ``frames:ready``."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._client = redis.Redis.from_url(self.settings.redis_url, decode_responses=True)

    def close(self) -> None:
        self._client.close()

    def publish_frames_ready(
        self,
        *,
        company_id: str,
        establishment_id: str,
        camera_id: str,
        sequence_id: str,
        captured_at: str,
        frame_uris: list[str],
        preproc_meta: dict[str, Any] | list[dict[str, Any]],
    ) -> str:
        """XADD one sequence message; returns the stream entry id."""
        fields = {
            "company_id": company_id,
            "establishment_id": establishment_id,
            "camera_id": camera_id,
            "sequence_id": sequence_id,
            "captured_at": captured_at,
            "frame_uris": json.dumps(frame_uris),
            "preproc_meta": json.dumps(preproc_meta),
        }
        entry_id = self._client.xadd(FRAMES_READY_STREAM, fields)
        logger.info(
            "XADD %s sequence=%s camera=%s frames=%d id=%s",
            FRAMES_READY_STREAM,
            sequence_id,
            camera_id,
            len(frame_uris),
            entry_id,
        )
        return entry_id

    def set_latest_frame(
        self,
        *,
        camera_id: str,
        uri: str,
        captured_at: str,
        company_id: str,
        establishment_id: str,
        ttl_seconds: int,
    ) -> None:
        """``HSET frame:latest:{camera_id}`` with the newest pointer and refresh its TTL."""
        key = latest_frame_key(camera_id)
        pipe = self._client.pipeline(transaction=True)
        pipe.hset(
            key,
            mapping={
                "uri": uri,
                "captured_at": captured_at,
                "company_id": company_id,
                "establishment_id": establishment_id,
            },
        )
        pipe.expire(key, max(int(ttl_seconds), 1))
        pipe.execute()
