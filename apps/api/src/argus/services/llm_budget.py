"""Redis fixed-window LLM rate limit and daily budget for the worker. Fails closed."""

from __future__ import annotations

import time
from datetime import UTC, datetime

from argus.config import settings
from argus.services.redis import get_redis

RATE_LIMIT_KEY_PREFIX = "llm:rate:"
BUDGET_KEY_PREFIX = "llm:budget:"
RATE_LIMIT_TTL_SECONDS = 120
BUDGET_TTL_SECONDS = 172800

RATE_LIMITED = "rate_limit"
BUDGET_EXCEEDED = "budget_exceeded"


async def check_llm_allowance() -> str | None:
    """INCR fixed-window counters; returns the denial reason or None when allowed."""
    redis = get_redis()

    minute_bucket = int(time.time() // 60)
    rate_key = f"{RATE_LIMIT_KEY_PREFIX}{minute_bucket}"
    rate_count = await redis.incr(rate_key)
    if rate_count == 1:
        await redis.expire(rate_key, RATE_LIMIT_TTL_SECONDS)
    if rate_count > settings.llm_rate_limit_per_minute:
        return RATE_LIMITED

    day_bucket = datetime.now(UTC).strftime("%Y%m%d")
    budget_key = f"{BUDGET_KEY_PREFIX}{day_bucket}"
    budget_count = await redis.incr(budget_key)
    if budget_count == 1:
        await redis.expire(budget_key, BUDGET_TTL_SECONDS)
    if budget_count > settings.llm_daily_budget:
        return BUDGET_EXCEEDED

    return None
