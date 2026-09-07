#!/usr/bin/env python3
"""Idempotent dev seed — platform users, two companies, locations with sketches,
agents (N:N), cameras with stream config + placements, rule sets with shifts,
recipes, rules, notification config."""

from __future__ import annotations

import asyncio
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

# Stable IDs for local verification
COMPANY_DOWNTOWN_ID = uuid.UUID("11111111-1111-4111-8111-111111111111")
COMPANY_AIRPORT_ID = uuid.UUID("12121212-1212-4212-8212-121212121212")
LOCATION_DOWNTOWN_ID = uuid.UUID("22222222-2222-4222-8222-222222222222")
LOCATION_AIRPORT_ID = uuid.UUID("23232323-2323-4323-8323-232323232323")
CAMERA_DOWNTOWN_ID = uuid.UUID("33333333-3333-4333-8333-333333333333")
CAMERA_AIRPORT_ID = uuid.UUID("34343434-3434-4343-8434-343434343434")
REGION_ID = uuid.UUID("44444444-4444-4444-8444-444444444444")
RULE_SET_ID = uuid.UUID("55555555-5555-4555-8555-555555555555")
RECIPE_ID = uuid.UUID("66666666-6666-4666-8666-666666666666")
RULE_ID = uuid.UUID("77777777-7777-4777-8777-777777777777")
AGENT_ALPHA_ID = uuid.UUID("35353535-3535-4353-8535-353535353535")
AGENT_BETA_ID = uuid.UUID("36363636-3636-4363-8636-363636363636")
USER_ROOT_ID = uuid.UUID("88888888-8888-4888-8888-888888888888")
USER_ADMIN_ID = uuid.UUID("8a8a8a8a-8a8a-4a8a-8a8a-8a8a8a8a8a8a")
USER_MANAGER_1_ID = uuid.UUID("99999999-9999-4999-8999-999999999999")
USER_OPERATOR_1_ID = uuid.UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
USER_MANAGER_2_ID = uuid.UUID("cccccccc-cccc-4ccc-8ccc-cccccccccccc")
USER_OPERATOR_2_ID = uuid.UUID("dddddddd-dddd-4ddd-8ddd-dddddddddddd")
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

COMPANIES = [
    {"id": COMPANY_DOWNTOWN_ID, "slug": "downtown-retail", "name": "Downtown Retail"},
    {"id": COMPANY_AIRPORT_ID, "slug": "airport-retail", "name": "Airport Retail"},
]

USERS = [
    {"id": USER_ROOT_ID, "company": None, "email": "root@argus.local", "role": UserRole.ROOT},
    {"id": USER_ADMIN_ID, "company": None, "email": "admin@argus.local", "role": UserRole.ADMIN},
    {"id": USER_MANAGER_1_ID, "company": COMPANY_DOWNTOWN_ID, "email": "manager.downtown@argus.local", "role": UserRole.MANAGER},
    {"id": USER_OPERATOR_1_ID, "company": COMPANY_DOWNTOWN_ID, "email": "operator.downtown@argus.local", "role": UserRole.OPERATOR},
    {"id": USER_MANAGER_2_ID, "company": COMPANY_AIRPORT_ID, "email": "manager.airport@argus.local", "role": UserRole.MANAGER},
    {"id": USER_OPERATOR_2_ID, "company": COMPANY_AIRPORT_ID, "email": "operator.airport@argus.local", "role": UserRole.OPERATOR},
]

# Agent ↔ Location N:N: alpha covers both, beta only airport
AGENTS = [
    {"id": AGENT_ALPHA_ID, "company": COMPANY_DOWNTOWN_ID, "device_id": "agent-alpha-001", "name": "Agent Alpha", "locations": [LOCATION_DOWNTOWN_ID, LOCATION_AIRPORT_ID]},
    {"id": AGENT_BETA_ID, "company": COMPANY_AIRPORT_ID, "device_id": "agent-beta-001", "name": "Agent Beta", "locations": [LOCATION_AIRPORT_ID]},
]

LOCATIONS = [
    {"id": LOCATION_DOWNTOWN_ID, "company": COMPANY_DOWNTOWN_ID, "name": "Downtown Store", "address": "Main Street, 100 — Downtown", "timezone": "America/New_York"},
    {"id": LOCATION_AIRPORT_ID, "company": COMPANY_AIRPORT_ID, "name": "Airport Store", "address": "Terminal 2, Gate B — Airport", "timezone": "America/New_York"},
]

CAMERAS = [
    {"id": CAMERA_DOWNTOWN_ID, "company": COMPANY_DOWNTOWN_ID, "location": LOCATION_DOWNTOWN_ID, "name": "Entrance Cam", "stream_url": "rtsp://edge-alpha.local:8554/entrance", "placement_x": 0.25, "placement_y": 0.2},
    {"id": CAMERA_AIRPORT_ID, "company": COMPANY_AIRPORT_ID, "location": LOCATION_AIRPORT_ID, "name": "Gate Cam", "stream_url": "rtsp://edge-beta.local:8554/gate", "placement_x": 0.7, "placement_y": 0.35},
]


async def seed(session: AsyncSession) -> dict[str, str]:
    await set_session_context(session, company_id=None, role=UserRole.ROOT.value)
    ids: dict[str, str] = {}

    for spec in COMPANIES:
        company = await session.scalar(select(Company).where(Company.slug == spec["slug"]))
        if company is None:
            company = Company(id=spec["id"], name=spec["name"], slug=spec["slug"])
            session.add(company)
            await session.flush()
        ids[f"company_id:{spec['slug']}"] = str(company.id)

    locations_by_id: dict[uuid.UUID, Location] = {}
    for spec in LOCATIONS:
        location = await session.get(Location, spec["id"])
        if location is None:
            location = Location(
                id=spec["id"],
                company_id=spec["company"],
                name=spec["name"],
                address=spec["address"],
                sketch=SKETCH_SVG,
                timezone=spec["timezone"],
            )
            session.add(location)
            await session.flush()
        locations_by_id[spec["id"]] = location
        ids[f"location_id:{spec['id']}"] = str(location.id)

    # Agents + N:N with locations
    for spec in AGENTS:
        agent = await session.get(Agent, spec["id"])
        if agent is None:
            agent = Agent(id=spec["id"], company_id=spec["company"], device_id=spec["device_id"], name=spec["name"])
            session.add(agent)
            await session.flush()
        for location_id in spec["locations"]:
            existing = await session.scalar(
                select(AgentLocation).where(
                    AgentLocation.agent_id == spec["id"],
                    AgentLocation.location_id == location_id,
                )
            )
            if existing is None:
                session.add(AgentLocation(company_id=spec["company"], agent_id=spec["id"], location_id=location_id))
        ids[f"agent_id:{spec['device_id']}"] = str(agent.id)

    # Cameras with stream config + sketch placements
    for spec in CAMERAS:
        camera = await session.get(Camera, spec["id"])
        if camera is None:
            camera = Camera(
                id=spec["id"],
                company_id=spec["company"],
                location_id=spec["location"],
                name=spec["name"],
                stream_url=spec["stream_url"],
                placement_x=spec["placement_x"],
                placement_y=spec["placement_y"],
            )
            session.add(camera)
        ids[f"camera_id:{spec['name']}"] = str(spec["id"])

    region = await session.get(RegionOfInterest, REGION_ID)
    if region is None:
        region = RegionOfInterest(
            id=REGION_ID,
            company_id=COMPANY_DOWNTOWN_ID,
            camera_id=CAMERA_DOWNTOWN_ID,
            name="Checkout Zone",
            polygon=[{"x": 0.1, "y": 0.1}, {"x": 0.9, "y": 0.1}, {"x": 0.9, "y": 0.9}],
        )
        session.add(region)

    # Rule set with shift schedules
    rule_set = await session.get(RuleSet, RULE_SET_ID)
    if rule_set is None:
        rule_set = RuleSet(
            id=RULE_SET_ID,
            company_id=COMPANY_DOWNTOWN_ID,
            name="Business Hours",
            description="Default surveillance rule set for store hours",
            is_active=True,
        )
        session.add(rule_set)
        await session.flush()

        for day, start, end in (("mon", dt_time(8, 0), dt_time(20, 0)), ("tue", dt_time(8, 0), dt_time(20, 0)), ("sat", dt_time(9, 0), dt_time(18, 0))):
            session.add(
                RuleSetSchedule(
                    company_id=COMPANY_DOWNTOWN_ID,
                    rule_set_id=RULE_SET_ID,
                    day_of_week=day,
                    start_time=start,
                    end_time=end,
                    location_id=LOCATION_DOWNTOWN_ID,
                )
            )

    assignment = await session.scalar(
        select(RuleSetCameraAssignment).where(
            RuleSetCameraAssignment.camera_id == CAMERA_DOWNTOWN_ID
        )
    )
    if assignment is None:
        session.add(
            RuleSetCameraAssignment(
                company_id=COMPANY_DOWNTOWN_ID,
                rule_set_id=RULE_SET_ID,
                camera_id=CAMERA_DOWNTOWN_ID,
            )
        )

    # Recipe (AI analysis profile) with detection schema
    recipe = await session.get(Recipe, RECIPE_ID)
    if recipe is None:
        recipe = Recipe(
            id=RECIPE_ID,
            company_id=COMPANY_DOWNTOWN_ID,
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
                "required": ["is_suspicious", "detection_class", "confidence_score", "description"],
            },
        )
        session.add(recipe)

    # Rule bound to detection class + confidence threshold
    rule = await session.get(Rule, RULE_ID)
    if rule is None:
        rule = Rule(
            id=RULE_ID,
            company_id=COMPANY_DOWNTOWN_ID,
            rule_set_id=RULE_SET_ID,
            name="Shelf Tamper",
            detection_class="shelf_tamper",
            confidence_threshold=0.600,
            condition={"field": "suspicious", "op": "eq", "value": True},
            severity_weight=3,
        )
        session.add(rule)
        await session.flush()
        session.add(
            RuleRegionMapping(
                company_id=COMPANY_DOWNTOWN_ID,
                rule_id=RULE_ID,
                region_id=REGION_ID,
            )
        )

    # Users
    for spec in USERS:
        user = await session.scalar(select(CompanyUser).where(CompanyUser.email == spec["email"]))
        if user is None:
            session.add(
                CompanyUser(
                    id=spec["id"],
                    company_id=spec["company"],
                    email=spec["email"],
                    password_hash=hash_password(DEFAULT_PASSWORD),
                    role=spec["role"],
                )
            )
    ids["seed_password"] = DEFAULT_PASSWORD

    notif = await session.get(NotificationConfig, NOTIF_ID)
    if notif is None:
        session.add(
            NotificationConfig(
                id=NOTIF_ID,
                company_id=COMPANY_DOWNTOWN_ID,
                channel=NotificationChannel.SMS,
                recipient="+15551234567",
            )
        )

    await session.commit()
    await set_key(f"camera:active_mode:{CAMERA_DOWNTOWN_ID}", str(RULE_SET_ID), ex=86400)
    return ids


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
