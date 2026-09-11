"""Evidence retention — assemble/store clip ≤ 10 minutes for positive hits.

AI Engineering pattern: Evidence retention.

Clip strategy (MVP):
1. Prefer ffmpeg: download frames, stitch to mp4 (1 fps default), upload to S3,
   set ``clip_uri`` to the mp4 object.
2. If ffmpeg is unavailable or stitching fails: store ordered frame URI list as
   clip metadata; set ``clip_uri`` to the first frame URI and record
   ``window_start`` / ``window_end`` on the Detection. Temporary frames remain
   TTL-bound in MinIO — operators should treat the URI list as the evidence
   sequence until a durable clip pipeline lands.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4

from argus_prompt_eval.config import settings
from argus_prompt_eval.temporal_window import TimeWindow, clamp_window, window_from_capture
from argus_prompt_eval.vlm import download_s3_bytes, upload_bytes

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EvidenceClip:
    clip_uri: str
    frame_uris: list[str]
    window: TimeWindow
    assembled_with_ffmpeg: bool
    meta: dict


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def retain_evidence(
    *,
    company_id: UUID,
    camera_id: UUID,
    sequence_id: str,
    frame_uris: list[str],
    captured_at: datetime,
    sample_interval_seconds: float = 1.0,
) -> EvidenceClip:
    """Build/store evidence clip (≤ max_clip_seconds)."""
    window = clamp_window(
        window_from_capture(
            captured_at,
            frame_count=len(frame_uris),
            sample_interval_seconds=sample_interval_seconds,
        )
    )
    if not frame_uris:
        raise ValueError("Cannot retain evidence without frame_uris")

    if ffmpeg_available():
        try:
            clip_uri = _stitch_ffmpeg(
                company_id=company_id,
                camera_id=camera_id,
                sequence_id=sequence_id,
                frame_uris=frame_uris,
                fps=max(0.2, 1.0 / sample_interval_seconds),
            )
            return EvidenceClip(
                clip_uri=clip_uri,
                frame_uris=frame_uris,
                window=window,
                assembled_with_ffmpeg=True,
                meta={"strategy": "ffmpeg_mp4", "fps": 1.0 / sample_interval_seconds},
            )
        except Exception as exc:  # noqa: BLE001 — fall back to frame list
            logger.warning("ffmpeg stitch failed, falling back to frame list: %s", exc)

    # Fallback: representative frame sequence URI list; clip_uri = first frame.
    return EvidenceClip(
        clip_uri=frame_uris[0],
        frame_uris=frame_uris,
        window=window,
        assembled_with_ffmpeg=False,
        meta={
            "strategy": "frame_uri_list",
            "note": (
                "ffmpeg unavailable or failed; clip_uri is the first frame. "
                "Use frame_uris + window timestamps as the evidence sequence."
            ),
            "max_clip_seconds": settings.max_clip_seconds,
        },
    )


def _stitch_ffmpeg(
    *,
    company_id: UUID,
    camera_id: UUID,
    sequence_id: str,
    frame_uris: list[str],
    fps: float,
) -> str:
    with tempfile.TemporaryDirectory(prefix="prompt-eval-clip-") as tmp:
        tmp_path = Path(tmp)
        for index, uri in enumerate(frame_uris):
            dest = tmp_path / f"frame_{index:05d}.jpg"
            if uri.startswith("s3://"):
                data, _ = download_s3_bytes(uri)
            elif uri.startswith("data:"):
                import base64

                _, _, b64 = uri.partition(",")
                data = base64.b64decode(b64)
            else:
                raise ValueError(f"Unsupported URI for ffmpeg stitch: {uri[:20]}")
            dest.write_bytes(data)

        out_path = tmp_path / "clip.mp4"
        cmd = [
            "ffmpeg",
            "-y",
            "-framerate",
            str(fps),
            "-i",
            str(tmp_path / "frame_%05d.jpg"),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(out_path),
        ]
        subprocess.run(cmd, check=True, capture_output=True, timeout=120)
        key = (
            f"clips/{company_id}/{camera_id}/{sequence_id}/"
            f"{uuid4().hex}.mp4"
        )
        return upload_bytes(key, out_path.read_bytes(), content_type="video/mp4")
