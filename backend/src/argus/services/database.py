"""Async SQLAlchemy engine, sessions, and RLS session-variable injection."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from argus.config import settings

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            settings.database_url,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_factory


async def set_session_context(
    session: AsyncSession,
    *,
    tenant_id: UUID | None = None,
    role: str | None = None,
) -> None:
    """Inject PostgreSQL GUCs consumed by RLS policies (uses set_config, not SET LOCAL)."""
    if tenant_id is not None:
        await session.execute(
            text("SELECT set_config('app.current_tenant_id', :value, true)"),
            {"value": str(tenant_id)},
        )
    if role is not None:
        await session.execute(
            text("SELECT set_config('app.current_role', :value, true)"),
            {"value": role},
        )


@asynccontextmanager
async def tenant_session(
    tenant_id: UUID | None,
    role: str,
) -> AsyncGenerator[AsyncSession, None]:
    """Transactional session with RLS context applied."""
    factory = get_session_factory()
    async with factory() as session:
        await set_session_context(session, tenant_id=tenant_id, role=role)
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency — session without auth context (internal/worker use)."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def check_database_connection() -> bool:
    engine = get_engine()
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT 1"))
        return result.scalar_one() == 1


async def dispose_engine() -> None:
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None
