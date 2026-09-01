"""Celery application — Redis broker and task routing."""

from __future__ import annotations

from celery import Celery

from argus.config import settings

celery_app = Celery(
    "argus",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "argus.workers.vlm_analyzer",
        "argus.workers.aggregator",
        "argus.workers.scheduler",
        "argus.workers.notifier",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_routes={
        "vlm.*": {"queue": "vlm"},
        "aggregate.*": {"queue": "aggregate"},
        "notify.*": {"queue": "notify"},
        "schedule.*": {"queue": "schedule"},
    },
    beat_schedule={
        "activate-scheduled-modes": {
            "task": "schedule.activate_scheduled_modes",
            "schedule": 60.0,
        },
        "poll-ingest-stream": {
            "task": "vlm.process_ingest_stream",
            "schedule": 2.0,
        },
    },
)
