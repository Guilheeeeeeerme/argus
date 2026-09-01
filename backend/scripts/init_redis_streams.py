#!/usr/bin/env python3
"""Create Redis Stream consumer groups for ingestion pipeline."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from redis.exceptions import ResponseError  # noqa: E402

from argus.services.redis import close_redis, get_redis  # noqa: E402
from argus.services.stream import INGEST_CONSUMER_GROUP, INGEST_STREAM  # noqa: E402


async def main() -> int:
    redis = get_redis()
    try:
        await redis.xgroup_create(
            INGEST_STREAM,
            INGEST_CONSUMER_GROUP,
            id="0",
            mkstream=True,
        )
        print(f"Created consumer group {INGEST_CONSUMER_GROUP} on {INGEST_STREAM}")
    except ResponseError as exc:
        if "BUSYGROUP" in str(exc):
            print(f"Consumer group {INGEST_CONSUMER_GROUP} already exists on {INGEST_STREAM}")
        else:
            raise
    finally:
        await close_redis()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
