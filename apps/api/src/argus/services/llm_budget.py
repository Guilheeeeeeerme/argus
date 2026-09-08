"""Redis fixed-window LLM rate limit and daily budget for the worker. Fails closed."""

from __future__ import annotations

import time
from datetime import UTC, datetime
from uuid import UUID

from argus.config import settings
from argus.services.redis import get_redis

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


async def check_llm_allowance(company_id: UUID | str | None = None) -> str | None:
    """INCR fixed-window counters; returns the denial reason or None when allowed.

    Counters are per-company when ``company_id`` is provided, plus a global
    daily ceiling. Optional token/cost budgets halt when configured (>0).
    """
    redis = get_redis()
    tenant = str(company_id) if company_id else "global"

    minute_bucket = int(time.time() // 60)
    rate_key = f"{RATE_LIMIT_KEY_PREFIX}{tenant}:{minute_bucket}"
    rate_count = await redis.incr(rate_key)
    if rate_count == 1:
        await redis.expire(rate_key, RATE_LIMIT_TTL_SECONDS)
    if rate_count > settings.llm_rate_limit_per_minute:
        return RATE_LIMITED

    day_bucket = datetime.now(UTC).strftime("%Y%m%d")
    budget_key = f"{BUDGET_KEY_PREFIX}{tenant}:{day_bucket}"
    budget_count = await redis.incr(budget_key)
    if budget_count == 1:
        await redis.expire(budget_key, BUDGET_TTL_SECONDS)
    if budget_count > settings.llm_daily_budget:
        return BUDGET_EXCEEDED

    global_key = f"{GLOBAL_BUDGET_KEY_PREFIX}{day_bucket}"
    global_count = await redis.incr(global_key)
    if global_count == 1:
        await redis.expire(global_key, BUDGET_TTL_SECONDS)
    if global_count > settings.llm_global_daily_budget:
        return BUDGET_EXCEEDED

    if settings.llm_daily_token_budget > 0:
        token_key = f"{TOKEN_KEY_PREFIX}{tenant}:{day_bucket}"
        token_count = await redis.incrby(
            token_key, max(1, settings.llm_estimated_tokens_per_call)
        )
        if token_count == settings.llm_estimated_tokens_per_call:
            await redis.expire(token_key, BUDGET_TTL_SECONDS)
        if token_count > settings.llm_daily_token_budget:
            return TOKEN_BUDGET_EXCEEDED

    if settings.llm_daily_cost_usd > 0:
        cost_key = f"{COST_KEY_PREFIX}{tenant}:{day_bucket}"
        # Store micro-dollars as integers to avoid float Redis ops.
        micro = int(round(settings.llm_estimated_cost_per_call_usd * 1_000_000))
        cost_micro = await redis.incrby(cost_key, max(1, micro))
        if cost_micro == micro or cost_micro == 1:
            await redis.expire(cost_key, BUDGET_TTL_SECONDS)
        if cost_micro / 1_000_000 > settings.llm_daily_cost_usd:
            return COST_BUDGET_EXCEEDED

    return None
