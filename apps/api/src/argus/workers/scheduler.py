"""Context mode scheduler — activate modes from schedules."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, time
from zoneinfo import ZoneInfo

from sqlalchemy import select

from argus.domain.enums import ScheduleDay, UserRole
from argus.domain.models import Camera, RuleSetCameraAssignment, RuleSetSchedule, Location
from argus.services.database import company_session
from argus.services.ingestion import ACTIVE_MODE_KEY, ACTIVE_MODE_TTL_SECS
from argus.services.redis import set_key
from argus.workers.celery_app import celery_app
from argus.workers.utils import run_async

logger = logging.getLogger(__name__)

_DAY_MAP = {
    0: ScheduleDay.MON,
    1: ScheduleDay.TUE,
    2: ScheduleDay.WED,
    3: ScheduleDay.THU,
    4: ScheduleDay.FRI,
    5: ScheduleDay.SAT,
    6: ScheduleDay.SUN,
}


def is_within_schedule(start: time, end: time, current: time) -> bool:
    if start <= end:
        return start <= current <= end
    return current >= start or current <= end


def matches_market(schedule_location_id, camera_location_id) -> bool:
    return schedule_location_id is None or schedule_location_id == camera_location_id


@celery_app.task(name="schedule.activate_scheduled_modes")
def activate_scheduled_modes() -> int:
    return run_async(_activate_scheduled_modes())


async def _activate_scheduled_modes() -> int:
    activated = 0
    async with company_session(None, UserRole.ROOT.value) as session:
        schedules = list((await session.scalars(select(RuleSetSchedule))).all())
        locations = {m.id: m for m in (await session.scalars(select(Location))).all()}
        assignments = list(
            (await session.scalars(select(RuleSetCameraAssignment))).all()
        )
        cameras = {
            camera.id: camera
            for camera in (await session.scalars(select(Camera))).all()
        }

    for schedule in schedules:
        market = locations.get(schedule.location_id) if schedule.location_id else None
        tz_name = market.timezone if market else "UTC"
        local_now = datetime.now(UTC).astimezone(ZoneInfo(tz_name))
        current_day = _DAY_MAP[local_now.weekday()]
        previous_day = _DAY_MAP[(local_now.weekday() - 1) % 7]
        if schedule.start_time <= schedule.end_time:
            day_matches = current_day == schedule.day_of_week
        else:
            day_matches = (
                current_day == schedule.day_of_week and local_now.time() >= schedule.start_time
            ) or (previous_day == schedule.day_of_week and local_now.time() <= schedule.end_time)
        if not day_matches or not is_within_schedule(
            schedule.start_time, schedule.end_time, local_now.time()
        ):
            continue

        for assignment in assignments:
            if assignment.rule_set_id != schedule.rule_set_id:
                continue
            if not matches_market(schedule.location_id, cameras[assignment.camera_id].location_id):
                continue
            key = ACTIVE_MODE_KEY.format(camera_id=assignment.camera_id)
            await set_key(key, str(schedule.rule_set_id), ex=ACTIVE_MODE_TTL_SECS)
            activated += 1
            logger.info(
                "Activated mode %s for camera %s",
                schedule.rule_set_id,
                assignment.camera_id,
            )

    return activated
