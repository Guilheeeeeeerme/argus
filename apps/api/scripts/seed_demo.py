#!/usr/bin/env python3
"""Idempotent demo seed — generic establishment (no retail language).

Platform ROOT/ADMIN are created by bootstrap / seed_platform, never here.
"""

from __future__ import annotations

import asyncio
import os
import sys
import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from argus.config import settings  # noqa: E402
from argus.core.passwords import hash_password  # noqa: E402
from argus.domain.enums import UserRole  # noqa: E402
from argus.domain.models import (  # noqa: E402
    Camera,
    Company,
    CompanyUser,
    Establishment,
    Prompt,
    PromptSet,
    WebhookEndpoint,
)
from argus.services.database import set_session_context  # noqa: E402

COMPANY_DEMO_ID = uuid.UUID("11111111-1111-4111-8111-111111111111")
ESTABLISHMENT_DEMO_ID = uuid.UUID("22222222-2222-4222-8222-222222222222")
CAMERA_DEMO_ID = uuid.UUID("33333333-3333-4333-8333-333333333333")
PROMPT_SET_ID = uuid.UUID("55555555-5555-4555-8555-555555555555")
PROMPT_ID = uuid.UUID("77777777-7777-4777-8777-777777777777")
USER_MANAGER_ID = uuid.UUID("99999999-9999-4999-8999-999999999999")
USER_GUEST_ID = uuid.UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
WEBHOOK_ID = uuid.UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")

DEFAULT_PASSWORD = "Password123!"
DEMO_WEBHOOK_TOKEN = "demo-webhook-token-change-me"


def demo_password() -> str:
    return os.environ.get("DEMO_PASSWORD") or DEFAULT_PASSWORD


async def seed_demo(session: AsyncSession) -> dict[str, str]:
    await set_session_context(session, company_id=None, role=UserRole.ROOT.value)
    ids: dict[str, str] = {}

    company = await session.get(Company, COMPANY_DEMO_ID)
    if company is None:
        company = Company(
            id=COMPANY_DEMO_ID,
            name="Demo Company",
            slug="demo-company",
        )
        session.add(company)
        await session.flush()
    ids["company_id"] = str(company.id)

    establishment = await session.get(Establishment, ESTABLISHMENT_DEMO_ID)
    if establishment is None:
        establishment = Establishment(
            id=ESTABLISHMENT_DEMO_ID,
            company_id=company.id,
            name="Demo Establishment",
            address="1 Example Way",
            timezone="UTC",
            active=True,
        )
        session.add(establishment)
        await session.flush()
    ids["establishment_id"] = str(establishment.id)

    camera = await session.get(Camera, CAMERA_DEMO_ID)
    if camera is None:
        camera = Camera(
            id=CAMERA_DEMO_ID,
            company_id=company.id,
            establishment_id=establishment.id,
            name="Cam 01 — Lobby",
            stream_url="rtsp://example.invalid/cam01",
            is_active=True,
        )
        session.add(camera)
        await session.flush()
    ids["camera_id"] = str(camera.id)

    prompt_set = await session.get(PromptSet, PROMPT_SET_ID)
    if prompt_set is None:
        prompt_set = PromptSet(
            id=PROMPT_SET_ID,
            company_id=company.id,
            camera_id=camera.id,
            name="Default watchlist",
        )
        session.add(prompt_set)
        await session.flush()
    ids["prompt_set_id"] = str(prompt_set.id)

    prompt = await session.get(Prompt, PROMPT_ID)
    if prompt is None:
        prompt = Prompt(
            id=PROMPT_ID,
            company_id=company.id,
            prompt_set_id=prompt_set.id,
            text="Is there an unauthorized person in a restricted area?",
            enabled=True,
            sort_order=0,
        )
        session.add(prompt)
        await session.flush()
    ids["prompt_id"] = str(prompt.id)

    token = os.environ.get("DEMO_WEBHOOK_TOKEN") or DEMO_WEBHOOK_TOKEN
    webhook = await session.get(WebhookEndpoint, WEBHOOK_ID)
    if webhook is None:
        webhook = WebhookEndpoint(
            id=WEBHOOK_ID,
            company_id=company.id,
            establishment_id=establishment.id,
            name="Demo inbound context",
            token_hash=hash_password(token),
            active=True,
        )
        session.add(webhook)
        await session.flush()
    ids["webhook_token"] = token
    ids["webhook_id"] = str(WEBHOOK_ID)

    password_hash = hash_password(demo_password())
    for user_id, email, role, name in (
        (USER_MANAGER_ID, "manager@demo.local", UserRole.MANAGER, "Demo Manager"),
        (USER_GUEST_ID, "guest@demo.local", UserRole.OPERATOR, "Demo Operator"),
    ):
        user = await session.get(CompanyUser, user_id)
        if user is None:
            existing = await session.scalar(
                select(CompanyUser).where(CompanyUser.email == email)
            )
            if existing is None:
                session.add(
                    CompanyUser(
                        id=user_id,
                        company_id=company.id,
                        email=email,
                        name=name,
                        role=role,
                        password_hash=password_hash,
                    )
                )
        ids[f"user_{role.value}"] = str(user_id)

    await session.commit()
    return ids


async def main() -> int:
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        ids = await seed_demo(session)
    await engine.dispose()
    print("Demo seed complete:", ids)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
