#!/usr/bin/env python3
"""Sync API stream configs into go2rtc (stream-gateway).

Polls ``GET /v1/internal/stream-configs`` and:
1. Rewrites ``go2rtc.yaml`` streams section (durable).
2. PUTs each stream into the live go2rtc HTTP API for hot reload.
"""

from __future__ import annotations

import logging
import os
import signal
import time
from typing import Any
from urllib.parse import quote, urlparse, urlunparse

import httpx
import yaml

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s [stream-gateway-sync] %(message)s",
)
logger = logging.getLogger("stream-gateway-sync")

API_INTERNAL_URL = os.environ.get("API_INTERNAL_URL", "http://api:8000").rstrip("/")
STREAM_GATEWAY_URL = os.environ.get("STREAM_GATEWAY_URL", "http://stream-gateway:1984").rstrip("/")
STREAM_GATEWAY_TOKEN = os.environ.get("STREAM_GATEWAY_TOKEN", "dev-stream-gateway-token")
POLL_INTERVAL = float(os.environ.get("POLL_INTERVAL", "30"))
CONFIG_PATH = os.environ.get("GO2RTC_CONFIG_PATH", "/config/go2rtc.yaml")


def _auth_url(stream_url: str, username: str | None, password: str | None) -> str:
    if not username:
        return stream_url
    parsed = urlparse(stream_url)
    if parsed.username:
        return stream_url
    netloc = f"{quote(username, safe='')}:{quote(password or '', safe='')}@{parsed.hostname}"
    if parsed.port:
        netloc += f":{parsed.port}"
    return urlunparse(parsed._replace(netloc=netloc))


def fetch_configs(client: httpx.Client) -> list[dict[str, Any]]:
    response = client.get(
        f"{API_INTERNAL_URL}/v1/internal/stream-configs",
        headers={"X-Stream-Gateway-Token": STREAM_GATEWAY_TOKEN},
        timeout=15.0,
    )
    response.raise_for_status()
    return list(response.json())


def write_config_file(streams: dict[str, str]) -> None:
    base: dict[str, Any] = {
        "api": {"listen": ":1984"},
        "rtsp": {"listen": ":8554"},
        "webrtc": {"listen": ":8555"},
        "streams": streams,
    }
    if os.path.isfile(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, encoding="utf-8") as fh:
                loaded = yaml.safe_load(fh) or {}
            if isinstance(loaded, dict):
                base = {**loaded, "streams": streams}
        except Exception:  # noqa: BLE001
            logger.exception("failed reading existing %s; rewriting", CONFIG_PATH)
    os.makedirs(os.path.dirname(CONFIG_PATH) or ".", exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as fh:
        yaml.safe_dump(base, fh, default_flow_style=False)
    logger.info("wrote %d stream(s) to %s", len(streams), CONFIG_PATH)


def put_live_streams(client: httpx.Client, streams: dict[str, str]) -> None:
    for name, src in streams.items():
        try:
            # go2rtc: PUT /api/streams?name=<id>&src=<url>
            response = client.put(
                f"{STREAM_GATEWAY_URL}/api/streams",
                params={"name": name, "src": src},
                timeout=10.0,
            )
            if response.status_code >= 400:
                logger.warning(
                    "go2rtc PUT stream %s failed: %s %s",
                    name,
                    response.status_code,
                    response.text[:200],
                )
        except Exception:  # noqa: BLE001
            logger.exception("go2rtc PUT failed for %s", name)


def sync_once(client: httpx.Client) -> None:
    configs = fetch_configs(client)
    streams: dict[str, str] = {}
    for item in configs:
        stream_url = item.get("stream_url")
        if not stream_url:
            continue
        camera_id = str(item["camera_id"])
        streams[camera_id] = _auth_url(
            stream_url,
            item.get("username"),
            item.get("password"),
        )
    write_config_file(streams)
    put_live_streams(client, streams)


def main() -> None:
    stop = False

    def _stop(signum: int, _frame: object) -> None:
        nonlocal stop
        logger.info("signal %s; exiting", signum)
        stop = True

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    logger.info(
        "sync starting api=%s gateway=%s interval=%.1fs",
        API_INTERNAL_URL,
        STREAM_GATEWAY_URL,
        POLL_INTERVAL,
    )
    with httpx.Client() as client:
        while not stop:
            try:
                sync_once(client)
            except Exception:  # noqa: BLE001
                logger.exception("sync iteration failed")
            # Interruptible sleep
            deadline = time.monotonic() + POLL_INTERVAL
            while not stop and time.monotonic() < deadline:
                time.sleep(0.5)


if __name__ == "__main__":
    main()
