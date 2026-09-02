"""Notification worker — Twilio SMS/WhatsApp dispatch."""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import select

from argus.domain.enums import NotificationChannel, NotificationStatus, UserRole
from argus.integrations.twilio_client import get_notifier
from argus.services.database import tenant_session
from argus.domain.models import Decision, NotificationConfig, NotificationDelivery
from argus.workers.celery_app import celery_app
from argus.workers.utils import run_async

logger = logging.getLogger(__name__)


@celery_app.task(
    name="notify.notify_warning",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3,
)
def notify_warning(self, decision_id: str) -> str:
    return run_async(_notify_warning(decision_id))


async def _notify_warning(decision_id: str) -> str:
    notifier = get_notifier()
    async with tenant_session(None, UserRole.ROOT_ADMIN.value) as session:
        decision = await session.get(Decision, UUID(decision_id))
        if decision is None:
            raise ValueError(f"Decision not found: {decision_id}")

        configs = list(
            (
                await session.scalars(
                    select(NotificationConfig).where(
                        NotificationConfig.tenant_id == decision.tenant_id,
                        NotificationConfig.is_active.is_(True),
                    )
                )
            ).all()
        )

        for config in configs:
            delivery = NotificationDelivery(
                tenant_id=decision.tenant_id,
                decision_id=decision.id,
                config_id=config.id,
                channel=config.channel,
                status=NotificationStatus.PENDING,
            )
            session.add(delivery)
            await session.flush()

            deep_link = f"https://triage.argus.local/decisions/{decision.id}"
            body = (
                f"ARGUS Warning: decision {decision.id} on camera {decision.camera_id}. "
                f"Review: {deep_link}"
            )
            try:
                if config.channel == NotificationChannel.SMS:
                    sid = notifier.send_sms(to=config.recipient, body=body)
                else:
                    sid = notifier.send_whatsapp(to=config.recipient, body=body)
                delivery.status = NotificationStatus.SENT
                delivery.provider_message_id = sid
            except Exception as exc:
                delivery.status = NotificationStatus.FAILED
                delivery.error_detail = str(exc)
                logger.exception("Notification failed for decision %s", decision_id)
                raise

        await session.commit()
    return decision_id
