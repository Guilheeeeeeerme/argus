"""LLM budget helpers — Evidence/VLM worker paths retired from MVP."""

from __future__ import annotations

import os
from datetime import UTC, datetime

import pytest
import pytest_asyncio

os.environ.setdefault("AUTH0_USE_MOCK", "true")

from argus.config import settings  # noqa: E402
from argus.services.database import dispose_engine  # noqa: E402
from argus.services.llm_budget import BUDGET_EXCEEDED, check_llm_allowance  # noqa: E402
from argus.services.redis import close_redis, get_redis  # noqa: E402

SEED_COMPANY_ID = "11111111-1111-4111-8111-111111111111"


@pytest_asyncio.fixture(autouse=True)
async def _cleanup():
    yield
    await close_redis()
    await dispose_engine()


@pytest.mark.asyncio
async def test_check_llm_allowance_denies_over_budget() -> None:
    redis = get_redis()
    today = datetime.now(UTC).strftime("%Y%m%d")
    key = f"llm:budget:{SEED_COMPANY_ID}:{today}"
    await redis.set(key, int(settings.llm_daily_budget) + 1)
    try:
        assert await check_llm_allowance(SEED_COMPANY_ID) == BUDGET_EXCEEDED
    finally:
        await redis.delete(key)


@pytest.mark.skip(reason="Evidence / Celery VLM analyzer paths removed from MVP domain")
@pytest.mark.asyncio
async def test_budget_exhausted_skips_llm_call() -> None:
    pass


@pytest.mark.skip(reason="Evidence / Celery VLM analyzer paths removed from MVP domain")
@pytest.mark.asyncio
async def test_rate_limit_exhausted_skips_llm_call() -> None:
    pass


@pytest.mark.skip(reason="Evidence / Celery VLM analyzer paths removed from MVP domain")
@pytest.mark.asyncio
async def test_policy_block_skips_llm_call() -> None:
    pass
