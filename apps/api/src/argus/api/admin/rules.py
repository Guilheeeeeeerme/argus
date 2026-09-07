"""Rule management routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from argus.api.deps import get_company_db, require_role
from argus.core.auth import AuthContext
from argus.domain.enums import UserRole
from argus.domain.models import RuleSet, RegionOfInterest, Rule, RuleRegionMapping
from argus.domain.schemas.admin import CreateRuleRequest, RuleResponse, UpdateRuleRequest

router = APIRouter(prefix="/companies/{company_id}/rules", tags=["admin-rules"])


@router.post("", response_model=RuleResponse, status_code=status.HTTP_201_CREATED)
async def create_rule(
    company_id: UUID,
    body: CreateRuleRequest,
    session: AsyncSession = Depends(get_company_db),
    _auth: AuthContext = Depends(require_role(UserRole.MANAGER, UserRole.ROOT, UserRole.ADMIN)),
) -> RuleResponse:
    mode = await session.get(RuleSet, body.rule_set_id)
    if mode is None or mode.company_id != company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule set not found")

    rule = Rule(
        company_id=company_id,
        rule_set_id=body.rule_set_id,
        name=body.name,
        detection_class=body.detection_class,
        confidence_threshold=body.confidence_threshold,
        condition=body.condition,
        severity_weight=body.severity_weight,
    )
    session.add(rule)
    await session.flush()

    for region_id in body.region_ids:
        region = await session.get(RegionOfInterest, region_id)
        if region is None or region.company_id != company_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid region_id: {region_id}",
            )
        session.add(
            RuleRegionMapping(
                company_id=company_id,
                rule_id=rule.id,
                region_id=region_id,
            )
        )
    await session.flush()

    return RuleResponse(
        id=rule.id,
        rule_set_id=rule.rule_set_id,
        name=rule.name,
        detection_class=rule.detection_class,
        confidence_threshold=float(rule.confidence_threshold),
        condition=rule.condition,
        severity_weight=rule.severity_weight,
        region_ids=body.region_ids,
    )


@router.get("", response_model=list[RuleResponse])
async def list_rules(
    company_id: UUID,
    session: AsyncSession = Depends(get_company_db),
    _auth: AuthContext = Depends(require_role(UserRole.MANAGER, UserRole.ROOT, UserRole.ADMIN)),
) -> list[RuleResponse]:
    rules = list((await session.scalars(select(Rule).where(Rule.company_id == company_id))).all())
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
                rule_set_id=rule.rule_set_id,
                name=rule.name,
                detection_class=rule.detection_class,
                confidence_threshold=float(rule.confidence_threshold),
                condition=rule.condition,
                severity_weight=rule.severity_weight,
                region_ids=mappings,
            )
        )
    return result


@router.patch("/{rule_id}", response_model=RuleResponse)
async def update_rule(
    company_id: UUID,
    rule_id: UUID,
    body: UpdateRuleRequest,
    session: AsyncSession = Depends(get_company_db),
    _auth: AuthContext = Depends(require_role(UserRole.MANAGER, UserRole.ROOT, UserRole.ADMIN)),
) -> RuleResponse:
    rule = await session.scalar(
        select(Rule).where(Rule.id == rule_id, Rule.company_id == company_id)
    )
    if rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")
    if body.name is not None:
        rule.name = body.name
    if body.detection_class is not None:
        rule.detection_class = body.detection_class
    if body.confidence_threshold is not None:
        rule.confidence_threshold = body.confidence_threshold
    if body.condition is not None:
        rule.condition = body.condition
    if body.severity_weight is not None:
        rule.severity_weight = body.severity_weight
    if body.region_ids is not None:
        for mapping in list(
            (await session.scalars(
                select(RuleRegionMapping).where(RuleRegionMapping.rule_id == rule.id)
            )).all()
        ):
            await session.delete(mapping)
        for region_id in body.region_ids:
            region = await session.get(RegionOfInterest, region_id)
            if region is None or region.company_id != company_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid region_id: {region_id}",
                )
            session.add(
                RuleRegionMapping(company_id=company_id, rule_id=rule.id, region_id=region_id)
            )
    await session.flush()
    mappings = list(
        (
            await session.scalars(
                select(RuleRegionMapping.region_id).where(RuleRegionMapping.rule_id == rule.id)
            )
        ).all()
    )
    return RuleResponse(
        id=rule.id,
        rule_set_id=rule.rule_set_id,
        name=rule.name,
        detection_class=rule.detection_class,
        confidence_threshold=float(rule.confidence_threshold),
        condition=rule.condition,
        severity_weight=rule.severity_weight,
        region_ids=mappings,
    )
