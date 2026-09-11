"""Temporal windowing — align / bound evidence clip windows.

AI Engineering pattern: Temporal windowing.
Clip duration is hard-capped at ``MAX_CLIP_SECONDS`` (default 10 minutes).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from argus_prompt_eval.config import settings


@dataclass(frozen=True)
class TimeWindow:
    start: datetime
    end: datetime

    @property
    def duration_seconds(self) -> float:
        return max(0.0, (self.end - self.start).total_seconds())


def ensure_aware(ts: datetime) -> datetime:
    if ts.tzinfo is None:
        return ts.replace(tzinfo=UTC)
    return ts


def window_from_capture(
    captured_at: datetime,
    *,
    frame_count: int,
    sample_interval_seconds: float = 1.0,
) -> TimeWindow:
    """Build a window centered on capture time spanning the frame sequence."""
    captured = ensure_aware(captured_at)
    span = max(0.0, (frame_count - 1) * sample_interval_seconds)
    start = captured
    end = captured + timedelta(seconds=span)
    return clamp_window(TimeWindow(start=start, end=end))


def clamp_window(window: TimeWindow, *, max_seconds: int | None = None) -> TimeWindow:
    """Clamp window duration to the evidence retention ceiling."""
    limit = max_seconds if max_seconds is not None else settings.max_clip_seconds
    start = ensure_aware(window.start)
    end = ensure_aware(window.end)
    if end < start:
        start, end = end, start
    if (end - start).total_seconds() <= limit:
        return TimeWindow(start=start, end=end)
    return TimeWindow(start=start, end=start + timedelta(seconds=limit))


def extend_around(
    center: datetime,
    *,
    before_seconds: float = 0.0,
    after_seconds: float = 0.0,
) -> TimeWindow:
    center_aware = ensure_aware(center)
    return clamp_window(
        TimeWindow(
            start=center_aware - timedelta(seconds=before_seconds),
            end=center_aware + timedelta(seconds=after_seconds),
        )
    )
