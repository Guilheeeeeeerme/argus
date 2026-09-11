"""AI Engineering: Media preprocessing.

Normalize and enrich sampled camera frames before object storage upload.
Outputs JPEG bytes plus ``preproc_meta`` for the ``frames:ready`` Redis stream.
"""

from __future__ import annotations

import io
from dataclasses import asdict, dataclass
from typing import Any

from PIL import Image, ImageOps


MAX_EDGE = 1280
JPEG_QUALITY = 85


@dataclass(frozen=True)
class PreprocMeta:
    """Metadata describing transformations applied to a frame."""

    max_edge: int
    jpeg_quality: int
    original_width: int
    original_height: int
    width: int
    height: int
    contrast_normalize: bool
    format: str = "JPEG"
    color_mode: str = "RGB"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def preprocess_frame(
    raw: bytes,
    *,
    max_edge: int = MAX_EDGE,
    jpeg_quality: int = JPEG_QUALITY,
    contrast_normalize: bool = False,
) -> tuple[bytes, PreprocMeta]:
    """Resize (max edge), convert to RGB JPEG, optionally contrast-normalize.

    Args:
        raw: Encoded image bytes (any Pillow-supported format).
        max_edge: Longest side after resize; smaller images are left unchanged.
        jpeg_quality: JPEG quality (~85 for MVP).
        contrast_normalize: When True, apply Pillow autocontrast.

    Returns:
        ``(jpeg_bytes, preproc_meta)``.
    """
    with Image.open(io.BytesIO(raw)) as img:
        original_width, original_height = img.size
        rgb = img.convert("RGB")

    if contrast_normalize:
        rgb = ImageOps.autocontrast(rgb)

    width, height = rgb.size
    longest = max(width, height)
    if longest > max_edge:
        scale = max_edge / float(longest)
        new_size = (max(1, int(width * scale)), max(1, int(height * scale)))
        rgb = rgb.resize(new_size, Image.Resampling.LANCZOS)
        width, height = rgb.size

    buf = io.BytesIO()
    rgb.save(buf, format="JPEG", quality=jpeg_quality, optimize=True)
    meta = PreprocMeta(
        max_edge=max_edge,
        jpeg_quality=jpeg_quality,
        original_width=original_width,
        original_height=original_height,
        width=width,
        height=height,
        contrast_normalize=contrast_normalize,
    )
    return buf.getvalue(), meta
