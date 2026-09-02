"""Context mode scheduler — activate modes from schedules."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select

from argus.domain.enums import ScheduleDay, UserRole
from argus.domain.models import ContextModeCameraAssignment, ContextModeSchedule, Market
from argus.services.database import tenant_session
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


@celery_app.task(name="schedule.activate_scheduled_modes")
def activate_scheduled_modes() -> int:
    return run_async(_activate_scheduled_modes())


async def _activate_scheduled_modes() -> int:
    activated = 0
    async with tenant_session(None, UserRole.ROOT_ADMIN.value) as session:
        schedules = list((await session.scalars(select(ContextModeSchedule))).all())
        markets = {m.id: m for m in (await session.scalars(select(Market))).all()}
        assignments = list(
            (await session.scalars(select(ContextModeCameraAssignment))).all()
        )

    for schedule in schedules:
        market = markets.get(schedule.market_id) if schedule.market_id else None
        tz_name = market.timezone if market else "UTC"
        local_now = datetime.now(UTC).astimezone(ZoneInfo(tz_name))
        if _DAY_MAP[local_now.weekday()] != schedule.day_of_week:
            continue
        if not (schedule.start_time <= local_now.time() <= schedule.end_time):
            continue

        for assignment in assignments:
            if assignment.context_mode_id != schedule.context_mode_id:
                continue
            if schedule.market_id:
                # Filter cameras by market via assignment tenant scope only for MVP
                pass
            key = ACTIVE_MODE_KEY.format(camera_id=assignment.camera_id)
            await set_key(key, str(schedule.context_mode_id), ex=ACTIVE_MODE_TTL_SECS)
            activated += 1
            logger.info(
                "Activated mode %s for camera %s",
                schedule.context_mode_id,
                assignment.camera_id,
            )

    return activated
