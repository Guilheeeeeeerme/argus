"""Main loop: poll cameras / consume go2rtc snapshots → preprocess → store → Redis."""

from __future__ import annotations

import logging
import signal
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx

from argus_stream_prep.config import Settings, get_settings
from argus_stream_prep.gateway_client import GatewayClient
from argus_stream_prep.preprocessing import PreprocMeta, preprocess_frame
from argus_stream_prep.redis_out import RedisOut
from argus_stream_prep.storage import FrameStorage
from argus_stream_prep.temporal_window import FrameSample, TemporalWindowBuffer

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StreamConfig:
    """Active camera stream identity from ``GET /v1/internal/stream-configs``."""

    camera_id: str
    company_id: str
    establishment_id: str
    name: str
    stream_url: str | None = None


@dataclass(frozen=True)
class PreparedFrame:
    """Preprocessed JPEG ready for windowing / upload."""

    jpeg_bytes: bytes
    meta: PreprocMeta


def fetch_stream_configs(settings: Settings) -> list[StreamConfig]:
    """Pull active camera configs from the API (gateway token auth)."""
    url = f"{settings.api_internal_url.rstrip('/')}/v1/internal/stream-configs"
    headers = {"X-Stream-Gateway-Token": settings.stream_gateway_token}
    with httpx.Client(timeout=15.0) as client:
        response = client.get(url, headers=headers)
        response.raise_for_status()
        payload = response.json()
    configs: list[StreamConfig] = []
    for item in payload:
        configs.append(
            StreamConfig(
                camera_id=str(item["camera_id"]),
                company_id=str(item["company_id"]),
                establishment_id=str(item["establishment_id"]),
                name=str(item.get("name") or item["camera_id"]),
                stream_url=item.get("stream_url"),
            )
        )
    return configs


def _publish_window(
    window: Any,
    *,
    storage: FrameStorage,
    redis_out: RedisOut,
    settings: Settings,
) -> None:
    frame_uris: list[str] = []
    metas: list[dict[str, Any]] = []
    for index, sample in enumerate(window.frames):
        prepared: PreparedFrame = sample.payload
        uri = storage.upload_frame(
            company_id=window.company_id,
            establishment_id=window.establishment_id,
            camera_id=window.camera_id,
            sequence_id=window.sequence_id,
            index=index,
            jpeg_bytes=prepared.jpeg_bytes,
            frame_ttl_seconds=settings.frame_ttl_seconds,
        )
        frame_uris.append(uri)
        metas.append(prepared.meta.to_dict())

    captured_at = window.captured_at
    if captured_at.tzinfo is None:
        captured_at = captured_at.replace(tzinfo=timezone.utc)
    redis_out.publish_frames_ready(
        company_id=window.company_id,
        establishment_id=window.establishment_id,
        camera_id=window.camera_id,
        sequence_id=window.sequence_id,
        captured_at=captured_at.isoformat(),
        frame_uris=frame_uris,
        preproc_meta={"frames": metas, "frame_ttl_seconds": settings.frame_ttl_seconds},
    )


def run_loop(settings: Settings | None = None) -> None:
    """Poll stream configs, sample frames, window, upload, and XADD."""
    settings = settings or get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )

    stop = False

    def _handle_stop(signum: int, _frame: object) -> None:
        nonlocal stop
        logger.info("received signal %s; shutting down", signum)
        stop = True

    signal.signal(signal.SIGINT, _handle_stop)
    signal.signal(signal.SIGTERM, _handle_stop)

    gateway = GatewayClient(
        settings.stream_gateway_url,
        allow_synthetic=settings.allow_synthetic_frames,
    )
    storage = FrameStorage(settings)
    redis_out = RedisOut(settings)
    windows: TemporalWindowBuffer[PreparedFrame] = TemporalWindowBuffer(
        window_size=settings.window_size
    )

    try:
        storage.ensure_bucket()
    except Exception:  # noqa: BLE001
        logger.exception("bucket ensure failed; continuing (bucket may already exist)")

    configs: list[StreamConfig] = []
    last_config_poll = 0.0
    sample_interval = 1.0 / max(settings.sample_fps, 0.1)
    last_sample_at: dict[str, float] = {}

    logger.info(
        "stream-prep started gateway=%s api=%s fps=%.2f window=%d",
        settings.stream_gateway_url,
        settings.api_internal_url,
        settings.sample_fps,
        settings.window_size,
    )

    while not stop:
        now = time.monotonic()
        if now - last_config_poll >= settings.poll_interval or not configs:
            try:
                configs = fetch_stream_configs(settings)
                last_config_poll = now
                logger.info("loaded %d active stream config(s)", len(configs))
            except Exception:  # noqa: BLE001
                logger.exception("failed to refresh stream configs")
                if not configs:
                    time.sleep(min(5.0, settings.poll_interval))
                    continue

        for cfg in configs:
            cam_last = last_sample_at.get(cfg.camera_id, 0.0)
            if now - cam_last < sample_interval:
                continue
            last_sample_at[cfg.camera_id] = now
            try:
                raw = gateway.fetch_frame(cfg.camera_id)
                jpeg, meta = preprocess_frame(
                    raw,
                    contrast_normalize=settings.contrast_normalize,
                )
                sample = FrameSample(
                    payload=PreparedFrame(jpeg_bytes=jpeg, meta=meta),
                    captured_at=datetime.now(timezone.utc),
                    camera_id=cfg.camera_id,
                    company_id=cfg.company_id,
                    establishment_id=cfg.establishment_id,
                )
                completed = windows.add(sample)
                if completed is not None:
                    _publish_window(
                        completed,
                        storage=storage,
                        redis_out=redis_out,
                        settings=settings,
                    )
            except Exception:  # noqa: BLE001
                logger.exception("sample failed for camera %s", cfg.camera_id)

        # Time-based flush for slow cameras (2× window duration at sample_fps).
        max_age = sample_interval * settings.window_size * 2
        for completed in windows.flush_stale(max_age_seconds=max_age):
            try:
                _publish_window(
                    completed,
                    storage=storage,
                    redis_out=redis_out,
                    settings=settings,
                )
            except Exception:  # noqa: BLE001
                logger.exception("flush publish failed for %s", completed.camera_id)

        time.sleep(0.05)

    gateway.close()
    redis_out.close()
    logger.info("stream-prep stopped")


def main() -> None:
    run_loop()


if __name__ == "__main__":
    main()
