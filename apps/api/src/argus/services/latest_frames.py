"""Read the per-camera latest-frame pointers written by stream-prep.

stream-prep keeps ``HSET frame:latest:{camera_id} {uri, captured_at, company_id,
establishment_id}`` with a short TTL; an absent hash means the camera has no
recent signal.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from argus.services.redis import get_redis

LATEST_FRAME_KEY = "frame:latest:{camera_id}"


def latest_frame_key(camera_id: UUID | str) -> str:
    return LATEST_FRAME_KEY.format(camera_id=camera_id)


@dataclass(frozen=True)
class LatestFrame:
    camera_id: str
    uri: str
    captured_at: str
    company_id: str | None = None
    establishment_id: str | None = None

    def captured_at_datetime(self) -> datetime | None:
        try:
            return datetime.fromisoformat(self.captured_at)
        except ValueError:
            return None


def _from_hash(camera_id: str, fields: dict[str, str] | None) -> LatestFrame | None:
    if not fields or not fields.get("uri") or not fields.get("captured_at"):
        return None
    return LatestFrame(
        camera_id=camera_id,
        uri=fields["uri"],
        captured_at=fields["captured_at"],
        company_id=fields.get("company_id") or None,
        establishment_id=fields.get("establishment_id") or None,
    )


async def get_latest_frame(camera_id: UUID | str) -> LatestFrame | None:
    fields = await get_redis().hgetall(latest_frame_key(camera_id))
    return _from_hash(str(camera_id), fields)


async def get_latest_frames(camera_ids: Iterable[UUID | str]) -> dict[str, LatestFrame]:
    """One pipelined ``HGETALL`` per camera; cameras without a hash are omitted."""
    ids = [str(camera_id) for camera_id in camera_ids]
    if not ids:
        return {}
    pipe = get_redis().pipeline(transaction=False)
    for camera_id in ids:
        pipe.hgetall(latest_frame_key(camera_id))
    results = await pipe.execute()
    frames: dict[str, LatestFrame] = {}
    for camera_id, fields in zip(ids, results, strict=True):
        frame = _from_hash(camera_id, fields)
        if frame is not None:
            frames[camera_id] = frame
    return frames
