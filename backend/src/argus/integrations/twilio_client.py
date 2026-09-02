"""Twilio SMS and WhatsApp notification client."""

from __future__ import annotations

import logging
import uuid
from typing import Protocol, runtime_checkable

from argus.config import settings
from argus.domain.enums import NotificationChannel

logger = logging.getLogger(__name__)


@runtime_checkable
class NotifierClient(Protocol):
    def send_sms(self, *, to: str, body: str) -> str: ...
    def send_whatsapp(self, *, to: str, body: str, media_url: str | None = None) -> str: ...


class TwilioNotifier:
    def __init__(self) -> None:
        from twilio.rest import Client

        self._client = Client(settings.twilio_account_sid, settings.twilio_auth_token)

    def send_sms(self, *, to: str, body: str) -> str:
        message = self._client.messages.create(
            to=to,
            from_=settings.twilio_sms_from,
            body=body,
        )
        return message.sid

    def send_whatsapp(self, *, to: str, body: str, media_url: str | None = None) -> str:
        kwargs: dict = {
            "to": f"whatsapp:{to}" if not to.startswith("whatsapp:") else to,
            "from_": settings.twilio_whatsapp_from,
            "body": body,
        }
        if media_url:
            kwargs["media_url"] = [media_url]
        message = self._client.messages.create(**kwargs)
        return message.sid


class MockTwilioNotifier:
    def send_sms(self, *, to: str, body: str) -> str:
        if settings.dev_notify_fail:
            raise RuntimeError("simulated development notification failure")
        sid = f"SM{uuid.uuid4().hex[:32]}"
        logger.info("Mock SMS to %s: %s (sid=%s)", to, body[:80], sid)
        return sid

    def send_whatsapp(self, *, to: str, body: str, media_url: str | None = None) -> str:
        if settings.dev_notify_fail:
            raise RuntimeError("simulated development notification failure")
        sid = f"SM{uuid.uuid4().hex[:32]}"
        logger.info("Mock WhatsApp to %s media=%s (sid=%s)", to, media_url, sid)
        return sid


def get_notifier() -> NotifierClient:
    if settings.notification_mode == "twilio" and settings.twilio_account_sid and settings.twilio_auth_token:
        return TwilioNotifier()
    return MockTwilioNotifier()
