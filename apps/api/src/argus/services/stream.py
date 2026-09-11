"""Redis Stream helpers for MVP pipeline contracts."""

from __future__ import annotations

from typing import Any

from argus.services.redis import xadd

FRAMES_READY_STREAM = "frames:ready"
CONTEXT_EVENTS_STREAM = "context:events"
DETECTIONS_POSITIVE_STREAM = "detections:positive"
DETECTIONS_POSITIVE_GROUP = "api-bridge"

# Legacy aliases kept for older worker imports during transition.
INGEST_STREAM = FRAMES_READY_STREAM
INGEST_DLQ_STREAM = "ingest:dlq"
INGEST_CONSUMER_GROUP = "prompt-eval"
VLM_PROCESSING_QUEUE = FRAMES_READY_STREAM
FRAMES_READY_CONSUMER_GROUP = "prompt-eval"
CONTEXT_EVENTS_CONSUMER_GROUP = "prompt-eval"
DETECTIONS_POSITIVE_CONSUMER_GROUP = DETECTIONS_POSITIVE_GROUP


async def enqueue_frames_ready(fields: dict[str, Any]) -> str:
    """Push a prepared frame sequence onto frames:ready."""
    return await xadd(FRAMES_READY_STREAM, fields)


async def enqueue_ingest_event(fields: dict[str, Any]) -> str:
    """Backward-compatible alias for test inject / legacy callers."""
    return await enqueue_frames_ready(fields)


async def enqueue_context_event(fields: dict[str, Any]) -> str:
    return await xadd(CONTEXT_EVENTS_STREAM, fields)


async def enqueue_detection_positive(fields: dict[str, Any]) -> str:
    return await xadd(DETECTIONS_POSITIVE_STREAM, fields)
