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
from argus.domain.models import Evidence, Recipe, Rule
from argus.guardrails.screening import screen
from argus.integrations.llm_provider import resolve_llm_chain
from argus.integrations.model_rank import rank_for
from argus.integrations.openai_vlm import VLMClient
from argus.services.database import company_session
from argus.services.llm_budget import check_llm_allowance
from argus.services.recipe_builder import (
    build_prompt,
    build_user_context,
    compute_severity_score,
    retrieve_rag_feedback,
    sanitize_vlm_result,
)
from argus.services.redis import move_to_dlq, xack, xreadgroup
from argus.services.stream import INGEST_CONSUMER_GROUP, INGEST_STREAM
from argus.workers.celery_app import celery_app
from argus.workers.utils import run_async

logger = logging.getLogger(__name__)

CONSUMER_NAME = f"vlm-{socket.gethostname()}-{os.getpid()}"
_vlm_provider: tuple[str, VLMClient] | None = None


def get_vlm_provider() -> tuple[str, VLMClient]:
    global _vlm_provider
    if _vlm_provider is None:
        _vlm_provider = resolve_llm_chain(settings)[0]
    return _vlm_provider


def get_vlm_client() -> VLMClient:
    return get_vlm_provider()[1]


def set_vlm_client(client: VLMClient) -> None:
    global _vlm_provider
    _vlm_provider = ("mock", client)


async def _model_for_attempt(provider: str, attempt: int) -> str | None:
    ranks = await rank_for(provider)
    if ranks and attempt < len(ranks):
        return ranks[attempt]
    return None


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
        return run_async(_analyze_message(message_id, fields, attempt=self.request.retries))
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


async def _analyze_message(message_id: str, fields: dict[str, Any], *, attempt: int = 0) -> str:
    parsed = _parse_stream_fields(fields)
    company_id = UUID(parsed["company_id"])
    camera_id = UUID(parsed["camera_id"])
    rule_set_id = UUID(parsed["rule_set_id"])
    ingestion_id = UUID(parsed["ingestion_id"])
    region_id = UUID(parsed["region_id"]) if parsed.get("region_id") else None
    captured_at = datetime.fromisoformat(parsed["captured_at"])
    frame_uris: list[str] = parsed["frame_uris"]

    async with company_session(company_id, UserRole.MANAGER.value) as session:
        recipe = await session.scalar(
            select(Recipe)
            .where(Recipe.rule_set_id == rule_set_id, Recipe.company_id == company_id)
            .order_by(Recipe.version.desc())
            .limit(1)
        )
        if recipe is None:
            raise ValueError(f"No recipe configured for rule set {rule_set_id}")

        rules = list(
            (
                await session.scalars(
                    select(Rule).where(
                        Rule.rule_set_id == rule_set_id,
                        Rule.company_id == company_id,
                    )
                )
            ).all()
        )
        rag_feedback = await retrieve_rag_feedback(
            session, company_id=company_id, camera_id=camera_id
        )

        blocked_policy = _screen_feedback(rag_feedback)
        if blocked_policy is not None:
            evidence = _skipped_evidence(
                company_id=company_id,
                camera_id=camera_id,
                region_id=region_id,
                rule_set_id=rule_set_id,
                captured_at=captured_at,
                frame_uri=frame_uris[0] if frame_uris else "",
                ingestion_id=ingestion_id,
                status="policy_block",
                detail=f"feedback blocked by policy {blocked_policy}",
            )
            session.add(evidence)
            await session.flush()
            await _maybe_xack(message_id)
            logger.warning(
                "LLM call skipped: evidence=%s reason=policy_block policy=%s",
                evidence.id,
                blocked_policy,
            )
            return str(evidence.id)

        prompt = build_prompt(recipe, rules, rag_feedback)
        output_schema = dict(recipe.output_schema)

    allowance = await check_llm_allowance(company_id)
    if allowance is not None:
        async with company_session(company_id, UserRole.MANAGER.value) as session:
            evidence = _skipped_evidence(
                company_id=company_id,
                camera_id=camera_id,
                region_id=region_id,
                rule_set_id=rule_set_id,
                captured_at=captured_at,
                frame_uri=frame_uris[0] if frame_uris else "",
                ingestion_id=ingestion_id,
                status=allowance,
                detail=f"llm skipped: {allowance}",
            )
            session.add(evidence)
            await session.flush()
            await _maybe_xack(message_id)
            logger.warning(
                "LLM call skipped: evidence=%s reason=%s", evidence.id, allowance
            )
            return str(evidence.id)

    provider, client = get_vlm_provider()
    model = await _model_for_attempt(provider, attempt)
    user_context = build_user_context(rag_feedback)
    scenario = parsed.get("edge_trigger_metadata", {}).get("scenario", "")
    if settings.auth0_use_mock and scenario:
        prompt = f"{prompt}\nDevelopment scenario: {scenario}"
    vlm_result = sanitize_vlm_result(
        client.analyze(
            system_prompt=prompt,
            frame_uris=frame_uris,
            output_schema=output_schema,
            model=model,
            user_context=user_context,
        )
    )
    severity_score = compute_severity_score(vlm_result, rules)

    async with company_session(company_id, UserRole.MANAGER.value) as session:
        evidence = Evidence(
            company_id=company_id,
            camera_id=camera_id,
            region_id=region_id,
            rule_set_id=rule_set_id,
            captured_at=captured_at,
            vlm_result=vlm_result,
            detection_class=vlm_result.get("detection_class"),
            confidence=vlm_result.get("confidence_score", vlm_result.get("confidence")),
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


def _screen_feedback(rag_feedback: list[Any]) -> str | None:
    """Screen untrusted feedback text before any prompt build. Returns blocking policy id."""
    for feedback in rag_feedback:
        reasoning = getattr(feedback, "reasoning", "") or ""
        hits = screen(reasoning)
        blocked = [hit for hit in hits if hit.action == "block"]
        if blocked:
            return blocked[0].policy_id
    return None


def _skipped_evidence(
    *,
    company_id: UUID,
    camera_id: UUID,
    region_id: UUID | None,
    rule_set_id: UUID,
    captured_at: datetime,
    frame_uri: str,
    ingestion_id: UUID,
    status: str,
    detail: str,
) -> Evidence:
    """Evidence row for an LLM call that was not performed (fails closed)."""
    return Evidence(
        company_id=company_id,
        camera_id=camera_id,
        region_id=region_id,
        rule_set_id=rule_set_id,
        captured_at=captured_at,
        vlm_result={"status": status, "error": detail},
        detection_class=None,
        confidence=None,
        severity_score=0,
        frame_storage_uri=frame_uri,
        ingestion_id=ingestion_id,
    )


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
