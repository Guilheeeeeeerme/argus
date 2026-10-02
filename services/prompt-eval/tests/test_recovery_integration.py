"""Run with explicit disposable Redis/Postgres URLs; never target production."""

import asyncio
import os
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from argus_prompt_eval import redis_io
from argus_prompt_eval._models_fallback import Base
from argus_prompt_eval.persist import find_positive, persist_positive
from argus_prompt_eval.structured_output import PromptEvalResult, PromptHit
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


@pytest.mark.skipif(
    not os.getenv("TEST_RECOVERY_REDIS_URL"), reason="needs disposable Redis"
)
def test_redis_recovers_old_consumer_and_respects_idle(monkeypatch):
    async def run():
        client = Redis.from_url(
            os.environ["TEST_RECOVERY_REDIS_URL"], decode_responses=True
        )
        monkeypatch.setattr(redis_io, "_client", client)
        stream, group = "test:" + str(uuid4()), "eval"
        monkeypatch.setattr(redis_io.settings, "consumer_retry_idle_ms", 1000)
        monkeypatch.setattr(redis_io.settings, "consumer_batch_size", 1)
        try:
            await client.xgroup_create(stream, group, id="0", mkstream=True)
            ids = [await client.xadd(stream, {"sequence_id": str(i)}) for i in range(2)]
            await client.xreadgroup(group, "retired-consumer", {stream: ">"})
            assert (await redis_io.claim_pending(stream, group, "current", "0-0"))[
                1
            ] == []
            for message_id in ids:
                await client.xclaim(
                    stream, group, "retired-consumer", 0, [message_id], idle=2000
                )
            cursor, first = await redis_io.claim_pending(
                stream, group, "current", "0-0"
            )
            _, second = await redis_io.claim_pending(stream, group, "current", cursor)
            assert [first[0][0], second[0][0]] == ids
            # A failed attempt remains pending but cannot spin immediately.
            assert (await redis_io.claim_pending(stream, group, "current", "0-0"))[
                1
            ] == []
            await client.xack(stream, group, *ids)
            assert (await client.xpending(stream, group))["pending"] == 0
        finally:
            await client.delete(stream)
            await client.aclose()

    asyncio.run(run())


@pytest.mark.skipif(
    not os.getenv("TEST_RECOVERY_POSTGRES_URL"), reason="needs disposable Postgres"
)
def test_postgres_replay_and_concurrent_claim_share_one_detection():
    async def run():
        admin = create_async_engine(os.environ["TEST_RECOVERY_POSTGRES_URL"])
        async with admin.begin() as connection:
            await connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await connection.run_sync(Base.metadata.create_all)
            if not await connection.scalar(
                text("SELECT 1 FROM pg_roles WHERE rolname = 'argus_app'")
            ):
                await connection.execute(text("CREATE ROLE argus_app LOGIN"))
            await connection.execute(text("GRANT USAGE ON SCHEMA public TO argus_app"))
            await connection.execute(
                text("GRANT ALL ON ALL TABLES IN SCHEMA public TO argus_app")
            )
        engine = create_async_engine(admin.url.set(username="argus_app"))
        factory = async_sessionmaker(engine, expire_on_commit=False)
        company, camera, establishment = uuid4(), uuid4(), uuid4()
        args = {"company_id": company, "camera_id": camera, "sequence_id": "retry"}
        try:
            async with factory() as first, factory() as second:
                assert await find_positive(first, **args) is None
                waiting = asyncio.create_task(find_positive(second, **args))
                # A second consumer must wait while the first transaction owns it.
                with pytest.raises(TimeoutError):
                    await asyncio.wait_for(asyncio.shield(waiting), 0.1)
                now = datetime.now(UTC)
                detection, triage = await persist_positive(
                    first,
                    **args,
                    establishment_id=establishment,
                    result=PromptEvalResult(
                        any_match=True,
                        prompt_hits=[
                            PromptHit(prompt_id="p", matched=True, confidence=0.9)
                        ],
                    ),
                    evidence=SimpleNamespace(
                        clip_uri="clip",
                        frame_uris=["frame"],
                        window=SimpleNamespace(start=now, end=now),
                    ),
                )
                await first.commit()
                replay = await asyncio.wait_for(waiting, 2)
                assert replay[0].id == detection.id
                assert replay[1].id == triage.id
                await second.commit()
            async with factory() as other:
                assert (
                    await find_positive(other, **{**args, "company_id": uuid4()})
                    is None
                )
        finally:
            await engine.dispose()
            await admin.dispose()

    asyncio.run(run())
