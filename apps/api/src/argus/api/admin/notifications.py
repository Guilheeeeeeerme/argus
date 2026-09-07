"""Notification configuration and delivery status routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from argus.api.deps import get_company_db, require_role
from argus.core.auth import AuthContext
from argus.domain.enums import UserRole
from argus.domain.models import Decision, NotificationConfig, NotificationDelivery
from argus.domain.schemas.admin import (
    CreateNotificationConfigRequest,
    NotificationConfigResponse,
    NotificationDeliveryResponse,
)

router = APIRouter(prefix="/companies/{company_id}", tags=["admin-notifications"])


@router.post(
    "/notification-configs",
    response_model=NotificationConfigResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_notification_config(
    company_id: UUID,
    body: CreateNotificationConfigRequest,
    session: AsyncSession = Depends(get_company_db),
    _auth: AuthContext = Depends(require_role(UserRole.MANAGER, UserRole.ROOT, UserRole.ADMIN)),
) -> NotificationConfig:
    config = NotificationConfig(
        company_id=company_id,
        channel=body.channel,
        recipient=body.recipient,
    )
    session.add(config)
    await session.flush()
    return config


@router.get("/notification-configs", response_model=list[NotificationConfigResponse])
async def list_notification_configs(
    session: AsyncSession = Depends(get_company_db),
    _auth: AuthContext = Depends(require_role(UserRole.MANAGER, UserRole.ROOT, UserRole.ADMIN)),
) -> list[NotificationConfig]:
    return list((await session.scalars(select(NotificationConfig))).all())


@router.get(
    "/decisions/{decision_id}/notification-deliveries",
    response_model=list[NotificationDeliveryResponse],
)
async def list_decision_deliveries(
    company_id: UUID,
    decision_id: UUID,
    session: AsyncSession = Depends(get_company_db),
    _auth: AuthContext = Depends(require_role(UserRole.MANAGER, UserRole.ROOT, UserRole.ADMIN)),
) -> list[NotificationDelivery]:
    decision = await session.get(Decision, decision_id)
    if decision is None or decision.company_id != company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Decision not found")
    return list(
        (
            await session.scalars(
                select(NotificationDelivery).where(
                    NotificationDelivery.decision_id == decision_id
                )
            )
        ).all()
    )
