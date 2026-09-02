"""VLM analyzer worker — consume ingest stream, analyze frames, create Evidence."""

from __future__ import annotations

import json
import logging
import os
import socket
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select

from argus.config import settings
from argus.domain.enums import UserRole
from argus.domain.models import Evidence, Lens, Rule
from argus.integrations.openai_vlm import MockVLMClient, OpenAIVLMClient, VLMClient
from argus.services.database import tenant_session
from argus.services.lens_builder import (
    build_prompt,
    compute_severity_score,
    retrieve_rag_feedback,
)
from argus.services.redis import move_to_dlq, xack, xreadgroup
from argus.services.stream import INGEST_CONSUMER_GROUP, INGEST_STREAM
from argus.workers.celery_app import celery_app
from argus.workers.utils import run_async

logger = logging.getLogger(__name__)

CONSUMER_NAME = f"vlm-{socket.gethostname()}-{os.getpid()}"
_vlm_client: VLMClient | None = None


def get_vlm_client() -> VLMClient:
    global _vlm_client
    if _vlm_client is None:
        _vlm_client = MockVLMClient() if settings.auth0_use_mock or not settings.openai_api_key else OpenAIVLMClient()
    return _vlm_client


def set_vlm_client(client: VLMClient) -> None:
    global _vlm_client
    _vlm_client = client


@celery_app.task(name="vlm.process_ingest_stream")
def process_ingest_stream() -> int:
    return run_async(_process_ingest_stream_batch())


@celery_app.task(
    name="vlm.analyze_ingest_message",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=60,
    max_retries=3,
)
def analyze_ingest_message(self, message_id: str, fields: dict[str, Any]) -> str | None:
    try:
        return run_async(_analyze_message(message_id, fields))
    except Exception as exc:
        if self.request.retries >= self.max_retries:
            run_async(move_to_dlq(fields, error=str(exc)))
            run_async(xack(INGEST_STREAM, INGEST_CONSUMER_GROUP, message_id))
            logger.exception("Message %s moved to DLQ after retries", message_id)
            return None
        raise


async def _process_ingest_stream_batch() -> int:
    messages = await xreadgroup(
        INGEST_CONSUMER_GROUP,
        CONSUMER_NAME,
        {INGEST_STREAM: ">"},
        count=10,
        block_ms=1000,
    )
    processed = 0
    for _stream, entries in messages:
        for message_id, fields in entries:
            analyze_ingest_message.delay(message_id, dict(fields))
            processed += 1
    return processed


async def _analyze_message(message_id: str, fields: dict[str, Any]) -> str:
    parsed = _parse_stream_fields(fields)
    tenant_id = UUID(parsed["tenant_id"])
    camera_id = UUID(parsed["camera_id"])
    context_mode_id = UUID(parsed["context_mode_id"])
    ingestion_id = UUID(parsed["ingestion_id"])
    region_id = UUID(parsed["region_id"]) if parsed.get("region_id") else None
    captured_at = datetime.fromisoformat(parsed["captured_at"])
    frame_uris: list[str] = parsed["frame_uris"]

    async with tenant_session(tenant_id, UserRole.TENANT_ADMIN.value) as session:
        lens = await session.scalar(
            select(Lens)
            .where(Lens.context_mode_id == context_mode_id, Lens.tenant_id == tenant_id)
            .order_by(Lens.version.desc())
            .limit(1)
        )
        if lens is None:
            raise ValueError(f"No lens configured for context mode {context_mode_id}")

        rules = list(
            (
                await session.scalars(
                    select(Rule).where(
                        Rule.context_mode_id == context_mode_id,
                        Rule.tenant_id == tenant_id,
                    )
                )
            ).all()
        )
        rag_feedback = await retrieve_rag_feedback(
            session, tenant_id=tenant_id, camera_id=camera_id
        )
        prompt = build_prompt(lens, rules, rag_feedback)
        output_schema = dict(lens.output_schema)

    client = get_vlm_client()
    scenario = parsed.get("edge_trigger_metadata", {}).get("scenario", "")
    if settings.auth0_use_mock and scenario:
        prompt = f"{prompt}\nDevelopment scenario: {scenario}"
    vlm_result = client.analyze(
        system_prompt=prompt,
        frame_uris=frame_uris,
        output_schema=output_schema,
    )
    severity_score = compute_severity_score(vlm_result, rules)

    async with tenant_session(tenant_id, UserRole.TENANT_ADMIN.value) as session:
        evidence = Evidence(
            tenant_id=tenant_id,
            camera_id=camera_id,
            region_id=region_id,
            context_mode_id=context_mode_id,
            captured_at=captured_at,
            vlm_result=vlm_result,
            severity_score=severity_score,
            frame_storage_uri=frame_uris[0] if frame_uris else "",
            ingestion_id=ingestion_id,
        )
        session.add(evidence)
        await session.flush()
        evidence_id = str(evidence.id)

    await _maybe_xack(message_id)

    from argus.workers.aggregator import aggregate_evidence

    aggregate_evidence.delay(evidence_id)
    return evidence_id


async def _maybe_xack(message_id: str) -> None:
    """Acknowledge Redis stream messages when ID format is valid."""
    parts = message_id.split("-", 1)
    if len(parts) == 2 and parts[0].isdigit():
        await xack(INGEST_STREAM, INGEST_CONSUMER_GROUP, message_id)


def _parse_stream_fields(fields: dict[str, Any]) -> dict[str, Any]:
    parsed = dict(fields)
    for key in ("frame_uris", "edge_trigger_metadata"):
        raw = parsed.get(key)
        if isinstance(raw, str) and raw:
            parsed[key] = json.loads(raw)
        elif raw in (None, ""):
            parsed[key] = [] if key == "frame_uris" else {}
    if not parsed.get("region_id"):
        parsed["region_id"] = ""
    return parsed
