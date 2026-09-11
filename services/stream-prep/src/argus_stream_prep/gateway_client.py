"""Fetch frames from go2rtc HTTP snapshot API (stream-gateway)."""

from __future__ import annotations

import io
import logging
from datetime import datetime, timezone

import httpx
from PIL import Image, ImageDraw

logger = logging.getLogger(__name__)


class GatewayClient:
    """HTTP client for go2rtc snapshot frames with synthetic fallback."""

    def __init__(
        self,
        base_url: str,
        *,
        timeout: float = 10.0,
        allow_synthetic: bool = True,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.allow_synthetic = allow_synthetic
        self._client = httpx.Client(timeout=timeout)

    def close(self) -> None:
        self._client.close()

    def fetch_frame(self, camera_id: str) -> bytes:
        """GET ``/api/frame.jpeg?src={camera_id}``; fall back to synthetic JPEG."""
        url = f"{self.base_url}/api/frame.jpeg"
        try:
            response = self._client.get(url, params={"src": camera_id})
            response.raise_for_status()
            if response.content:
                return response.content
            raise ValueError("empty frame body")
        except Exception as exc:  # noqa: BLE001 — MVP: any gateway miss → synthetic
            if not self.allow_synthetic:
                raise
            logger.warning(
                "go2rtc frame unavailable for %s (%s); using synthetic frame",
                camera_id,
                exc,
            )
            return self.synthetic_frame(camera_id)

    @staticmethod
    def synthetic_frame(camera_id: str, *, width: int = 640, height: int = 360) -> bytes:
        """Generate a labeled RGB JPEG for local tests without live media."""
        img = Image.new("RGB", (width, height), color=(32, 48, 64))
        draw = ImageDraw.Draw(img)
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        draw.rectangle((16, 16, width - 16, height - 16), outline=(120, 180, 220), width=2)
        draw.text((28, 28), f"camera={camera_id}", fill=(220, 230, 240))
        draw.text((28, 52), stamp, fill=(180, 200, 220))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        return buf.getvalue()
