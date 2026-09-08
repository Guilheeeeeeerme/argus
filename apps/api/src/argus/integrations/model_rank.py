"""Cheapest-first model ranking with Redis caching, refreshed by Celery beat."""

from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime
from typing import Any

from argus.config import settings
from argus.services.redis import get_redis, set_key
from argus.workers.celery_app import celery_app
from argus.workers.utils import run_async

logger = logging.getLogger(__name__)

RANK_KEY_TEMPLATE = "models:rank:{provider}"
RANK_UPDATED_AT_KEY = "models:rank:updatedAt"


def _gemini_list_url() -> str:
    return settings.gemini_base_url.rstrip("/") + "/v1beta/models"

_SEED_MODEL_PRICES: dict[str, list[tuple[str, float]]] = {
    "gemini": [
        ("gemini-2.5-flash-lite", 0.10),
        ("gemini-2.5-flash", 0.30),
        ("gemini-3-flash", 0.30),
    ],
    "openai": [
        ("gpt-5-nano", 0.05),
        ("gpt-4.1-nano", 0.10),
        ("gpt-4o-mini", 0.15),
    ],
}

_EXCLUDED_MODEL_PATTERN = re.compile(
    r"(?i)(embed|image|imagen|tts|aqa|realtime|audio|moderation|vision|whisper|search|veo|distill)"
)

_ALLOWED_MODEL_PREFIXES: dict[str, tuple[str, ...]] = {
    "gemini": ("gemini-2", "gemini-3", "gemini-1.5", "gemini-flash", "gemini-pro"),
    "openai": ("gpt-4", "gpt-5", "gpt-3.5", "o1", "o3", "o4"),
}


def _is_allowlisted_model(provider: str, name: str) -> bool:
    prefixes = _ALLOWED_MODEL_PREFIXES.get(provider, ())
    lower = name.lower()
    if _EXCLUDED_MODEL_PATTERN.search(lower):
        return False
    return any(lower.startswith(prefix) for prefix in prefixes)


def _seed_candidates(provider: str) -> list[tuple[str, float]]:
    return list(_SEED_MODEL_PRICES.get(provider, []))


def _enrich_candidates(provider: str, candidates: list[tuple[str, float]]) -> list[tuple[str, float]]:
    """Best-effort provider models.list enrichment. Never crashes the caller.

    Unknown / non-allowlisted model IDs are ignored (not inserted at inf price).
    """
    known_prices = {name: price for name, price in candidates}
    try:
        if provider == "gemini":
            import httpx

            if settings.gemini_api_key:
                response = httpx.get(
                    _gemini_list_url(),
                    headers={"x-goog-api-key": settings.gemini_api_key},
                    timeout=10,
                )
                response.raise_for_status()
                for model in response.json().get("models", []):
                    methods = model.get("supportedGenerationMethods") or []
                    if "generateContent" not in methods:
                        continue
                    name = (model.get("name") or "").removeprefix("models/")
                    if name and _is_allowlisted_model(provider, name) and name not in known_prices:
                        # Only promote models we already priced via seeds.
                        continue
        elif provider == "openai":
            from openai import OpenAI

            if settings.openai_api_key:
                client = OpenAI(
                    api_key=settings.openai_api_key,
                    base_url=settings.openai_base_url or None,
                )
                for model in client.models.list():
                    model_id = getattr(model, "id", "")
                    if (
                        model_id
                        and _is_allowlisted_model(provider, model_id)
                        and model_id not in known_prices
                    ):
                        continue
    except Exception:
        logger.info("Model rank enrichment unavailable for %s; using seeds", provider)
    return candidates


def compute_rank(provider: str, *, top_n: int | None = None) -> list[str]:
    limit = top_n if top_n is not None else settings.model_rank_top_n
    # Enrichment is best-effort discovery only; production rank stays seed-priced.
    _enrich_candidates(provider, _seed_candidates(provider))
    candidates = _seed_candidates(provider)
    seen: set[str] = set()
    unique: list[tuple[str, float]] = []
    for name, price in candidates:
        if not _is_allowlisted_model(provider, name):
            continue
        if name in seen:
            continue
        seen.add(name)
        unique.append((name, price))
    unique.sort(key=lambda item: item[1])
    return [name for name, _price in unique[: max(1, limit)]]


async def refresh_rank_cache(provider: str) -> list[str]:
    rank = compute_rank(provider)
    await set_key(RANK_KEY_TEMPLATE.format(provider=provider), json.dumps(rank))
    await set_key(
        RANK_UPDATED_AT_KEY,
        datetime.now(UTC).isoformat(),
    )
    logger.info("Model rank refreshed for %s: %s", provider, rank)
    return rank


async def rank_for(provider: str) -> list[str]:
    """Cheapest-first model names for a provider, cached in Redis with in-code fallback."""
    try:
        raw = await get_redis().get(RANK_KEY_TEMPLATE.format(provider=provider))
    except Exception:
        raw = None
    if raw:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list) and parsed and all(isinstance(m, str) for m in parsed):
                return parsed
        except (TypeError, ValueError):
            logger.info("Invalid model rank cache for %s; using defaults", provider)
    return [name for name, _price in _seed_candidates(provider)[: max(1, settings.model_rank_top_n)]]


@celery_app.task(name="models.refresh_rank")
def refresh_rank() -> dict[str, list[str]]:
    return run_async(_refresh_all_ranks())


async def _refresh_all_ranks() -> dict[str, list[str]]:
    refreshed: dict[str, list[str]] = {}
    for provider in sorted(_SEED_MODEL_PRICES):
        refreshed[provider] = await refresh_rank_cache(provider)
    return refreshed
