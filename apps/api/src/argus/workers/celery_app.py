"""Celery application — retained for optional offline jobs; VLM lives in prompt-eval.

No beat schedule: the model is pinned via ``GEMINI_MODEL`` (no runtime ranking).
"""

from __future__ import annotations

from celery import Celery

from argus.config import settings

celery_app = Celery(
    "argus",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={},
)
