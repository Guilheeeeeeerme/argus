"""CPU cascade. Heavy vision dependencies are loaded only when used."""

from __future__ import annotations

import json
import math
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class Settings:
    idle_fps: float = 0.5
    burst_fps: float = 3
    burst_seconds: float = 10
    motion_threshold: float = 0.02
    novelty_threshold: float = 0.05
    max_keyframes: int = 3
    sample_interval_seconds: float = 1
    max_cameras: int = 256

    def __post_init__(self):
        for value in (
            self.idle_fps,
            self.burst_fps,
            self.burst_seconds,
            self.sample_interval_seconds,
        ):
            if not math.isfinite(value) or value <= 0:
                raise ValueError("rates and durations must be positive finite numbers")
        if not 1 <= self.max_keyframes <= 3 or self.max_cameras < 1:
            raise ValueError("invalid state/keyframe limit")
        if not all(
            math.isfinite(v) and 0 <= v <= 1
            for v in (self.motion_threshold, self.novelty_threshold)
        ):
            raise ValueError("invalid threshold")


def timestamp(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp requires timezone")
    return parsed.timestamp()


def parse(fields):
    for key in (
        "company_id",
        "establishment_id",
        "camera_id",
        "sequence_id",
        "captured_at",
    ):
        if not isinstance(fields.get(key), str) or not fields[key].strip():
            raise ValueError("missing identity/timestamp")
    timestamp(fields["captured_at"])
    uris = json.loads(fields["frame_uris"])
    meta = json.loads(fields.get("preproc_meta", "{}"))
    if (
        not isinstance(uris, list)
        or len(uris) > 128
        or any(not isinstance(u, str) or not u for u in uris)
    ):
        raise ValueError("invalid frame list")
    if not isinstance(meta, dict):
        raise TypeError("invalid preprocessing metadata")
    interval = float(meta.get("sample_interval_seconds", 1))
    if not math.isfinite(interval) or interval <= 0:
        raise ValueError("invalid sampling interval")
    return uris, meta, interval


class OpenCVVision:
    def signature(self, frame):
        import cv2

        return (
            cv2.resize(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), (32, 32)).astype(
                "float32"
            )
            / 255
        )

    def motion(self, old, new):
        import cv2

        return float(cv2.absdiff(old, new).mean())

    def novelty(self, old, new):
        import numpy as np

        a, b = old.ravel(), new.ravel()
        denom = float(np.linalg.norm(a) * np.linalg.norm(b))
        return (
            float(1 - np.dot(a, b) / denom)
            if denom
            else float(not np.array_equal(a, b))
        )


class EdgeInferencePipeline:
    def __init__(self, settings, detector, load_frame, *, vision=None, embedder=None):
        self.settings, self.detector, self.load_frame = settings, detector, load_frame
        self.vision = vision or OpenCVVision()
        self.embedder = embedder or self.vision.signature
        self.states = OrderedDict()

    def process(self, fields, sensors=None, sensor_buffer=None):
        uris, meta, interval = parse(fields)
        identity = tuple(
            fields[k] for k in ("company_id", "establishment_id", "camera_id")
        )
        # Copy state: failed loads/inference must not advance sampling on retries.
        state = dict(self.states.get(identity, {}))
        selected = []
        end = timestamp(fields["captured_at"])
        historical = end <= state.get("last_time", -math.inf)
        if historical:
            state = {}  # Retry older windows independently of newer sampling state.
        tracker_identity = identity + (object(),) if historical else identity
        for index, uri in enumerate(uris):
            frame_meta = meta.get("frames", [])
            frame_time = (
                frame_meta[index].get("captured_at")
                if isinstance(frame_meta, list)
                and index < len(frame_meta)
                and isinstance(frame_meta[index], dict)
                else None
            )
            now = (
                timestamp(frame_time)
                if frame_time
                else end - (len(uris) - 1 - index) * interval
            )
            events = list(sensors or [])
            if sensor_buffer is not None:
                events = sensor_buffer.match(
                    company_id=identity[0],
                    establishment_id=identity[1],
                    camera_id=identity[2],
                    timestamp=datetime.fromtimestamp(now, timezone.utc),
                )
            trigger = any(e.get("role") == "trigger" for e in events)
            if trigger:
                state["burst_until"] = now + self.settings.burst_seconds
            fps = (
                self.settings.burst_fps
                if now < state.get("burst_until", -math.inf)
                else self.settings.idle_fps
            )
            if now - state.get("last_time", -math.inf) < 1 / fps:
                continue
            frame = self.load_frame(uri)
            signature = self.vision.signature(frame)
            old = state.get("signature")
            motion = self.vision.motion(old, signature) if old is not None else 1.0
            state.update(last_time=now, signature=signature)
            if motion >= self.settings.motion_threshold:
                state["burst_until"] = now + self.settings.burst_seconds
            if motion < self.settings.motion_threshold and not trigger:
                continue
            tracks = self.detector.detect(frame, tracker_identity)
            if not tracks:
                continue
            confidence = max(float(t["confidence"]) for t in tracks)
            if not math.isfinite(confidence) or not 0 <= confidence <= 1:
                raise ValueError("invalid detector confidence")
            embedding = self.embedder(frame)
            prior = state.get("key_signature")
            novel = (
                prior is None
                or self.vision.novelty(prior, embedding)
                >= self.settings.novelty_threshold
            )
            if (
                not novel
                and confidence <= state.get("key_confidence", 0)
                and not trigger
            ):
                continue
            state.update(key_signature=embedding, key_confidence=confidence)
            selected.append((confidence, uri, tracks, motion, now, events, index))
        if not historical:
            self.states[identity] = state
            self.states.move_to_end(identity)
        while len(self.states) > self.settings.max_cameras:
            self.states.popitem(last=False)
        if not selected:
            return None
        selected.sort(key=lambda item: item[0], reverse=True)
        selected = selected[: self.settings.max_keyframes]
        aligned = {}
        for item in selected:
            for event in item[5]:
                aligned[
                    str(
                        event.get(
                            "id",
                            event.get(
                                "context_event_id", json.dumps(event, sort_keys=True)
                            ),
                        )
                    )
                ] = event
        output = dict(fields)
        selected_meta = dict(meta)
        original_meta = meta.get("frames", [])
        selected_meta["frames"] = [
            (
                dict(original_meta[s[6]])
                if isinstance(original_meta, list)
                and s[6] < len(original_meta)
                and isinstance(original_meta[s[6]], dict)
                else {}
            )
            | {"captured_at": datetime.fromtimestamp(s[4], timezone.utc).isoformat()}
            for s in selected
        ]
        output["preproc_meta"] = json.dumps(selected_meta)
        output.update(
            frame_uris=json.dumps([s[1] for s in selected]),
            edge_score=str(selected[0][0]),
            motion_score=str(max(s[3] for s in selected)),
            tracks=json.dumps([t for s in selected for t in s[2]]),
            sensor_ids=json.dumps(
                [
                    e.get("id", e.get("context_event_id"))
                    for e in aligned.values()
                    if e.get("id", e.get("context_event_id"))
                ]
            ),
            sensors=json.dumps(list(aligned.values())),
            temporal_span_seconds=str(
                max(s[4] for s in selected) - min(s[4] for s in selected)
            ),
        )
        return output
