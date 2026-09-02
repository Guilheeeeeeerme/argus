"""Worker async/sync bridge utilities."""

from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from typing import TypeVar

T = TypeVar("T")


def run_async(coro: Coroutine[object, object, T]) -> T:
    """Run async coroutine from synchronous Celery task context."""
    return asyncio.run(coro)
