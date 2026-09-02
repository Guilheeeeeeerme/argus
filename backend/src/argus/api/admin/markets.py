"""Market management routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from argus.api.deps import get_tenant_db, require_role
from argus.core.auth import AuthContext
from argus.domain.enums import UserRole
from argus.domain.models import Market
from argus.domain.schemas.admin import CreateMarketRequest, MarketResponse

router = APIRouter(prefix="/tenants/{tenant_id}/markets", tags=["admin-markets"])


@router.get("", response_model=list[MarketResponse])
async def list_markets(
    session: AsyncSession = Depends(get_tenant_db),
    _auth: AuthContext = Depends(require_role(UserRole.TENANT_ADMIN, UserRole.ROOT_ADMIN)),
) -> list[Market]:
    return list(
        (
            await session.scalars(
                select(Market).where(Market.deleted_at.is_(None)).order_by(Market.name)
            )
        ).all()
    )


@router.post("", response_model=MarketResponse, status_code=status.HTTP_201_CREATED)
async def create_market(
    tenant_id: UUID,
    body: CreateMarketRequest,
    session: AsyncSession = Depends(get_tenant_db),
    _auth: AuthContext = Depends(require_role(UserRole.TENANT_ADMIN, UserRole.ROOT_ADMIN)),
) -> Market:
    market = Market(tenant_id=tenant_id, name=body.name, timezone=body.timezone)
    session.add(market)
    await session.flush()
    return market
