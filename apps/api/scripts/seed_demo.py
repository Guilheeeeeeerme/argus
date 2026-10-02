#!/usr/bin/env python3
"""Idempotent public-camera demo; preserve operator edits and existing passwords.

Platform ROOT/ADMIN are created by bootstrap / seed_platform, never here.
"""

from __future__ import annotations

import asyncio
import os
import sys
import uuid
from pathlib import Path
from urllib.parse import urlsplit

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from argus.config import settings
from argus.core.passwords import hash_password
from argus.domain.enums import UserRole
from argus.domain.models import (
    Camera,
    Company,
    CompanyUser,
    CompanyUserMembership,
    Establishment,
    Prompt,
    PromptSet,
    WebhookEndpoint,
)
from argus.services.database import set_session_context
from demo_catalog import CAMERAS, SOURCE_PAGE, SOURCE_TERMS

COMPANY_DEMO_ID = uuid.UUID("11111111-1111-4111-8111-111111111111")
ESTABLISHMENT_DEMO_ID = uuid.UUID("22222222-2222-4222-8222-222222222222")
CAMERA_DEMO_ID = uuid.UUID("33333333-3333-4333-8333-333333333333")
PROMPT_SET_ID = uuid.UUID("55555555-5555-4555-8555-555555555555")
PROMPT_ID = uuid.UUID("77777777-7777-4777-8777-777777777777")
USER_MANAGER_ID = uuid.UUID("99999999-9999-4999-8999-999999999999")
USER_GUEST_ID = uuid.UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
WEBHOOK_ID = uuid.UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")

SANDBOX_COMPANY_ID = uuid.uuid5(COMPANY_DEMO_ID, "sandbox-company")

DEFAULT_PASSWORD = "Password123!"
DEMO_WEBHOOK_TOKEN = "demo-webhook-token-change-me"


def demo_password() -> str:
    configured = os.environ.get("DEMO_PASSWORD")
    if configured:
        return configured
    if urlsplit(settings.database_url).hostname not in {"localhost", "127.0.0.1", "::1", "postgres"}:
        raise ValueError("DEMO_PASSWORD must be configured for a remote demo database")
    return DEFAULT_PASSWORD


async def seed_demo(session: AsyncSession) -> dict[str, str]:
    await set_session_context(session, company_id=None, role=UserRole.ROOT.value)
    ids: dict[str, str] = {}

    company = await session.get(Company, COMPANY_DEMO_ID)
    if company is None:
        company = Company(
            id=COMPANY_DEMO_ID,
            name="Argus Demo Brasil",
            slug="demo-company",
        )
        session.add(company)
        await session.flush()
    ids["company_id"] = str(company.id)

    if company.name in {"Demo Company", "Argus Public Camera Demo"}:
        company.name = "Argus Demo Brasil"
    company.settings = {
        **(company.settings or {}),
        "demo_source": "Câmeras públicas de tráfego (Caltrans, EUA) — vídeo de demonstração",
        "demo_source_url": SOURCE_PAGE,
        "demo_source_terms": SOURCE_TERMS,
    }
    sandbox = await session.get(Company, SANDBOX_COMPANY_ID)
    if sandbox is None:
        session.add(
            Company(id=SANDBOX_COMPANY_ID, name="Sandbox de Demonstração", slug="demo-sandbox")
        )
        await session.flush()
    ids["sandbox_company_id"] = str(SANDBOX_COMPANY_ID)

    for index, item in enumerate(CAMERAS):
        site_id = (
            ESTABLISHMENT_DEMO_ID
            if index == 0
            else uuid.uuid5(COMPANY_DEMO_ID, item["key"] + ":site")
        )
        camera_id = (
            CAMERA_DEMO_ID
            if index == 0
            else uuid.uuid5(COMPANY_DEMO_ID, item["key"] + ":camera")
        )
        set_id = (
            PROMPT_SET_ID
            if index == 0
            else uuid.uuid5(COMPANY_DEMO_ID, item["key"] + ":prompts")
        )
        establishment = await session.get(Establishment, site_id)
        if establishment is None:
            establishment = Establishment(
                id=site_id,
                company_id=company.id,
                name=item["site"],
                address="São Paulo, SP, Brasil",
                timezone="America/Sao_Paulo",
                active=True,
            )
            session.add(establishment)
            await session.flush()
        elif establishment.name == "Demo Establishment":
            establishment.name = item["site"]
            establishment.address = "São Paulo, SP, Brasil"
            establishment.timezone = "America/Sao_Paulo"
        camera = await session.get(Camera, camera_id)
        stream = "ffmpeg:" + item["playlist"] + "#video=copy"
        if camera is None:
            camera = Camera(
                id=camera_id,
                company_id=company.id,
                establishment_id=site_id,
                name=item["name"],
                stream_url=stream,
                is_active=True,
            )
            session.add(camera)
            await session.flush()
        elif camera.stream_url == "rtsp://example.invalid/cam01":
            camera.name = item["name"]
            camera.stream_url = stream
        prompt_set = await session.get(PromptSet, set_id)
        if prompt_set is None:
            prompt_set = PromptSet(
                id=set_id,
                company_id=company.id,
                camera_id=camera_id,
                name=item["watchlist"],
            )
            session.add(prompt_set)
            await session.flush()
        elif prompt_set.name == "Default watchlist":
            prompt_set.name = item["watchlist"]
        for order, prompt_text in enumerate(item["prompts"]):
            prompt_id = (
                PROMPT_ID
                if index == 0 and order == 0
                else uuid.uuid5(set_id, str(order))
            )
            prompt = await session.get(Prompt, prompt_id)
            if prompt is None:
                session.add(
                    Prompt(
                        id=prompt_id,
                        company_id=company.id,
                        prompt_set_id=set_id,
                        text=prompt_text,
                        enabled=True,
                        sort_order=order,
                    )
                )
            elif prompt.text == "Is there an unauthorized person in a restricted area?":
                prompt.text = prompt_text
        await session.flush()
    # Preserve the stable fixture identifiers used by operators and API tests.
    ids.update(
        establishment_id=str(ESTABLISHMENT_DEMO_ID),
        camera_id=str(CAMERA_DEMO_ID),
        prompt_set_id=str(PROMPT_SET_ID),
        prompt_id=str(PROMPT_ID),
    )

    token = os.environ.get("DEMO_WEBHOOK_TOKEN") or DEMO_WEBHOOK_TOKEN
    webhook = await session.get(WebhookEndpoint, WEBHOOK_ID)
    if webhook is None:
        webhook = WebhookEndpoint(
            id=WEBHOOK_ID,
            company_id=company.id,
            establishment_id=ESTABLISHMENT_DEMO_ID,
            name="Contexto externo de demonstração",
            token_hash=hash_password(token),
            active=True,
        )
        session.add(webhook)
        await session.flush()
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
            if existing is not None:
                raise ValueError(
                    "Demo email is already owned by another user; no membership changed"
                )
            user = CompanyUser(
                id=user_id,
                company_id=company.id,
                email=email,
                role=role,
                password_hash=password_hash,
            )
            session.add(user)
            await session.flush()
        # Do not grant access to a reused fixture ID or alter an existing password.
        if user.email != email:
            raise ValueError("Demo user identity mismatch; no membership changed")
        targets = [company.id]
        if role == UserRole.MANAGER:
            targets.append(SANDBOX_COMPANY_ID)
        for target in targets:
            if await session.get(CompanyUserMembership, (user.id, target)) is None:
                session.add(CompanyUserMembership(user_id=user.id, company_id=target))
        ids[f"user_{role.value}"] = str(user.id)

    await session.commit()
    return ids


async def main() -> int:
    engine = create_async_engine(
        settings.database_url,
        pool_pre_ping=True,
        connect_args={"statement_cache_size": 0},
    )
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        ids = await seed_demo(session)
    await engine.dispose()
    print("Demo seed complete:", ids)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
