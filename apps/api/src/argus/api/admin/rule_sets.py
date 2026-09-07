"""Rule set, shift schedule, and recipe routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from argus.api.deps import get_company_db, require_role
from argus.core.auth import AuthContext
from argus.domain.enums import UserRole
from argus.domain.models import RuleSet, RuleSetSchedule, Recipe
from argus.domain.schemas.admin import (
    RuleSetResponse,
    CreateRuleSetRequest,
    CreateRecipeRequest,
    CreateScheduleRequest,
    RecipeResponse,
    ScheduleResponse,
)

router = APIRouter(prefix="/companies/{company_id}", tags=["admin-rule-sets"])


@router.post(
    "/rule-sets",
    response_model=RuleSetResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_rule_set(
    company_id: UUID,
    body: CreateRuleSetRequest,
    session: AsyncSession = Depends(get_company_db),
    _auth: AuthContext = Depends(require_role(UserRole.MANAGER, UserRole.ROOT, UserRole.ADMIN)),
) -> RuleSet:
    rule_set = RuleSet(
        company_id=company_id,
        name=body.name,
        description=body.description,
    )
    session.add(rule_set)
    await session.flush()
    return rule_set


@router.get("/rule-sets", response_model=list[RuleSetResponse])
async def list_rule_sets(
    session: AsyncSession = Depends(get_company_db),
    _auth: AuthContext = Depends(require_role(UserRole.MANAGER, UserRole.ROOT, UserRole.ADMIN)),
) -> list[RuleSet]:
    return list((await session.scalars(select(RuleSet))).all())


@router.post(
    "/rule-sets/{rule_set_id}/schedules",
    response_model=ScheduleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_schedule(
    company_id: UUID,
    rule_set_id: UUID,
    body: CreateScheduleRequest,
    session: AsyncSession = Depends(get_company_db),
    _auth: AuthContext = Depends(require_role(UserRole.MANAGER, UserRole.ROOT, UserRole.ADMIN)),
) -> RuleSetSchedule:
    rule_set = await session.get(RuleSet, rule_set_id)
    if rule_set is None or rule_set.company_id != company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule set not found")
    schedule = RuleSetSchedule(
        company_id=company_id,
        rule_set_id=rule_set_id,
        day_of_week=body.day_of_week,
        start_time=body.start_time,
        end_time=body.end_time,
        location_id=body.location_id,
    )
    session.add(schedule)
    await session.flush()
    return schedule


@router.post(
    "/rule-sets/{rule_set_id}/recipes",
    response_model=RecipeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_recipe(
    company_id: UUID,
    rule_set_id: UUID,
    body: CreateRecipeRequest,
    session: AsyncSession = Depends(get_company_db),
    _auth: AuthContext = Depends(require_role(UserRole.MANAGER, UserRole.ROOT, UserRole.ADMIN)),
) -> Recipe:
    rule_set = await session.get(RuleSet, rule_set_id)
    if rule_set is None or rule_set.company_id != company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule set not found")
    recipe = Recipe(
        company_id=company_id,
        rule_set_id=rule_set_id,
        name=body.name,
        system_prompt=body.system_prompt,
        output_schema=body.output_schema,
    )
    session.add(recipe)
    await session.flush()
    return recipe
