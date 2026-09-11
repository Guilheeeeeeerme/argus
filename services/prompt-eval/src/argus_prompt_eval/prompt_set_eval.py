"""Multi-prompt evaluation — evaluate the full active PromptSet per sequence.

AI Engineering pattern: Multi-prompt evaluation.
Loads PromptSet+Prompts for a camera, builds the system prompt, calls the VLM,
and normalizes structured hits.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import UUID

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from argus_prompt_eval.config import settings
from argus_prompt_eval.db import Prompt, PromptSet
from argus_prompt_eval.guardrails import render_prompt
from argus_prompt_eval.provider_router import analyze_with_failover
from argus_prompt_eval.structured_output import (
    PromptEvalResult,
    PromptHit,
    output_schema,
    parse_prompt_eval_result,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LoadedPromptSet:
    prompt_set: PromptSet
    prompts: list[Prompt]


async def load_prompt_set_for_camera(
    session: AsyncSession,
    *,
    company_id: UUID,
    camera_id: UUID,
    establishment_id: UUID | None = None,
) -> LoadedPromptSet | None:
    """Resolve PromptSet for camera (first by name, with enabled prompts)."""
    del establishment_id  # reserved for future establishment-level defaults
    prompt_set = await session.scalar(
        select(PromptSet)
        .where(
            PromptSet.company_id == company_id,
            PromptSet.camera_id == camera_id,
        )
        .options(selectinload(PromptSet.prompts))
        .order_by(PromptSet.created_at.asc())
        .limit(1)
    )
    if prompt_set is None:
        return None

    prompts = sorted(
        [p for p in prompt_set.prompts if p.enabled],
        key=lambda p: (p.sort_order, str(p.id)),
    )
    if not prompts:
        logger.warning("PromptSet %s has no enabled prompts", prompt_set.id)
        return None
    return LoadedPromptSet(prompt_set=prompt_set, prompts=prompts)


def build_system_prompt(prompt_set: PromptSet, prompts: list[Prompt]) -> str:
    prompts_block = "\n".join(
        f"- id={prompt.id}: {prompt.text.strip()}"
        for prompt in prompts
    ) or "- No prompts configured."
    return render_prompt(
        "vlm.system",
        {
            "system_prompt": (
                f"You evaluate camera frames for PromptSet '{prompt_set.name}'. "
                "For each evaluation prompt, decide whether it appears to be happening."
            ),
            "prompts_block": prompts_block,
        },
    )


def apply_thresholds(
    result: PromptEvalResult,
    prompts: list[Prompt],
    *,
    floor: float | None = None,
) -> PromptEvalResult:
    """Recompute matched flags using global confidence floor."""
    conf_floor = floor if floor is not None else settings.confidence_floor
    known = {str(p.id) for p in prompts}
    hits: list[PromptHit] = []
    for hit in result.prompt_hits:
        if known and hit.prompt_id not in known:
            continue
        matched = bool(hit.matched) and hit.confidence >= conf_floor
        hits.append(
            PromptHit(
                prompt_id=hit.prompt_id,
                matched=matched,
                confidence=hit.confidence,
                rationale=hit.rationale,
            )
        )
    any_match = any(h.matched for h in hits)
    return PromptEvalResult(any_match=any_match, summary=result.summary, prompt_hits=hits)


async def evaluate_prompt_set(
    session: AsyncSession,
    redis: Redis,
    *,
    company_id: UUID,
    camera_id: UUID,
    establishment_id: UUID,
    frame_uris: list[str],
    user_context: str = "",
) -> tuple[LoadedPromptSet, PromptEvalResult, str] | None:
    """Run multi-prompt VLM eval. Returns None when no PromptSet is configured."""
    loaded = await load_prompt_set_for_camera(
        session,
        company_id=company_id,
        camera_id=camera_id,
        establishment_id=establishment_id,
    )
    if loaded is None:
        logger.warning(
            "No PromptSet for company=%s camera=%s",
            company_id,
            camera_id,
        )
        return None

    system_prompt = build_system_prompt(loaded.prompt_set, loaded.prompts)
    provider, raw = await analyze_with_failover(
        redis=redis,
        company_id=company_id,
        system_prompt=system_prompt,
        frame_uris=frame_uris,
        output_schema=output_schema(),
        user_context=user_context,
    )
    normalized = _normalize_prompt_ids(raw, loaded.prompts)
    parsed = apply_thresholds(parse_prompt_eval_result(normalized), loaded.prompts)
    return loaded, parsed, provider


def _normalize_prompt_ids(raw: dict, prompts: list[Prompt]) -> dict:
    """Map free-form prompt_id values to UUIDs when the model echoes text snippets."""
    by_id = {str(p.id): str(p.id) for p in prompts}
    by_text = {p.text.strip().lower()[:80]: str(p.id) for p in prompts}
    hits = raw.get("prompt_hits")
    if not isinstance(hits, list):
        if raw.get("any_match") and prompts:
            conf = float(raw.get("confidence", settings.confidence_floor))
            return {
                **raw,
                "prompt_hits": [
                    {
                        "prompt_id": str(p.id),
                        "matched": True,
                        "confidence": conf,
                        "rationale": str(raw.get("summary", "")),
                    }
                    for p in prompts
                ],
            }
        return raw

    fixed = []
    for hit in hits:
        if not isinstance(hit, dict):
            continue
        pid = str(hit.get("prompt_id", ""))
        mapped = by_id.get(pid) or by_text.get(pid.lower()[:80]) or pid
        fixed.append({**hit, "prompt_id": mapped})
    return {**raw, "prompt_hits": fixed}
