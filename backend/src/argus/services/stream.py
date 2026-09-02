"""Redis Stream helpers for ingestion pipeline."""

from __future__ import annotations

from typing import Any

from argus.services.redis import xadd

INGEST_STREAM = "ingest:sequences"
INGEST_DLQ_STREAM = "ingest:dlq"
INGEST_DLQ_STREAM = "ingest:dlq"
INGEST_CONSUMER_GROUP = "vlm-workers"
# Alias referenced in some design docs
VLM_PROCESSING_QUEUE = INGEST_STREAM


async def enqueue_ingest_event(fields: dict[str, Any]) -> str:
    """Push an ingestion job onto the VLM processing stream."""
    return await xadd(INGEST_STREAM, fields)
