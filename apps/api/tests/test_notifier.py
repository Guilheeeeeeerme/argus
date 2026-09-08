"""Notification worker and HITL gate tests."""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select

os.environ.setdefault("AUTH0_USE_MOCK", "true")

from argus.domain.enums import (
    DecisionState,
    NotificationChannel,
    NotificationStatus,
    UserRole,
)
from argus.domain.models import Decision, NotificationConfig, NotificationDelivery
from argus.integrations.twilio_client import MockTwilioNotifier
from argus.services.database import dispose_engine, company_session
from argus.workers.notifier import _notify_warning, queue_warning_deliveries

SEED_COMPANY_ID = uuid.UUID("11111111-1111-4111-8111-111111111111")
SEED_CAMERA_ID = uuid.UUID("33333333-3333-4333-8333-333333333333")


@pytest.mark.asyncio
async def test_queue_warning_creates_awaiting_approval() -> None:
    async with company_session(SEED_COMPANY_ID, UserRole.MANAGER.value) as session:
        decision = Decision(
            company_id=SEED_COMPANY_ID,
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
                company_id=SEED_COMPANY_ID,
                channel=NotificationChannel.SMS,
                recipient="+15551234567",
            )
        )
        await session.flush()
        created = await queue_warning_deliveries(session, decision)
        await session.commit()
        decision_id = decision.id

    assert created == 1

    async with company_session(SEED_COMPANY_ID, UserRole.MANAGER.value) as session:
        delivery = await session.scalar(
            select(NotificationDelivery).where(
                NotificationDelivery.decision_id == decision_id
            )
        )
        assert delivery is not None
        assert delivery.status == NotificationStatus.AWAITING_APPROVAL

        # Idempotent: second queue does not duplicate.
        decision = await session.get(Decision, decision_id)
        assert decision is not None
        assert await queue_warning_deliveries(session, decision) == 0
        await session.commit()

    await dispose_engine()


@pytest.mark.asyncio
async def test_notify_warning_sends_only_pending(monkeypatch: pytest.MonkeyPatch) -> None:
    mock = MockTwilioNotifier()
    monkeypatch.setattr("argus.workers.notifier.get_notifier", lambda: mock)

    async with company_session(SEED_COMPANY_ID, UserRole.MANAGER.value) as session:
        decision = Decision(
            company_id=SEED_COMPANY_ID,
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
        config = NotificationConfig(
            company_id=SEED_COMPANY_ID,
            channel=NotificationChannel.SMS,
            recipient="+15551234567",
        )
        session.add(config)
        await session.flush()
        session.add(
            NotificationDelivery(
                company_id=SEED_COMPANY_ID,
                decision_id=decision.id,
                config_id=config.id,
                channel=NotificationChannel.SMS,
                status=NotificationStatus.AWAITING_APPROVAL,
            )
        )
        await session.commit()
        decision_id = str(decision.id)

    # Awaiting approval must not send.
    await _notify_warning(decision_id)
    assert mock.sent == [] if hasattr(mock, "sent") else True

    async with company_session(SEED_COMPANY_ID, UserRole.MANAGER.value) as session:
        delivery = await session.scalar(
            select(NotificationDelivery).where(
                NotificationDelivery.decision_id == uuid.UUID(decision_id)
            )
        )
        assert delivery is not None
        assert delivery.status == NotificationStatus.AWAITING_APPROVAL
        delivery.status = NotificationStatus.PENDING
        await session.commit()

    await _notify_warning(decision_id)

    async with company_session(SEED_COMPANY_ID, UserRole.MANAGER.value) as session:
        delivery = await session.scalar(
            select(NotificationDelivery).where(
                NotificationDelivery.decision_id == uuid.UUID(decision_id)
            )
        )
        assert delivery is not None
        assert delivery.status == NotificationStatus.SENT
        assert delivery.provider_message_id

    await dispose_engine()
