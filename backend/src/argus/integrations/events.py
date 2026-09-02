"""Development-friendly event sink with optional AWS SNS/EventBridge output."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from argus.config import settings

logger = logging.getLogger(__name__)


def _publish_aws(event: dict[str, Any]) -> None:
    import boto3

    if settings.event_transport == "sns":
        if not settings.sns_topic_arn:
            raise RuntimeError("SNS_TOPIC_ARN is required when EVENT_TRANSPORT=sns")
        boto3.client("sns", region_name=settings.aws_region).publish(
            TopicArn=settings.sns_topic_arn,
            Subject="ARGUS decision event",
            Message=json.dumps(event),
        )
    elif settings.event_transport == "eventbridge":
        boto3.client("events", region_name=settings.aws_region).put_events(
            Entries=[
                {
                    "EventBusName": settings.eventbridge_bus_name,
                    "Source": "argus",
                    "DetailType": event["type"],
                    "Detail": json.dumps(event),
                }
            ]
        )


async def publish_event(*, event_type: str, tenant_id: str, payload: dict[str, Any]) -> None:
    event = {"type": event_type, "tenant_id": tenant_id, "payload": payload}
    if settings.event_transport == "log":
        logger.info("ARGUS_EVENT %s", json.dumps(event, sort_keys=True))
        return
    await asyncio.to_thread(_publish_aws, event)
