"""Notification worker tests."""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime

import pytest

os.environ.setdefault("AUTH0_USE_MOCK", "true")

from argus.domain.enums import DecisionState, NotificationChannel, UserRole
from argus.domain.models import Decision, NotificationConfig
from argus.integrations.twilio_client import MockTwilioNotifier
from argus.services.database import dispose_engine, tenant_session
from argus.workers.notifier import _notify_warning

SEED_TENANT_ID = uuid.UUID("11111111-1111-4111-8111-111111111111")
SEED_CAMERA_ID = uuid.UUID("33333333-3333-4333-8333-333333333333")


@pytest.mark.asyncio
async def test_notify_warning_creates_delivery(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "argus.workers.notifier.get_notifier",
        lambda: MockTwilioNotifier(),
    )

    async with tenant_session(SEED_TENANT_ID, UserRole.TENANT_ADMIN.value) as session:
        decision = Decision(
            tenant_id=SEED_TENANT_ID,
            camera_id=SEED_CAMERA_ID,
            region_id=None,
            state=DecisionState.WARNING,
            cumulative_severity=6,
            evidence_count=3,
            window_start=datetime.now(UTC),
            window_end=datetime.now(UTC),
        )
        session.add(decision)
        await session.flush()
        session.add(
            NotificationConfig(
                tenant_id=SEED_TENANT_ID,
                channel=NotificationChannel.SMS,
                recipient="+15551234567",
            )
        )
        await session.flush()
        decision_id = str(decision.id)

    await _notify_warning(decision_id)
    await dispose_engine()
