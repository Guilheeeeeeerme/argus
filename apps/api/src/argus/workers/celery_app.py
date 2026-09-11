"""Celery application — retained for optional offline jobs; VLM moved to prompt-eval."""

from __future__ import annotations

from celery import Celery

from argus.config import settings

celery_app = Celery(
    "argus",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "argus.integrations.model_rank",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_routes={
        "models.*": {"queue": "vlm"},
    },
    beat_schedule={
        "refresh-model-rank": {
            "task": "models.refresh_rank",
            "schedule": max(1.0, settings.model_rank_refresh_ms / 1000.0),
        },
    },
)
