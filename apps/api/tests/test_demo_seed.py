"""Opt-in demo seed regression against an isolated disposable Postgres database."""

import asyncio
import importlib.util
import os
import sys
import uuid
from pathlib import Path

import pytest


@pytest.mark.skipif(
    not os.getenv("ARGUS_DEMO_TEST_URL"), reason="disposable Postgres required"
)
def test_demo_seed_is_complete_idempotent_and_preserves_edits():
    import asyncpg
    from argus.domain.base import Base
    from argus.domain.models import (
        Camera,
        Account,
        AccountUser,
        AccountUserMembership,
        Prompt,
    )
    from sqlalchemy import func, select, text
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    scripts = Path(__file__).resolve().parents[1] / "scripts"
    sys.path.insert(0, str(scripts))
    spec = importlib.util.spec_from_file_location(
        "demo_seed_test", scripts / "seed_demo.py"
    )
    seed = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(seed)

    async def verify():
        from urllib.parse import urlsplit, urlunsplit

        url = os.environ["ARGUS_DEMO_TEST_URL"]
        database = "argus_demo_test_" + uuid.uuid4().hex
        admin = await asyncpg.connect(url)
        engine = None
        try:
            await admin.execute(f'CREATE DATABASE "{database}"')
            parts = urlsplit(url)
            test_url = urlunsplit(
                ("postgresql+asyncpg", parts.netloc, "/" + database, "", "")
            )
            engine = create_async_engine(test_url)
            async with engine.begin() as connection:
                await connection.execute(text("CREATE EXTENSION vector"))
                await connection.run_sync(Base.metadata.create_all)
            factory = async_sessionmaker(engine, expire_on_commit=False)
            async with factory() as session:
                first = await seed.seed_demo(session)
                user = await session.get(AccountUser, seed.USER_MANAGER_ID)
                saved_password = user.password_hash
                camera = await session.get(Camera, seed.CAMERA_DEMO_ID)
                camera.stream_url = "rtsp://operator-edited.example.test/live"
                prompt = await session.get(Prompt, seed.PROMPT_ID)
                prompt.text = "Operator edited prompt"
                await session.commit()
                second = await seed.seed_demo(session)
                assert first == second
                assert not any("password" in key or "token" in key for key in second)
                for model, count in [
                    (Account, 2),
                    (Camera, 3),
                    (Prompt, 6),
                    (AccountUser, 2),
                    (AccountUserMembership, 3),
                ]:
                    assert (
                        await session.scalar(select(func.count()).select_from(model))
                        == count
                    )
                assert user.password_hash == saved_password
                assert camera.stream_url == "rtsp://operator-edited.example.test/live"
                assert prompt.text == "Operator edited prompt"
        finally:
            if engine:
                await engine.dispose()
            await admin.execute(f'DROP DATABASE IF EXISTS "{database}" WITH (FORCE)')
            await admin.close()

    asyncio.run(verify())
