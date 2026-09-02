#!/usr/bin/env python3
"""Idempotent dev seed — root admin, sample tenant, market, context mode, lenses."""

from __future__ import annotations

import asyncio
import sys
import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from argus.config import settings  # noqa: E402
from argus.domain.enums import NotificationChannel, UserRole  # noqa: E402
from argus.domain.models import (  # noqa: E402
    Camera,
    ContextMode,
    ContextModeCameraAssignment,
    Lens,
    Market,
    NotificationConfig,
    RegionOfInterest,
    Rule,
    RuleRegionMapping,
    Tenant,
    TenantUser,
)
from argus.services.database import set_session_context  # noqa: E402
from argus.services.redis import set_key  # noqa: E402

# Stable IDs for local verification
SEED_TENANT_ID = uuid.UUID("11111111-1111-4111-8111-111111111111")
SEED_MARKET_ID = uuid.UUID("22222222-2222-4222-8222-222222222222")
SEED_CAMERA_ID = uuid.UUID("33333333-3333-4333-8333-333333333333")
SEED_REGION_ID = uuid.UUID("44444444-4444-4444-8444-444444444444")
SEED_MODE_ID = uuid.UUID("55555555-5555-4555-8555-555555555555")
SEED_LENS_ID = uuid.UUID("66666666-6666-4666-8666-666666666666")
SEED_RULE_ID = uuid.UUID("77777777-7777-4777-8777-777777777777")
SEED_ROOT_ADMIN_ID = uuid.UUID("88888888-8888-4888-8888-888888888888")
SEED_TENANT_ADMIN_ID = uuid.UUID("99999999-9999-4999-8999-999999999999")
SEED_WATCHER_ID = uuid.UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
SEED_NOTIF_ID = uuid.UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")

TENANT_SLUG = "demo-retail"


async def _get_or_create_tenant(session: AsyncSession) -> Tenant:
    existing = await session.scalar(select(Tenant).where(Tenant.slug == TENANT_SLUG))
    if existing:
        return existing
    tenant = Tenant(
        id=SEED_TENANT_ID,
        name="Demo Retail",
        slug=TENANT_SLUG,
    )
    session.add(tenant)
    await session.flush()
    return tenant


async def seed(session: AsyncSession) -> dict[str, str]:
    await set_session_context(session, tenant_id=None, role=UserRole.ROOT_ADMIN.value)

    tenant = await _get_or_create_tenant(session)

    market = await session.get(Market, SEED_MARKET_ID)
    if market is None:
        market = Market(
            id=SEED_MARKET_ID,
            tenant_id=tenant.id,
            name="Downtown Store",
            timezone="America/New_York",
        )
        session.add(market)

    camera = await session.get(Camera, SEED_CAMERA_ID)
    if camera is None:
        camera = Camera(
            id=SEED_CAMERA_ID,
            tenant_id=tenant.id,
            market_id=SEED_MARKET_ID,
            name="Entrance Cam",
            edge_device_id="edge-demo-001",
        )
        session.add(camera)

    region = await session.get(RegionOfInterest, SEED_REGION_ID)
    if region is None:
        region = RegionOfInterest(
            id=SEED_REGION_ID,
            tenant_id=tenant.id,
            camera_id=SEED_CAMERA_ID,
            name="Checkout Zone",
            polygon=[{"x": 0.1, "y": 0.1}, {"x": 0.9, "y": 0.1}, {"x": 0.9, "y": 0.9}],
        )
        session.add(region)

    mode = await session.get(ContextMode, SEED_MODE_ID)
    if mode is None:
        mode = ContextMode(
            id=SEED_MODE_ID,
            tenant_id=tenant.id,
            name="Business Hours",
            description="Default surveillance context for store hours",
            is_active=True,
        )
        session.add(mode)

    assignment = await session.scalar(
        select(ContextModeCameraAssignment).where(
            ContextModeCameraAssignment.camera_id == SEED_CAMERA_ID
        )
    )
    if assignment is None:
        session.add(
            ContextModeCameraAssignment(
                tenant_id=tenant.id,
                context_mode_id=SEED_MODE_ID,
                camera_id=SEED_CAMERA_ID,
            )
        )

    lens = await session.get(Lens, SEED_LENS_ID)
    if lens is None:
        lens = Lens(
            id=SEED_LENS_ID,
            tenant_id=tenant.id,
            context_mode_id=SEED_MODE_ID,
            name="Shelf Monitoring",
            system_prompt=(
                "Analyze the scene for suspicious activity near shelves. "
                "NEVER identify individuals or infer biometric attributes."
            ),
            output_schema={
                "type": "object",
                "properties": {
                    "suspicious": {"type": "boolean"},
                    "description": {"type": "string"},
                },
                "required": ["suspicious", "description"],
            },
        )
        session.add(lens)

    rule = await session.get(Rule, SEED_RULE_ID)
    if rule is None:
        rule = Rule(
            id=SEED_RULE_ID,
            tenant_id=tenant.id,
            context_mode_id=SEED_MODE_ID,
            name="Shelf Tamper",
            condition={"field": "suspicious", "op": "eq", "value": True},
            severity_weight=3,
        )
        session.add(rule)
        await session.flush()
        session.add(
            RuleRegionMapping(
                tenant_id=tenant.id,
                rule_id=SEED_RULE_ID,
                region_id=SEED_REGION_ID,
            )
        )

    root_admin = await session.scalar(
        select(TenantUser).where(
            TenantUser.idp_subject == "auth0|seed-root-admin",
            TenantUser.role == UserRole.ROOT_ADMIN,
        )
    )
    if root_admin is None:
        session.add(
            TenantUser(
                id=SEED_ROOT_ADMIN_ID,
                tenant_id=None,
                idp_subject="auth0|seed-root-admin",
                email="root@argus.local",
                role=UserRole.ROOT_ADMIN,
            )
        )

    tenant_admin = await session.scalar(
        select(TenantUser).where(
            TenantUser.idp_subject == "auth0|seed-tenant-admin",
            TenantUser.tenant_id == tenant.id,
        )
    )
    if tenant_admin is None:
        session.add(
            TenantUser(
                id=SEED_TENANT_ADMIN_ID,
                tenant_id=tenant.id,
                idp_subject="auth0|seed-tenant-admin",
                email="admin@demo-retail.local",
                role=UserRole.TENANT_ADMIN,
            )
        )

    watcher = await session.scalar(
        select(TenantUser).where(
            TenantUser.idp_subject == "auth0|seed-watcher",
            TenantUser.tenant_id == tenant.id,
        )
    )
    if watcher is None:
        session.add(
            TenantUser(
                id=SEED_WATCHER_ID,
                tenant_id=tenant.id,
                idp_subject="auth0|seed-watcher",
                email="watcher@demo-retail.local",
                role=UserRole.WATCHER,
            )
        )

    notif = await session.get(NotificationConfig, SEED_NOTIF_ID)
    if notif is None:
        session.add(
            NotificationConfig(
                id=SEED_NOTIF_ID,
                tenant_id=tenant.id,
                channel=NotificationChannel.SMS,
                recipient="+15551234567",
            )
        )

    await session.commit()
    await set_key(f"camera:active_mode:{SEED_CAMERA_ID}", str(SEED_MODE_ID), ex=86400)
    return {
        "tenant_id": str(tenant.id),
        "market_id": str(SEED_MARKET_ID),
        "camera_id": str(SEED_CAMERA_ID),
        "context_mode_id": str(SEED_MODE_ID),
        "lens_id": str(SEED_LENS_ID),
        "root_admin_subject": "auth0|seed-root-admin",
    }


async def main() -> int:
    engine = create_async_engine(settings.admin_database_url, pool_pre_ping=True)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        ids = await seed(session)
    await engine.dispose()
    for key, value in ids.items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
