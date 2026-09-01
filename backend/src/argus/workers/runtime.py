"""Worker runtime entrypoints."""

from __future__ import annotations

import os
import sys

from argus.config import settings


def exec_celery_worker(*, queues: str, beat: bool = False) -> None:
    argv = [
        "celery",
        "-A",
        "argus.workers.celery_app",
    ]
    if beat:
        argv.extend(["beat", "-l", settings.log_level.lower()])
    else:
        argv.extend(
            [
                "worker",
                "-Q",
                queues,
                "-l",
                settings.log_level.lower(),
                "--concurrency",
                "2",
            ]
        )
    os.execvp("celery", argv)


def run_worker_for_role(role: str) -> None:
    if role == "worker-vlm":
        exec_celery_worker(queues="vlm")
    elif role == "worker-aggregator":
        exec_celery_worker(queues="aggregate")
    elif role == "worker-notify":
        exec_celery_worker(queues="notify")
    elif role == "worker-scheduler":
        os.execvp(
            "celery",
            [
                "celery",
                "-A",
                "argus.workers.celery_app",
                "worker",
                "-Q",
                "schedule",
                "-B",
                "-l",
                settings.log_level.lower(),
                "--concurrency",
                "1",
            ],
        )
    else:
        print(f"Unknown worker role: {role}", file=sys.stderr)
        sys.exit(1)
