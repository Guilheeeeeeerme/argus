"""Rule management routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from argus.api.deps import get_tenant_db, require_role
from argus.core.auth import AuthContext
from argus.domain.enums import UserRole
from argus.domain.models import ContextMode, RegionOfInterest, Rule, RuleRegionMapping
from argus.domain.schemas.admin import CreateRuleRequest, RuleResponse

router = APIRouter(prefix="/tenants/{tenant_id}/rules", tags=["admin-rules"])


@router.post("", response_model=RuleResponse, status_code=status.HTTP_201_CREATED)
async def create_rule(
    tenant_id: UUID,
    body: CreateRuleRequest,
    session: AsyncSession = Depends(get_tenant_db),
    _auth: AuthContext = Depends(require_role(UserRole.TENANT_ADMIN, UserRole.ROOT_ADMIN)),
) -> RuleResponse:
    mode = await session.get(ContextMode, body.context_mode_id)
    if mode is None or mode.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Context mode not found")

    rule = Rule(
        tenant_id=tenant_id,
        context_mode_id=body.context_mode_id,
        name=body.name,
        condition=body.condition,
        severity_weight=body.severity_weight,
    )
    session.add(rule)
    await session.flush()

    for region_id in body.region_ids:
        region = await session.get(RegionOfInterest, region_id)
        if region is None or region.tenant_id != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid region_id: {region_id}",
            )
        session.add(
            RuleRegionMapping(
                tenant_id=tenant_id,
                rule_id=rule.id,
                region_id=region_id,
            )
        )
    await session.flush()

    return RuleResponse(
        id=rule.id,
        context_mode_id=rule.context_mode_id,
        name=rule.name,
        condition=rule.condition,
        severity_weight=rule.severity_weight,
        region_ids=body.region_ids,
    )


@router.get("", response_model=list[RuleResponse])
async def list_rules(
    tenant_id: UUID,
    session: AsyncSession = Depends(get_tenant_db),
    _auth: AuthContext = Depends(require_role(UserRole.TENANT_ADMIN, UserRole.ROOT_ADMIN)),
) -> list[RuleResponse]:
    rules = list((await session.scalars(select(Rule).where(Rule.tenant_id == tenant_id))).all())
    result: list[RuleResponse] = []
    for rule in rules:
        mappings = list(
            (
                await session.scalars(
                    select(RuleRegionMapping.region_id).where(
                        RuleRegionMapping.rule_id == rule.id
                    )
                )
            ).all()
        )
        result.append(
            RuleResponse(
                id=rule.id,
                context_mode_id=rule.context_mode_id,
                name=rule.name,
                condition=rule.condition,
                severity_weight=rule.severity_weight,
                region_ids=mappings,
            )
        )
    return result
