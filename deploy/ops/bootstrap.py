"""Ported from infra/containers/argus/bootstrap.py — no changes to behavior.

Creates the initial platform ROOT account (idempotent) and ensures the frame
bucket exists. Invoked by deploy/migrate.sh inside the one-shot `migrate`
service (same image as api), using ADMIN_DATABASE_URL and dev/seed env vars.
"""

import asyncio
import os

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from argus.config import settings
from argus.core.passwords import hash_password
from argus.domain.enums import UserRole
from argus.domain.models import AccountUser
from argus.services.database import set_session_context
from argus.services.storage import ensure_bucket_exists


async def main():
    engine = create_async_engine(settings.admin_database_url)
    async with async_sessionmaker(engine)() as session:
        await set_session_context(session, account_id=None, role=UserRole.ROOT.value)
        email = os.environ["DEV_ROOT_EMAIL"]
        if not await session.scalar(select(AccountUser).where(AccountUser.email == email)):
            session.add(AccountUser(email=email, account_id=None, role=UserRole.ROOT,
                                    password_hash=hash_password(os.environ["DEV_ROOT_PASSWORD"])))
            await session.commit()
    await engine.dispose()
    await ensure_bucket_exists()


asyncio.run(main())
