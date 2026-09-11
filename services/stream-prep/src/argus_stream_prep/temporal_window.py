"""AI Engineering: Temporal windowing.

Group sampled frames into short sequence windows for downstream prompt-eval.
MVP uses a fixed frame count (4–8); time-based windows can replace this later.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Generic, TypeVar

T = TypeVar("T")

DEFAULT_WINDOW_SIZE = 6
MIN_WINDOW_SIZE = 4
MAX_WINDOW_SIZE = 8


def clamp_window_size(size: int) -> int:
    """Clamp requested window size into the MVP 4–8 frame band."""
    return max(MIN_WINDOW_SIZE, min(MAX_WINDOW_SIZE, size))


@dataclass
class FrameSample(Generic[T]):
    """One sampled frame awaiting window completion."""

    payload: T
    captured_at: datetime
    camera_id: str
    company_id: str
    establishment_id: str


@dataclass
class FrameWindow(Generic[T]):
    """A completed temporal window of frames."""

    sequence_id: str
    company_id: str
    establishment_id: str
    camera_id: str
    captured_at: datetime
    frames: list[FrameSample[T]] = field(default_factory=list)


class TemporalWindowBuffer(Generic[T]):
    """Accumulate frames per camera until a window is ready to flush."""

    def __init__(self, window_size: int = DEFAULT_WINDOW_SIZE) -> None:
        self.window_size = clamp_window_size(window_size)
        self._buffers: dict[str, list[FrameSample[T]]] = {}

    def add(self, sample: FrameSample[T]) -> FrameWindow[T] | None:
        """Append a sample; return a completed window when size is reached."""
        key = sample.camera_id
        buf = self._buffers.setdefault(key, [])
        buf.append(sample)
        if len(buf) < self.window_size:
            return None
        frames = buf[: self.window_size]
        del buf[: self.window_size]
        return FrameWindow(
            sequence_id=str(uuid.uuid4()),
            company_id=frames[0].company_id,
            establishment_id=frames[0].establishment_id,
            camera_id=frames[0].camera_id,
            captured_at=frames[-1].captured_at,
            frames=frames,
        )

    def flush_stale(
        self,
        *,
        max_age_seconds: float,
        now: datetime | None = None,
    ) -> list[FrameWindow[T]]:
        """Optional time-based flush: emit partial windows older than max age.

        Partial windows still require at least :data:`MIN_WINDOW_SIZE` frames.
        """
        now = now or datetime.now(timezone.utc)
        completed: list[FrameWindow[T]] = []
        for camera_id, buf in list(self._buffers.items()):
            if len(buf) < MIN_WINDOW_SIZE:
                continue
            age = (now - buf[0].captured_at).total_seconds()
            if age < max_age_seconds:
                continue
            frames = list(buf)
            buf.clear()
            completed.append(
                FrameWindow(
                    sequence_id=str(uuid.uuid4()),
                    company_id=frames[0].company_id,
                    establishment_id=frames[0].establishment_id,
                    camera_id=camera_id,
                    captured_at=frames[-1].captured_at,
                    frames=frames,
                )
            )
        return completed
