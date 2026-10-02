"""prompt-eval consumer loop.

AI Engineering orchestration:
frames:ready → context_grounding → prompt_set_eval → negative_discard
  |→ evidence_retention → persist → detections:positive

Also XREADGROUP context:events (API already persists ContextEvent rows;
grounding reads the table. This consumer keeps the group caught up).
"""

from __future__ import annotations

import asyncio
import logging
import signal
from datetime import UTC, datetime
from uuid import UUID

from argus_prompt_eval.config import settings
from argus_prompt_eval.consensus import ConsensusEngine
from argus_prompt_eval.context_grounding import ground_candidate, ground_context
from argus_prompt_eval.db import _USING_SHARED_MODELS, account_session
from argus_prompt_eval.evidence_retention import retain_evidence
from argus_prompt_eval.negative_discard import discard_sequence, should_discard
from argus_prompt_eval.persist import find_positive, persist_positive
from argus_prompt_eval.prompt_set_eval import evaluate_prompt_set
from argus_prompt_eval.redis_io import (
    claim_pending,
    close_redis,
    ensure_consumer_group,
    get_redis,
    parse_candidates_ready,
    parse_context_event,
    parse_frames_ready,
    publish_detection_positive,
    xack,
    xreadgroup,
)
from argus_prompt_eval.temporal_window import ensure_aware

logger = logging.getLogger(__name__)

_stop = asyncio.Event()


def _request_stop(*_args: object) -> None:
    _stop.set()


def input_stream() -> str:
    return (
        settings.candidates_stream
        if settings.edge_cv_enabled
        else settings.frames_stream
    )


async def _handle_candidates_ready(message_id: str, fields: dict[str, str]) -> None:
    try:
        payload = parse_candidates_ready(fields)
        context = ground_candidate(payload)
    except (ValueError, TypeError, KeyError, OverflowError):
        discard_sequence(
            sequence_id=fields.get("sequence_id", ""), reason="malformed_candidate"
        )
        await xack(settings.candidates_stream, settings.frames_group, message_id)
        return
    if payload["sensor_veto"]:
        discard_sequence(sequence_id=payload["sequence_id"], reason="sensor_veto")
        await xack(settings.candidates_stream, settings.frames_group, message_id)
        return
    await _handle_frames_ready(
        message_id, fields, candidate=payload, candidate_context=context
    )


async def _handle_frames_ready(
    message_id: str,
    fields: dict[str, str],
    *,
    candidate: dict | None = None,
    candidate_context: str = "",
) -> None:
    payload = candidate if candidate is not None else parse_frames_ready(fields)
    stream = (
        settings.candidates_stream if candidate is not None else settings.frames_stream
    )
    account_id = UUID(payload["account_id"])
    unit_id = UUID(payload["unit_id"])
    camera_id = UUID(payload["camera_id"])
    sequence_id = str(payload["sequence_id"])
    frame_uris = list(payload["frame_uris"])
    preproc = payload.get("preproc_meta") or {}
    sample_interval = float(preproc.get("sample_interval_seconds", 1.0))
    captured_at = ensure_aware(
        datetime.fromisoformat(payload["captured_at"].replace("Z", "+00:00"))
        if payload.get("captured_at")
        else datetime.now(UTC)
    )

    if not frame_uris:
        discard_sequence(sequence_id=sequence_id, reason="empty_frames")
        await xack(stream, settings.frames_group, message_id)
        return

    redis = get_redis()
    async with account_session(account_id) as session:
        existing = await find_positive(
            session, account_id=account_id, camera_id=camera_id, sequence_id=sequence_id
        )
        if existing is not None:
            detection, triage = existing
            await _publish_positive(detection, triage)
            await xack(stream, settings.frames_group, message_id)
            return
        grounded = await ground_context(
            session,
            account_id=account_id,
            unit_id=unit_id,
            camera_id=camera_id,
        )
        if grounded.blocked_policy is not None:
            discard_sequence(
                sequence_id=sequence_id,
                reason=f"policy_block:{grounded.blocked_policy}",
                frame_uris=frame_uris,
            )
            await xack(stream, settings.frames_group, message_id)
            return

        evaluated = await evaluate_prompt_set(
            session,
            redis,
            account_id=account_id,
            camera_id=camera_id,
            unit_id=unit_id,
            frame_uris=frame_uris[:1] if candidate is not None else frame_uris,
            user_context=grounded.user_context
            + ("\n" + candidate_context if candidate_context else ""),
        )
        if evaluated is None:
            discard_sequence(
                sequence_id=sequence_id,
                reason="no_prompt_set",
                frame_uris=frame_uris,
            )
            await xack(stream, settings.frames_group, message_id)
            return

        _loaded, result, provider = evaluated
        if should_discard(result):
            discard_sequence(
                sequence_id=sequence_id,
                reason="no_match",
                frame_uris=frame_uris,
                extra={"provider": provider},
            )
            await xack(stream, settings.frames_group, message_id)
            return

        if candidate is not None:
            decision = ConsensusEngine(
                threshold=settings.consensus_threshold,
                edge_minimum=settings.consensus_edge_minimum,
            ).evaluate(
                sensor_score=candidate["sensor_score"],
                edge_score=candidate["edge_score"],
                gemini_score=max(
                    (hit.confidence for hit in result.prompt_hits if hit.matched),
                    default=0,
                ),
                prompt_hit=any(hit.matched for hit in result.prompt_hits),
                veto=candidate["sensor_veto"],
            )
            if not decision.is_positive:
                discard_sequence(
                    sequence_id=sequence_id,
                    reason=decision.reason,
                    frame_uris=frame_uris,
                )
                await xack(stream, settings.frames_group, message_id)
                return

        evidence_uris = frame_uris
        if candidate is not None and preproc.get("frames"):
            # Ranking is for VLM selection; evidence must play in capture order.
            evidence_uris = [
                uri
                for _, uri in sorted(
                    (
                        datetime.fromisoformat(
                            meta["captured_at"].replace("Z", "+00:00")
                        ),
                        uri,
                    )
                    for meta, uri in zip(preproc["frames"], frame_uris, strict=True)
                )
            ]
        evidence = retain_evidence(
            account_id=account_id,
            camera_id=camera_id,
            sequence_id=sequence_id,
            frame_uris=evidence_uris,
            captured_at=captured_at,
            sample_interval_seconds=sample_interval,
        )
        detection, triage = await persist_positive(
            session,
            account_id=account_id,
            unit_id=unit_id,
            camera_id=camera_id,
            sequence_id=sequence_id,
            result=result,
            evidence=evidence,
            captured_at=captured_at,
        )

    await _publish_positive(
        detection,
        triage,
        provider=provider,
        assembled_with_ffmpeg=evidence.assembled_with_ffmpeg,
    )
    logger.info(
        "positive detection=%s triage=%s provider=%s sequence=%s",
        detection.id,
        triage.id,
        provider,
        sequence_id,
    )
    await xack(stream, settings.frames_group, message_id)


async def _publish_positive(detection, triage, **metadata) -> None:
    # Publication is at least once; downstream must deduplicate by detection_id.
    await publish_detection_positive(
        {
            "detection_id": str(detection.id),
            "triage_case_id": str(triage.id),
            "clip_uri": detection.clip_uri,
            "prompt_hits": detection.prompt_hits,
            "confidence": float(detection.confidence),
            "summary": detection.summary,
            "account_id": str(detection.account_id),
            "unit_id": str(detection.unit_id),
            "camera_id": str(detection.camera_id),
            "sequence_id": detection.sequence_id,
            "state": "open",
            "created_at": (
                detection.created_at.isoformat()
                if getattr(detection, "created_at", None)
                else datetime.now(UTC).isoformat()
            ),
            **metadata,
        }
    )


async def _handle_context_event(message_id: str, fields: dict[str, str]) -> None:
    """Ack context:events; ContextEvent rows are written by the API webhook path.

    Grounding reads recent rows from ``context_events``. Keeping this consumer
    group caught up avoids pending-entry backlog on the shared stream.
    """
    parsed = parse_context_event(fields)
    logger.debug(
        "context event kind=%s unit=%s camera=%s",
        parsed.get("kind"),
        parsed.get("unit_id"),
        parsed.get("camera_id"),
    )
    await xack(settings.context_stream, settings.context_group, message_id)


async def run_forever() -> None:
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    stream = input_stream()
    await ensure_consumer_group(stream, settings.frames_group)
    await ensure_consumer_group(settings.context_stream, settings.context_group)
    consumer = "prompt-eval-1"
    logger.info(
        "prompt-eval listening frames=%s context=%s shared_models=%s",
        stream,
        settings.context_stream,
        _USING_SHARED_MODELS,
    )

    cursors = {stream: "0-0", settings.context_stream: "0-0"}
    while not _stop.is_set():
        try:
            batches = []
            for pending_stream, group in (
                (stream, settings.frames_group),
                (settings.context_stream, settings.context_group),
            ):
                cursors[pending_stream], pending = await claim_pending(
                    pending_stream, group, consumer, cursors[pending_stream]
                )
                if pending:
                    batches.append((pending_stream, pending))
            fresh = await xreadgroup(
                settings.frames_group,
                consumer,
                {
                    stream: ">",
                    settings.context_stream: ">",
                },
            )
            batches.extend(fresh)
        except Exception:
            logger.exception("stream read failed")
            await asyncio.sleep(1)
            continue

        if not batches:
            continue

        for stream_name, messages in batches:
            for message_id, fields in messages:
                try:
                    if stream_name == stream:
                        handler = (
                            _handle_candidates_ready
                            if settings.edge_cv_enabled
                            else _handle_frames_ready
                        )
                        await handler(message_id, fields)
                    else:
                        await _handle_context_event(message_id, fields)
                except Exception as exc:  # noqa: BLE001 — keep failed entries pending
                    logger.error(
                        "failed processing %s id=%s error_type=%s",
                        stream_name,
                        message_id,
                        type(exc).__name__,
                    )

    await close_redis()


def main() -> None:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _request_stop)
        except NotImplementedError:
            signal.signal(sig, lambda *_: _request_stop())
    try:
        loop.run_until_complete(run_forever())
    finally:
        loop.close()


if __name__ == "__main__":
    main()
