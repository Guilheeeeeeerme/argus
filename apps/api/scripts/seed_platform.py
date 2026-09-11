#!/usr/bin/env python3
"""Create platform ROOT only (no demo tenants). Used by local entrypoint."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from argus.config import settings  # noqa: E402
from argus.core.passwords import hash_password  # noqa: E402
from argus.domain.enums import UserRole  # noqa: E402
from argus.domain.models import CompanyUser  # noqa: E402
from argus.services.database import set_session_context  # noqa: E402


async def main() -> int:
    email = os.environ.get("DEV_ROOT_EMAIL") or settings.dev_root_email
    password = os.environ.get("DEV_ROOT_PASSWORD") or "Password123!"
    engine = create_async_engine(settings.admin_database_url, pool_pre_ping=True)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        await set_session_context(session, company_id=None, role=UserRole.ROOT.value)
        if not await session.scalar(select(CompanyUser).where(CompanyUser.email == email)):
            session.add(
                CompanyUser(
                    email=email,
                    company_id=None,
                    role=UserRole.ROOT,
                    password_hash=hash_password(password),
                )
            )
            await session.commit()
            print(f"platform_root={email}")
        else:
            print(f"platform_root_exists={email}")
    await engine.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
