#!/usr/bin/env python3
"""Create Redis Stream consumer groups for the MVP pipeline."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from redis.exceptions import ResponseError  # noqa: E402

from argus.services.redis import close_redis, get_redis  # noqa: E402

STREAMS = (
    ("frames:ready", "prompt-eval"),
    ("context:events", "prompt-eval"),
    ("detections:positive", "api-bridge"),
)


async def ensure_group(stream: str, group: str) -> None:
    redis = get_redis()
    try:
        await redis.xgroup_create(stream, group, id="0", mkstream=True)
        print(f"Created consumer group {group} on {stream}")
    except ResponseError as exc:
        if "BUSYGROUP" in str(exc):
            print(f"Consumer group {group} already exists on {stream}")
        else:
            raise


async def main() -> int:
    try:
        for stream, group in STREAMS:
            await ensure_group(stream, group)
    finally:
        await close_redis()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
