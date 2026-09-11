"""WebhookEndpoint admin CRUD — raw token returned once on create/rotate."""

from __future__ import annotations

import secrets
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from argus.api.deps import get_company_db, require_role
from argus.core.auth import AuthContext
from argus.core.passwords import hash_password
from argus.domain.enums import UserRole
from argus.domain.models import Establishment, WebhookEndpoint
from argus.domain.schemas.admin import (
    CreateWebhookEndpointRequest,
    UpdateWebhookEndpointRequest,
    WebhookEndpointResponse,
)

router = APIRouter(
    prefix="/companies/{company_id}/webhook-endpoints",
    tags=["admin-webhooks"],
)

_MANAGER_PLUS = (UserRole.MANAGER, UserRole.ROOT, UserRole.ADMIN)


def _new_token() -> str:
    return f"whsec_{secrets.token_urlsafe(32)}"


def _to_response(endpoint: WebhookEndpoint, *, token: str | None = None) -> WebhookEndpointResponse:
    return WebhookEndpointResponse(
        id=endpoint.id,
        name=endpoint.name,
        establishment_id=endpoint.establishment_id,
        active=endpoint.active,
        token=token,
    )


@router.get("", response_model=list[WebhookEndpointResponse])
async def list_webhook_endpoints(
    session: AsyncSession = Depends(get_company_db),
    _auth: AuthContext = Depends(require_role(*_MANAGER_PLUS)),
) -> list[WebhookEndpointResponse]:
    rows = list(
        (await session.scalars(select(WebhookEndpoint).order_by(WebhookEndpoint.name))).all()
    )
    return [_to_response(row) for row in rows]


@router.post("", response_model=WebhookEndpointResponse, status_code=status.HTTP_201_CREATED)
async def create_webhook_endpoint(
    company_id: UUID,
    body: CreateWebhookEndpointRequest,
    session: AsyncSession = Depends(get_company_db),
    _auth: AuthContext = Depends(require_role(*_MANAGER_PLUS)),
) -> WebhookEndpointResponse:
    if body.establishment_id is not None:
        establishment = await session.get(Establishment, body.establishment_id)
        if establishment is None or establishment.company_id != company_id:
            raise HTTPException(status_code=404, detail="Establishment not found")
    raw = _new_token()
    endpoint = WebhookEndpoint(
        company_id=company_id,
        name=body.name,
        establishment_id=body.establishment_id,
        token_hash=hash_password(raw),
        active=body.active,
    )
    session.add(endpoint)
    await session.flush()
    return _to_response(endpoint, token=raw)


@router.patch("/{endpoint_id}", response_model=WebhookEndpointResponse)
async def update_webhook_endpoint(
    company_id: UUID,
    endpoint_id: UUID,
    body: UpdateWebhookEndpointRequest,
    session: AsyncSession = Depends(get_company_db),
    _auth: AuthContext = Depends(require_role(*_MANAGER_PLUS)),
) -> WebhookEndpointResponse:
    endpoint = await session.scalar(
        select(WebhookEndpoint).where(
            WebhookEndpoint.id == endpoint_id,
            WebhookEndpoint.company_id == company_id,
        )
    )
    if endpoint is None:
        raise HTTPException(status_code=404, detail="Webhook endpoint not found")
    if body.establishment_id is not None:
        establishment = await session.get(Establishment, body.establishment_id)
        if establishment is None or establishment.company_id != company_id:
            raise HTTPException(status_code=404, detail="Establishment not found")
        endpoint.establishment_id = body.establishment_id
    if body.name is not None:
        endpoint.name = body.name
    if body.active is not None:
        endpoint.active = body.active
    await session.flush()
    return _to_response(endpoint)


@router.post("/{endpoint_id}/rotate", response_model=WebhookEndpointResponse)
async def rotate_webhook_token(
    company_id: UUID,
    endpoint_id: UUID,
    session: AsyncSession = Depends(get_company_db),
    _auth: AuthContext = Depends(require_role(*_MANAGER_PLUS)),
) -> WebhookEndpointResponse:
    endpoint = await session.scalar(
        select(WebhookEndpoint).where(
            WebhookEndpoint.id == endpoint_id,
            WebhookEndpoint.company_id == company_id,
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
    company_id: UUID,
    endpoint_id: UUID,
    session: AsyncSession = Depends(get_company_db),
    _auth: AuthContext = Depends(require_role(*_MANAGER_PLUS)),
) -> None:
    endpoint = await session.scalar(
        select(WebhookEndpoint).where(
            WebhookEndpoint.id == endpoint_id,
            WebhookEndpoint.company_id == company_id,
        )
    )
    if endpoint is None:
        raise HTTPException(status_code=404, detail="Webhook endpoint not found")
    await session.delete(endpoint)
