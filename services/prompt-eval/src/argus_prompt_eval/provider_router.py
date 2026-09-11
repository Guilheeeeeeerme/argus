"""Provider failover + budgets — ordered LLM chain with Redis spend caps.

AI Engineering pattern: Provider failover + budgets.
Default order Gemini → OpenAI; keyless providers skipped; budgets fail closed.
"""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from redis.asyncio import Redis

from argus_prompt_eval.config import Settings, settings
from argus_prompt_eval.vlm import (
    GeminiVLMClient,
    MockVLMClient,
    OpenAIVLMClient,
    VLMClient,
)

logger = logging.getLogger(__name__)

RATE_LIMIT_KEY_PREFIX = "llm:rate:"
BUDGET_KEY_PREFIX = "llm:budget:"
TOKEN_KEY_PREFIX = "llm:tokens:"
COST_KEY_PREFIX = "llm:cost:"
GLOBAL_BUDGET_KEY_PREFIX = "llm:budget:global:"
RATE_LIMIT_TTL_SECONDS = 120
BUDGET_TTL_SECONDS = 172800

RATE_LIMITED = "rate_limit"
BUDGET_EXCEEDED = "budget_exceeded"
TOKEN_BUDGET_EXCEEDED = "token_budget_exceeded"
COST_BUDGET_EXCEEDED = "cost_budget_exceeded"

_KNOWN = ("gemini", "openai")


def resolve_llm_chain(s: Settings | None = None) -> list[tuple[str, VLMClient]]:
    """Ordered (provider_name, client) chain; unknown/keyless providers skipped."""
    target = s or settings
    names = [
        n.strip().lower() for n in target.llm_provider_order.split(",") if n.strip()
    ]
    chain: list[tuple[str, VLMClient]] = []
    for name in names:
        if name == "gemini" and target.gemini_api_key:
            chain.append(("gemini", GeminiVLMClient()))
        elif name == "openai" and target.openai_api_key:
            chain.append(("openai", OpenAIVLMClient()))
    if chain:
        return chain
    if target.auth0_use_mock:
        return [("mock", MockVLMClient())]
    raise RuntimeError(
        "No LLM provider configured: set GEMINI_API_KEY or OPENAI_API_KEY "
        "(mock fallback requires AUTH0_USE_MOCK)"
    )


async def check_llm_allowance(
    redis: Redis,
    company_id: UUID | str | None = None,
    *,
    s: Settings | None = None,
) -> str | None:
    """INCR fixed-window counters; returns denial reason or None when allowed."""
    target = s or settings
    tenant = str(company_id) if company_id else "global"

    minute_bucket = int(time.time() // 60)
    rate_key = f"{RATE_LIMIT_KEY_PREFIX}{tenant}:{minute_bucket}"
    rate_count = await redis.incr(rate_key)
    if rate_count == 1:
        await redis.expire(rate_key, RATE_LIMIT_TTL_SECONDS)
    if rate_count > target.llm_rate_limit_per_minute:
        return RATE_LIMITED

    day_bucket = datetime.now(UTC).strftime("%Y%m%d")
    budget_key = f"{BUDGET_KEY_PREFIX}{tenant}:{day_bucket}"
    budget_count = await redis.incr(budget_key)
    if budget_count == 1:
        await redis.expire(budget_key, BUDGET_TTL_SECONDS)
    if budget_count > target.llm_daily_budget:
        return BUDGET_EXCEEDED

    global_key = f"{GLOBAL_BUDGET_KEY_PREFIX}{day_bucket}"
    global_count = await redis.incr(global_key)
    if global_count == 1:
        await redis.expire(global_key, BUDGET_TTL_SECONDS)
    if global_count > target.llm_global_daily_budget:
        return BUDGET_EXCEEDED

    if target.llm_daily_token_budget > 0:
        token_key = f"{TOKEN_KEY_PREFIX}{tenant}:{day_bucket}"
        token_count = await redis.incrby(
            token_key, max(1, target.llm_estimated_tokens_per_call)
        )
        if token_count == target.llm_estimated_tokens_per_call:
            await redis.expire(token_key, BUDGET_TTL_SECONDS)
        if token_count > target.llm_daily_token_budget:
            return TOKEN_BUDGET_EXCEEDED

    if target.llm_daily_cost_usd > 0:
        cost_key = f"{COST_KEY_PREFIX}{tenant}:{day_bucket}"
        micro = int(round(target.llm_estimated_cost_per_call_usd * 1_000_000))
        cost_micro = await redis.incrby(cost_key, max(1, micro))
        if cost_micro == micro or cost_micro == 1:
            await redis.expire(cost_key, BUDGET_TTL_SECONDS)
        if cost_micro / 1_000_000 > target.llm_daily_cost_usd:
            return COST_BUDGET_EXCEEDED

    return None


async def analyze_with_failover(
    *,
    redis: Redis,
    company_id: UUID,
    system_prompt: str,
    frame_uris: list[str],
    output_schema: dict[str, Any],
    user_context: str = "",
) -> tuple[str, dict[str, Any]]:
    """Try providers in order; raise after all fail or budget denial."""
    denial = await check_llm_allowance(redis, company_id)
    if denial is not None:
        raise RuntimeError(f"LLM budget denied: {denial}")

    errors: list[str] = []
    for name, client in resolve_llm_chain():
        try:
            result = client.analyze(
                system_prompt=system_prompt,
                frame_uris=frame_uris,
                output_schema=output_schema,
                user_context=user_context,
            )
            return name, result
        except Exception as exc:  # noqa: BLE001 — failover across providers
            logger.warning("Provider %s failed: %s", name, exc)
            errors.append(f"{name}: {exc}")
    raise RuntimeError("All LLM providers failed: " + "; ".join(errors))
