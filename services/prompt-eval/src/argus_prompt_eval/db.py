"""Database engine, RLS session context, and ORM model imports.

AI Engineering note: prefers shared ``argus.domain.models`` (copied into the
image via Dockerfile PYTHONPATH). Falls back to local table mirrors only when
the shared package is unavailable.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from functools import lru_cache
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from argus_prompt_eval.config import settings

try:
    from argus.domain.enums import FeedbackDisposition, TriageCaseState
    from argus.domain.models import (
        ContextEvent,
        Detection,
        Feedback,
        Prompt,
        PromptSet,
        TriageCase,
    )

    _USING_SHARED_MODELS = True
except ImportError:  # pragma: no cover — standalone / unit-test fallback
    from argus_prompt_eval._models_fallback import (  # type: ignore[no-redef]
        ContextEvent,
        Detection,
        Feedback,
        FeedbackDisposition,
        Prompt,
        PromptSet,
        TriageCase,
        TriageCaseState,
    )

    _USING_SHARED_MODELS = False


@lru_cache
def get_engine() -> AsyncEngine:
    return create_async_engine(settings.database_url, pool_pre_ping=True)


@lru_cache
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(get_engine(), expire_on_commit=False)


async def set_session_context(
    session: AsyncSession,
    *,
    company_id: UUID | None = None,
    role: str | None = "manager",
) -> None:
    """Inject PostgreSQL GUCs consumed by RLS policies."""
    await session.execute(
        text("SELECT set_config('app.current_company_id', :value, true)"),
        {"value": str(company_id) if company_id is not None else ""},
    )
    if role is not None:
        await session.execute(
            text("SELECT set_config('app.current_role', :value, true)"),
            {"value": role},
        )


@asynccontextmanager
async def company_session(
    company_id: UUID,
    role: str = "manager",
) -> AsyncGenerator[AsyncSession, None]:
    factory = get_session_factory()
    async with factory() as session:
        await set_session_context(session, company_id=company_id, role=role)
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


__all__ = [
    "ContextEvent",
    "Detection",
    "Feedback",
    "FeedbackDisposition",
    "Prompt",
    "PromptSet",
    "TriageCase",
    "TriageCaseState",
    "company_session",
    "get_engine",
    "get_session_factory",
    "set_session_context",
    "_USING_SHARED_MODELS",
]
