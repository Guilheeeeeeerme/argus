#!/usr/bin/env python3
"""Idempotent public-camera demo; preserve operator edits by default.

Platform ROOT/ADMIN are created by bootstrap / seed_platform, never here.

Passwords for the fixture demo users stay untouched unless DEMO_PASSWORD_SYNC=1
(with DEMO_PASSWORD set) — then manager@ / guest@ hashes are rotated to match.
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
    Account,
    AccountUser,
    AccountUserMembership,
    Unit,
    Prompt,
    PromptSet,
    WebhookEndpoint,
)
from argus.services.database import set_session_context
from demo_catalog import (
    CAMERAS,
    LEGACY_PROMPT_TEXTS,
    LEGACY_WATCHLIST_NAMES,
    SOURCE_PAGE,
    SOURCE_TERMS,
    SOURCES,
)

ACCOUNT_DEMO_ID = uuid.UUID("11111111-1111-4111-8111-111111111111")
UNIT_DEMO_ID = uuid.UUID("22222222-2222-4222-8222-222222222222")
CAMERA_DEMO_ID = uuid.UUID("33333333-3333-4333-8333-333333333333")
PROMPT_SET_ID = uuid.UUID("55555555-5555-4555-8555-555555555555")
PROMPT_ID = uuid.UUID("77777777-7777-4777-8777-777777777777")
USER_MANAGER_ID = uuid.UUID("99999999-9999-4999-8999-999999999999")
USER_GUEST_ID = uuid.UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
WEBHOOK_ID = uuid.UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")

SANDBOX_ACCOUNT_ID = uuid.uuid5(ACCOUNT_DEMO_ID, "sandbox-company")

DEFAULT_PASSWORD = "Password123!"
DEMO_WEBHOOK_TOKEN = "demo-webhook-token-change-me"


def demo_password() -> str:
    configured = os.environ.get("DEMO_PASSWORD")
    if configured:
        return configured
    if urlsplit(settings.database_url).hostname not in {"localhost", "127.0.0.1", "::1", "postgres"}:
        raise ValueError("DEMO_PASSWORD must be configured for a remote demo database")
    return DEFAULT_PASSWORD


def demo_password_sync_enabled() -> bool:
    return os.environ.get("DEMO_PASSWORD_SYNC", "").strip().lower() in {"1", "true", "yes"}


async def seed_demo(session: AsyncSession) -> dict[str, str]:
    await set_session_context(session, account_id=None, role=UserRole.ROOT.value)
    ids: dict[str, str] = {}

    account = await session.get(Account, ACCOUNT_DEMO_ID)
    if account is None:
        account = Account(
            id=ACCOUNT_DEMO_ID,
            name="Demo Company",
            slug="demo-company",
        )
        session.add(account)
        await session.flush()
    ids["account_id"] = str(account.id)

    if account.name == "Demo Company":
        account.name = "Argus Public Camera Demo"
    account.settings = {
        **(account.settings or {}),
        "demo_source": "Public live cameras (traffic, beach, zoo)",
        "demo_source_url": SOURCE_PAGE,
        "demo_source_terms": SOURCE_TERMS,
        "demo_sources": [
            {"name": s["name"], "page": s["page"], "terms": s["terms"]} for s in SOURCES
        ],
    }
    sandbox = await session.get(Account, SANDBOX_ACCOUNT_ID)
    if sandbox is None:
        session.add(
            Account(id=SANDBOX_ACCOUNT_ID, name="Demo Sandbox", slug="demo-sandbox")
        )
        await session.flush()
    ids["sandbox_account_id"] = str(SANDBOX_ACCOUNT_ID)

    for index, item in enumerate(CAMERAS):
        site_id = (
            UNIT_DEMO_ID
            if index == 0
            else uuid.uuid5(ACCOUNT_DEMO_ID, item["key"] + ":site")
        )
        camera_id = (
            CAMERA_DEMO_ID
            if index == 0
            else uuid.uuid5(ACCOUNT_DEMO_ID, item["key"] + ":camera")
        )
        set_id = (
            PROMPT_SET_ID
            if index == 0
            else uuid.uuid5(ACCOUNT_DEMO_ID, item["key"] + ":prompts")
        )
        address = item.get("address", "US-101, San Luis Obispo, California")
        timezone = item.get("timezone", "America/Los_Angeles")
        unit = await session.get(Unit, site_id)
        if unit is None:
            unit = Unit(
                id=site_id,
                account_id=account.id,
                name=item["site"],
                address=address,
                timezone=timezone,
                active=True,
            )
            session.add(unit)
            await session.flush()
        elif unit.name == "Demo Establishment":
            unit.name = item["site"]
            unit.address = address
            unit.timezone = timezone
        elif unit.address == "US-101, San Luis Obispo, California" and address != unit.address:
            unit.address = address
            unit.timezone = timezone
        camera = await session.get(Camera, camera_id)
        stream = "ffmpeg:" + item["playlist"] + "#video=copy"
        if camera is None:
            camera = Camera(
                id=camera_id,
                account_id=account.id,
                unit_id=site_id,
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
                account_id=account.id,
                camera_id=camera_id,
                name=item["watchlist"],
            )
            session.add(prompt_set)
            await session.flush()
        elif prompt_set.name in LEGACY_WATCHLIST_NAMES:
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
                        account_id=account.id,
                        prompt_set_id=set_id,
                        text=prompt_text,
                        enabled=True,
                        sort_order=order,
                    )
                )
            elif prompt.text in LEGACY_PROMPT_TEXTS:
                prompt.text = prompt_text
        await session.flush()
    # Preserve the stable fixture identifiers used by operators and API tests.
    ids.update(
        unit_id=str(UNIT_DEMO_ID),
        camera_id=str(CAMERA_DEMO_ID),
        prompt_set_id=str(PROMPT_SET_ID),
        prompt_id=str(PROMPT_ID),
    )

    token = os.environ.get("DEMO_WEBHOOK_TOKEN") or DEMO_WEBHOOK_TOKEN
    webhook = await session.get(WebhookEndpoint, WEBHOOK_ID)
    if webhook is None:
        webhook = WebhookEndpoint(
            id=WEBHOOK_ID,
            account_id=account.id,
            unit_id=UNIT_DEMO_ID,
            name="Demo inbound context",
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
        user = await session.get(AccountUser, user_id)
        if user is None:
            existing = await session.scalar(
                select(AccountUser).where(AccountUser.email == email)
            )
            if existing is not None:
                raise ValueError(
                    "Demo email is already owned by another user; no membership changed"
                )
            user = AccountUser(
                id=user_id,
                account_id=account.id,
                email=email,
                role=role,
                password_hash=password_hash,
            )
            session.add(user)
            await session.flush()
        if user.email != email:
            raise ValueError("Demo user identity mismatch; no membership changed")
        # Default: preserve operator-changed passwords. Opt-in sync for panel recovery.
        if demo_password_sync_enabled():
            user.password_hash = password_hash
        targets = [account.id]
        if role == UserRole.MANAGER:
            targets.append(SANDBOX_ACCOUNT_ID)
        for target in targets:
            if await session.get(AccountUserMembership, (user.id, target)) is None:
                session.add(AccountUserMembership(user_id=user.id, account_id=target))
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
