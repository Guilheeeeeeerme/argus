"""Dependency-free, bounded sensor correlation scoped to tenant and location."""

from __future__ import annotations

from collections import deque
from copy import deepcopy
from datetime import datetime
from math import isfinite


def _timestamp(value: object) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value) if isinstance(value, str) else value
        if isinstance(parsed, datetime) and parsed.utcoffset() is not None:
            return parsed
    except (TypeError, ValueError, OverflowError):
        pass
    return None


class SensorFusionBuffer:
    """Keep the latest events; match inclusive event-time windows, never other tenants.

    Count-bounded retention supports out-of-order arrivals without allowing a sensor's
    future timestamp to evict unrelated tenants' events.
    """

    def __init__(self, window_seconds: float = 5, max_events: int = 10_000):
        if not isfinite(window_seconds) or window_seconds < 0 or max_events < 1:
            raise ValueError("Invalid sensor buffer bounds")
        self.window_seconds = window_seconds
        self._events: deque[tuple[datetime, dict]] = deque(maxlen=max_events)

    def add(self, event: dict) -> None:
        if not isinstance(event, dict):
            return
        if any(
            not isinstance(event.get(key), str) or not event[key].strip()
            for key in ("company_id", "establishment_id")
        ):
            return
        camera = event.get("camera_id")
        if camera is not None and not isinstance(camera, str):
            return
        timestamp = _timestamp(event.get("occurred_at", event.get("received_at")))
        if timestamp is None or event.get("role", "context") not in (
            "trigger",
            "filter",
            "context",
        ):
            return
        confidence = event.get("confidence")
        if confidence is not None:
            try:
                confidence = float(confidence)
            except (ValueError, TypeError, OverflowError):
                return
            if not isfinite(confidence) or not 0 <= confidence <= 1:
                return
        normalized = deepcopy(event)
        normalized.update(
            role=event.get("role", "context"),
            confidence=confidence,
            occurred_at=timestamp.isoformat(),
        )
        self._events.append((timestamp, normalized))

    def match(
        self,
        *,
        company_id: str,
        establishment_id: str,
        camera_id: str,
        timestamp: datetime | str,
    ) -> list[dict]:
        target = _timestamp(timestamp)
        if target is None or not company_id or not establishment_id:
            return []
        return [
            deepcopy(event)
            for occurred_at, event in self._events
            if event["company_id"] == company_id
            and event["establishment_id"] == establishment_id
            and (not event.get("camera_id") or event["camera_id"] == camera_id)
            and abs((occurred_at - target).total_seconds()) <= self.window_seconds
        ]
