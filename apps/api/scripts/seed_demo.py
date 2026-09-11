#!/usr/bin/env python3
"""Idempotent demo seed — sample data under demo-retail + guest/manager only.

Platform ROOT/ADMIN are created by bootstrap / seed_platform, never here.
"""

from __future__ import annotations

import asyncio
import os
import sys
import uuid
from datetime import time as dt_time
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from argus.config import settings  # noqa: E402
from argus.core.passwords import hash_password  # noqa: E402
from argus.domain.enums import NotificationChannel, UserRole  # noqa: E402
from argus.domain.models import (  # noqa: E402
    Agent,
    AgentLocation,
    Camera,
    Company,
    CompanyUser,
    RuleSetCameraAssignment,
    Location,
    NotificationConfig,
    Recipe,
    RegionOfInterest,
    Rule,
    RuleRegionMapping,
    RuleSet,
    RuleSetSchedule,
)
from argus.services.database import set_session_context  # noqa: E402
from argus.services.redis import set_key  # noqa: E402

# Stable IDs (demo-retail reuses former downtown fixture UUID for test compatibility)
COMPANY_DEMO_ID = uuid.UUID("11111111-1111-4111-8111-111111111111")
LOCATION_DEMO_ID = uuid.UUID("22222222-2222-4222-8222-222222222222")
CAMERA_DEMO_ID = uuid.UUID("33333333-3333-4333-8333-333333333333")
REGION_ID = uuid.UUID("44444444-4444-4444-8444-444444444444")
RULE_SET_ID = uuid.UUID("55555555-5555-4555-8555-555555555555")
RECIPE_ID = uuid.UUID("66666666-6666-4666-8666-666666666666")
RULE_ID = uuid.UUID("77777777-7777-4777-8777-777777777777")
AGENT_DEMO_ID = uuid.UUID("35353535-3535-4353-8535-353535353535")
USER_MANAGER_ID = uuid.UUID("99999999-9999-4999-8999-999999999999")
USER_GUEST_ID = uuid.UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
NOTIF_ID = uuid.UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")

DEFAULT_PASSWORD = "Password123!"

SKETCH_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 300">'
    '<rect width="400" height="300" fill="#1a2332"/>'
    '<rect x="40" y="40" width="320" height="220" fill="none" stroke="#4a90d9" stroke-width="2"/>'
    '<text x="200" y="30" fill="#8ab4f8" font-size="14" text-anchor="middle">Entrance</text>'
    '<rect x="60" y="60" width="120" height="80" fill="#243447" stroke="#5f7a99"/>'
    '<text x="120" y="105" fill="#c8d6e5" font-size="12" text-anchor="middle">Shelves</text>'
    '<rect x="220" y="60" width="120" height="80" fill="#243447" stroke="#5f7a99"/>'
    '<text x="280" y="105" fill="#c8d6e5" font-size="12" text-anchor="middle">Checkout</text>'
    '<rect x="60" y="170" width="280" height="70" fill="#243447" stroke="#5f7a99"/>'
    '<text x="200" y="210" fill="#c8d6e5" font-size="12" text-anchor="middle">Aisle</text>'
    "</svg>"
)


def demo_password() -> str:
    return os.environ.get("DEMO_PASSWORD") or DEFAULT_PASSWORD


async def seed_demo(session: AsyncSession) -> dict[str, str]:
    await set_session_context(session, company_id=None, role=UserRole.ROOT.value)
    ids: dict[str, str] = {}
    password = demo_password()

    company = await session.scalar(select(Company).where(Company.slug == "demo-retail"))
    if company is None:
        company = Company(id=COMPANY_DEMO_ID, name="Demo Retail", slug="demo-retail")
        session.add(company)
        await session.flush()
    ids["company_id:demo-retail"] = str(company.id)

    location = await session.get(Location, LOCATION_DEMO_ID)
    if location is None:
        location = Location(
            id=LOCATION_DEMO_ID,
            company_id=COMPANY_DEMO_ID,
            name="Demo Store",
            address="100 Demo Street",
            sketch=SKETCH_SVG,
            timezone="America/New_York",
        )
        session.add(location)
        await session.flush()
    ids["location_id:demo"] = str(location.id)

    agent = await session.get(Agent, AGENT_DEMO_ID)
    if agent is None:
        agent = Agent(
            id=AGENT_DEMO_ID,
            company_id=COMPANY_DEMO_ID,
            device_id="agent-demo-001",
            name="Demo Agent",
        )
        session.add(agent)
        await session.flush()
    existing_link = await session.scalar(
        select(AgentLocation).where(
            AgentLocation.agent_id == AGENT_DEMO_ID,
            AgentLocation.location_id == LOCATION_DEMO_ID,
        )
    )
    if existing_link is None:
        session.add(
            AgentLocation(
                company_id=COMPANY_DEMO_ID,
                agent_id=AGENT_DEMO_ID,
                location_id=LOCATION_DEMO_ID,
            )
        )
    ids["agent_id:agent-demo-001"] = str(agent.id)

    camera = await session.get(Camera, CAMERA_DEMO_ID)
    if camera is None:
        camera = Camera(
            id=CAMERA_DEMO_ID,
            company_id=COMPANY_DEMO_ID,
            location_id=LOCATION_DEMO_ID,
            name="Entrance Cam",
            stream_url="rtsp://edge-demo.local:8554/entrance",
            placement_x=0.25,
            placement_y=0.2,
        )
        session.add(camera)
    ids["camera_id:Entrance Cam"] = str(CAMERA_DEMO_ID)

    region = await session.get(RegionOfInterest, REGION_ID)
    if region is None:
        session.add(
            RegionOfInterest(
                id=REGION_ID,
                company_id=COMPANY_DEMO_ID,
                camera_id=CAMERA_DEMO_ID,
                name="Checkout Zone",
                polygon=[{"x": 0.1, "y": 0.1}, {"x": 0.9, "y": 0.1}, {"x": 0.9, "y": 0.9}],
            )
        )

    rule_set = await session.get(RuleSet, RULE_SET_ID)
    if rule_set is None:
        session.add(
            RuleSet(
                id=RULE_SET_ID,
                company_id=COMPANY_DEMO_ID,
                name="Business Hours",
                description="Default surveillance rule set for store hours",
                is_active=True,
            )
        )
        await session.flush()
        for day, start, end in (
            ("mon", dt_time(8, 0), dt_time(20, 0)),
            ("tue", dt_time(8, 0), dt_time(20, 0)),
            ("sat", dt_time(9, 0), dt_time(18, 0)),
        ):
            session.add(
                RuleSetSchedule(
                    company_id=COMPANY_DEMO_ID,
                    rule_set_id=RULE_SET_ID,
                    day_of_week=day,
                    start_time=start,
                    end_time=end,
                    location_id=LOCATION_DEMO_ID,
                )
            )

    assignment = await session.scalar(
        select(RuleSetCameraAssignment).where(RuleSetCameraAssignment.camera_id == CAMERA_DEMO_ID)
    )
    if assignment is None:
        session.add(
            RuleSetCameraAssignment(
                company_id=COMPANY_DEMO_ID,
                rule_set_id=RULE_SET_ID,
                camera_id=CAMERA_DEMO_ID,
            )
        )

    recipe = await session.get(Recipe, RECIPE_ID)
    if recipe is None:
        session.add(
            Recipe(
                id=RECIPE_ID,
                company_id=COMPANY_DEMO_ID,
                rule_set_id=RULE_SET_ID,
                name="Shelf Monitoring",
                system_prompt=(
                    "Analyze the scene for suspicious activity near shelves. "
                    "Report detections with a detection_class and a confidence between 0 and 1. "
                    "NEVER identify individuals or infer biometric attributes."
                ),
                output_schema={
                    "type": "object",
                    "properties": {
                        "is_suspicious": {"type": "boolean"},
                        "detection_class": {
                            "type": "string",
                            "enum": ["loitering", "shelf_tamper", "break_in", "none"],
                        },
                        "confidence_score": {"type": "number", "minimum": 0, "maximum": 1},
                        "description": {"type": "string"},
                    },
                    "required": [
                        "is_suspicious",
                        "detection_class",
                        "confidence_score",
                        "description",
                    ],
                },
            )
        )

    rule = await session.get(Rule, RULE_ID)
    if rule is None:
        session.add(
            Rule(
                id=RULE_ID,
                company_id=COMPANY_DEMO_ID,
                rule_set_id=RULE_SET_ID,
                name="Shelf Tamper",
                detection_class="shelf_tamper",
                confidence_threshold=0.600,
                condition={"field": "suspicious", "op": "eq", "value": True},
                severity_weight=3,
            )
        )
        await session.flush()
        session.add(
            RuleRegionMapping(
                company_id=COMPANY_DEMO_ID,
                rule_id=RULE_ID,
                region_id=REGION_ID,
            )
        )

    for spec in (
        {
            "id": USER_MANAGER_ID,
            "email": "manager@demo.argus.local",
            "role": UserRole.MANAGER,
        },
        {
            "id": USER_GUEST_ID,
            "email": "guest@demo.argus.local",
            "role": UserRole.OPERATOR,
        },
    ):
        user = await session.scalar(select(CompanyUser).where(CompanyUser.email == spec["email"]))
        if user is None:
            session.add(
                CompanyUser(
                    id=spec["id"],
                    company_id=COMPANY_DEMO_ID,
                    email=spec["email"],
                    password_hash=hash_password(password),
                    role=spec["role"],
                )
            )

    notif = await session.get(NotificationConfig, NOTIF_ID)
    if notif is None:
        session.add(
            NotificationConfig(
                id=NOTIF_ID,
                company_id=COMPANY_DEMO_ID,
                channel=NotificationChannel.SMS,
                recipient="+15551234567",
            )
        )

    await session.commit()
    await set_key(f"camera:active_mode:{CAMERA_DEMO_ID}", str(RULE_SET_ID), ex=86400)
    ids["demo_password_set"] = "1"
    return ids


async def main() -> int:
    engine = create_async_engine(settings.admin_database_url, pool_pre_ping=True)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        ids = await seed_demo(session)
    await engine.dispose()
    for key, value in ids.items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
