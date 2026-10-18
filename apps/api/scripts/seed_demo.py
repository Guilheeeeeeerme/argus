#!/usr/bin/env python3
"""Idempotent public-camera demo; preserve operator edits by default.

Platform ROOT/ADMIN are created by bootstrap / seed_platform, never here.

Shape: one account, two estabelecimentos, three cameras each, Portuguese copy.

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

from sqlalchemy import delete, select
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
    LEGACY_CAMERA_NAMES,
    LEGACY_PLAYLISTS,
    LEGACY_PROMPT_TEXTS,
    LEGACY_WATCHLIST_NAMES,
    SOURCE_PAGE,
    SOURCE_TERMS,
    SOURCES,
    UNITS,
)

ACCOUNT_DEMO_ID = uuid.UUID("11111111-1111-4111-8111-111111111111")
UNIT_DEMO_ID = uuid.UUID("22222222-2222-4222-8222-222222222222")
CAMERA_DEMO_ID = uuid.UUID("33333333-3333-4333-8333-333333333333")
PROMPT_SET_ID = uuid.UUID("55555555-5555-4555-8555-555555555555")
PROMPT_ID = uuid.UUID("77777777-7777-4777-8777-777777777777")
USER_MANAGER_ID = uuid.UUID("99999999-9999-4999-8999-999999999999")
USER_GUEST_ID = uuid.UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
WEBHOOK_ID = uuid.UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")

# Legacy sandbox from the previous 2-account demo — removed on seed.
SANDBOX_ACCOUNT_ID = uuid.uuid5(ACCOUNT_DEMO_ID, "sandbox-company")

DEFAULT_PASSWORD = "Password123!"
DEMO_WEBHOOK_TOKEN = "demo-webhook-token-change-me"

KEEP_UNIT_KEYS = {unit["key"] for unit in UNITS}


def demo_password() -> str:
    configured = os.environ.get("DEMO_PASSWORD")
    if configured:
        return configured
    if urlsplit(settings.database_url).hostname not in {"localhost", "127.0.0.1", "::1", "postgres"}:
        raise ValueError("DEMO_PASSWORD must be configured for a remote demo database")
    return DEFAULT_PASSWORD


def demo_password_sync_enabled() -> bool:
    return os.environ.get("DEMO_PASSWORD_SYNC", "").strip().lower() in {"1", "true", "yes"}


def _unit_id(unit_key: str) -> uuid.UUID:
    if unit_key == UNITS[0]["key"]:
        return UNIT_DEMO_ID
    # Preserve the existing Florida Keys site UUID from the prior one-cam-per-site seed.
    if unit_key == UNITS[1]["key"]:
        return uuid.uuid5(ACCOUNT_DEMO_ID, "key-west-beach:site")
    return uuid.uuid5(ACCOUNT_DEMO_ID, unit_key + ":unit")


def _camera_id(unit_key: str, camera_key: str, camera_index: int) -> uuid.UUID:
    if unit_key == UNITS[0]["key"] and camera_index == 0:
        return CAMERA_DEMO_ID
    return uuid.uuid5(ACCOUNT_DEMO_ID, camera_key + ":camera")


def _prompt_set_id(unit_key: str, camera_key: str, camera_index: int) -> uuid.UUID:
    if unit_key == UNITS[0]["key"] and camera_index == 0:
        return PROMPT_SET_ID
    return uuid.uuid5(ACCOUNT_DEMO_ID, camera_key + ":prompts")


def _prompt_id(set_id: uuid.UUID, unit_key: str, camera_index: int, order: int) -> uuid.UUID:
    if unit_key == UNITS[0]["key"] and camera_index == 0 and order == 0:
        return PROMPT_ID
    return uuid.uuid5(set_id, str(order))


async def _purge_extras(session: AsyncSession, account_id: uuid.UUID) -> None:
    """Drop sandbox + any cameras/units outside the consolidated catalog."""
    keep_unit_ids = {_unit_id(key) for key in KEEP_UNIT_KEYS}
    keep_camera_ids = {
        _camera_id(unit["key"], camera["key"], index)
        for unit in UNITS
        for index, camera in enumerate(unit["cameras"])
    }

    sandbox = await session.get(Account, SANDBOX_ACCOUNT_ID)
    if sandbox is not None:
        await session.delete(sandbox)
        await session.flush()

    extra_cameras = (
        await session.scalars(
            select(Camera).where(
                Camera.account_id == account_id,
                Camera.id.notin_(keep_camera_ids),
            )
        )
    ).all()
    # Delete PromptSets first — ORM nulls camera_id on relationship detach, which
    # violates NOT NULL before the DB CASCADE can run.
    extra_camera_ids = [camera.id for camera in extra_cameras]
    if extra_camera_ids:
        extra_sets = (
            await session.scalars(
                select(PromptSet).where(PromptSet.camera_id.in_(extra_camera_ids))
            )
        ).all()
        for prompt_set in extra_sets:
            await session.delete(prompt_set)
        await session.flush()
    for camera in extra_cameras:
        await session.delete(camera)
    await session.flush()

    extra_units = (
        await session.scalars(
            select(Unit).where(
                Unit.account_id == account_id,
                Unit.id.notin_(keep_unit_ids),
            )
        )
    ).all()
    for unit in extra_units:
        await session.delete(unit)
    await session.flush()


async def seed_demo(session: AsyncSession) -> dict[str, str]:
    await set_session_context(session, account_id=None, role=UserRole.ROOT.value)
    ids: dict[str, str] = {}

    account = await session.get(Account, ACCOUNT_DEMO_ID)
    if account is None:
        account = Account(
            id=ACCOUNT_DEMO_ID,
            name="Argus Demo Brasil",
            slug="demo-company",
        )
        session.add(account)
        await session.flush()
    if account.name in {"Demo Company", "Argus Public Camera Demo"}:
        account.name = "Argus Demo Brasil"
    account.settings = {
        **(account.settings or {}),
        "demo_source": "Operação municipal demo · vias e orla (feeds públicos)",
        "demo_source_url": SOURCE_PAGE,
        "demo_source_terms": SOURCE_TERMS,
        "demo_sources": [
            {"name": s["name"], "page": s["page"], "terms": s["terms"]} for s in SOURCES
        ],
        "demo_shape": "1 conta · 2 estabelecimentos · 3 câmeras cada",
        "demo_narrative": "Monitoramento municipal — Distrito Vias + Distrito Orla",
    }
    ids["account_id"] = str(account.id)

    await _purge_extras(session, account.id)

    for unit_item in UNITS:
        unit_id = _unit_id(unit_item["key"])
        unit = await session.get(Unit, unit_id)
        if unit is None:
            unit = Unit(
                id=unit_id,
                account_id=account.id,
                name=unit_item["name"],
                address=unit_item["address"],
                timezone=unit_item["timezone"],
                active=True,
            )
            session.add(unit)
            await session.flush()
        else:
            # Consolidated demo units always converge to the Portuguese catalog labels.
            unit.name = unit_item["name"]
            unit.address = unit_item["address"]
            unit.timezone = unit_item["timezone"]
            unit.active = True

        for camera_index, camera_item in enumerate(unit_item["cameras"]):
            camera_id = _camera_id(unit_item["key"], camera_item["key"], camera_index)
            set_id = _prompt_set_id(unit_item["key"], camera_item["key"], camera_index)
            stream = "ffmpeg:" + camera_item["playlist"] + "#video=copy"
            playlist = camera_item["playlist"]

            camera = await session.get(Camera, camera_id)
            if camera is None:
                camera = Camera(
                    id=camera_id,
                    account_id=account.id,
                    unit_id=unit_id,
                    name=camera_item["name"],
                    stream_url=stream,
                    is_active=True,
                )
                session.add(camera)
                await session.flush()
            else:
                camera.unit_id = unit_id
                current_playlist = (camera.stream_url or "").removeprefix("ffmpeg:").split("#", 1)[0]
                if camera.stream_url in {
                    None,
                    "",
                    "rtsp://example.invalid/cam01",
                } or camera.stream_url.startswith(
                    (
                        "ffmpeg:https://wzmedia.dot.ca.gov/",
                        "ffmpeg:https://5ed325193d4e1.streamlock.net",
                        "ffmpeg:https://zssd-",
                        "ffmpeg:https://streaming-au.coastalcoms.com/",
                    )
                ) or current_playlist in LEGACY_PLAYLISTS or current_playlist == playlist:
                    # Refresh known public demo feeds; leave unknown operator URLs alone.
                    camera.stream_url = stream
                if camera.name in LEGACY_CAMERA_NAMES:
                    camera.name = camera_item["name"]
                camera.is_active = True

            prompt_set = await session.get(PromptSet, set_id)
            if prompt_set is None:
                prompt_set = PromptSet(
                    id=set_id,
                    account_id=account.id,
                    camera_id=camera_id,
                    name=camera_item["watchlist"],
                )
                session.add(prompt_set)
                await session.flush()
            else:
                prompt_set.camera_id = camera_id
                if prompt_set.name in LEGACY_WATCHLIST_NAMES:
                    prompt_set.name = camera_item["watchlist"]

            for order, prompt_text in enumerate(camera_item["prompts"]):
                prompt_id = _prompt_id(set_id, unit_item["key"], camera_index, order)
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
                    prompt.enabled = True
            await session.flush()

    ids.update(
        unit_id=str(UNIT_DEMO_ID),
        unit_costa_id=str(_unit_id(UNITS[1]["key"])),
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
            name="Contexto de entrada (demo)",
            token_hash=hash_password(token),
            active=True,
        )
        session.add(webhook)
        await session.flush()
    else:
        webhook.unit_id = UNIT_DEMO_ID
        if webhook.name in {"Demo inbound context"}:
            webhook.name = "Contexto de entrada (demo)"
    ids["webhook_id"] = str(WEBHOOK_ID)

    password_hash = hash_password(demo_password())
    for user_id, email, role, _name in (
        (USER_MANAGER_ID, "manager@demo.local", UserRole.MANAGER, "Gestor Demo"),
        (USER_GUEST_ID, "guest@demo.local", UserRole.OPERATOR, "Operador Demo"),
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
        if demo_password_sync_enabled():
            user.password_hash = password_hash
        if await session.get(AccountUserMembership, (user.id, account.id)) is None:
            session.add(AccountUserMembership(user_id=user.id, account_id=account.id))
        # Drop stale sandbox membership if still present after account delete race.
        await session.execute(
            delete(AccountUserMembership).where(
                AccountUserMembership.user_id == user.id,
                AccountUserMembership.account_id == SANDBOX_ACCOUNT_ID,
            )
        )
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
