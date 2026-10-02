"""WebhookEndpoint admin CRUD — raw token returned once on create/rotate."""

from __future__ import annotations

import secrets
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from argus.api.deps import get_account_db, require_role
from argus.core.auth import AuthContext
from argus.core.passwords import hash_password
from argus.domain.enums import UserRole
from argus.domain.models import Unit, WebhookEndpoint
from argus.domain.schemas.admin import (
    CreateWebhookEndpointRequest,
    UpdateWebhookEndpointRequest,
    WebhookEndpointResponse,
)

router = APIRouter(
    prefix="/accounts/{account_id}/webhook-endpoints",
    tags=["admin-webhooks"],
)

_MANAGER_PLUS = (UserRole.MANAGER, UserRole.ROOT, UserRole.ADMIN)


def _new_token() -> str:
    return f"whsec_{secrets.token_urlsafe(32)}"


def _to_response(endpoint: WebhookEndpoint, *, token: str | None = None) -> WebhookEndpointResponse:
    return WebhookEndpointResponse(
        id=endpoint.id,
        name=endpoint.name,
        unit_id=endpoint.unit_id,
        active=endpoint.active,
        token=token,
    )


@router.get("", response_model=list[WebhookEndpointResponse])
async def list_webhook_endpoints(
    session: AsyncSession = Depends(get_account_db),
    _auth: AuthContext = Depends(require_role(*_MANAGER_PLUS)),
) -> list[WebhookEndpointResponse]:
    rows = list(
        (await session.scalars(select(WebhookEndpoint).order_by(WebhookEndpoint.name))).all()
    )
    return [_to_response(row) for row in rows]


@router.post("", response_model=WebhookEndpointResponse, status_code=status.HTTP_201_CREATED)
async def create_webhook_endpoint(
    account_id: UUID,
    body: CreateWebhookEndpointRequest,
    session: AsyncSession = Depends(get_account_db),
    _auth: AuthContext = Depends(require_role(*_MANAGER_PLUS)),
) -> WebhookEndpointResponse:
    if body.unit_id is not None:
        unit = await session.get(Unit, body.unit_id)
        if unit is None or unit.account_id != account_id:
            raise HTTPException(status_code=404, detail="Unit not found")
    raw = _new_token()
    endpoint = WebhookEndpoint(
        account_id=account_id,
        name=body.name,
        unit_id=body.unit_id,
        token_hash=hash_password(raw),
        active=body.active,
    )
    session.add(endpoint)
    await session.flush()
    return _to_response(endpoint, token=raw)


@router.patch("/{endpoint_id}", response_model=WebhookEndpointResponse)
async def update_webhook_endpoint(
    account_id: UUID,
    endpoint_id: UUID,
    body: UpdateWebhookEndpointRequest,
    session: AsyncSession = Depends(get_account_db),
    _auth: AuthContext = Depends(require_role(*_MANAGER_PLUS)),
) -> WebhookEndpointResponse:
    endpoint = await session.scalar(
        select(WebhookEndpoint).where(
            WebhookEndpoint.id == endpoint_id,
            WebhookEndpoint.account_id == account_id,
        )
    )
    if endpoint is None:
        raise HTTPException(status_code=404, detail="Webhook endpoint not found")
    if body.unit_id is not None:
        unit = await session.get(Unit, body.unit_id)
        if unit is None or unit.account_id != account_id:
            raise HTTPException(status_code=404, detail="Unit not found")
        endpoint.unit_id = body.unit_id
    if body.name is not None:
        endpoint.name = body.name
    if body.active is not None:
        endpoint.active = body.active
    await session.flush()
    return _to_response(endpoint)


@router.post("/{endpoint_id}/rotate", response_model=WebhookEndpointResponse)
async def rotate_webhook_token(
    account_id: UUID,
    endpoint_id: UUID,
    session: AsyncSession = Depends(get_account_db),
    _auth: AuthContext = Depends(require_role(*_MANAGER_PLUS)),
) -> WebhookEndpointResponse:
    endpoint = await session.scalar(
        select(WebhookEndpoint).where(
            WebhookEndpoint.id == endpoint_id,
            WebhookEndpoint.account_id == account_id,
        )
    )
    if endpoint is None:
        raise HTTPException(status_code=404, detail="Webhook endpoint not found")
    raw = _new_token()
    endpoint.token_hash = hash_password(raw)
    await session.flush()
    return _to_response(endpoint, token=raw)


@router.delete("/{endpoint_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook_endpoint(
    account_id: UUID,
    endpoint_id: UUID,
    session: AsyncSession = Depends(get_account_db),
    _auth: AuthContext = Depends(require_role(*_MANAGER_PLUS)),
) -> None:
    endpoint = await session.scalar(
        select(WebhookEndpoint).where(
            WebhookEndpoint.id == endpoint_id,
            WebhookEndpoint.account_id == account_id,
        )
    )
    if endpoint is None:
        raise HTTPException(status_code=404, detail="Webhook endpoint not found")
    await session.delete(endpoint)
