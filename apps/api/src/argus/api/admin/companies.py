"""Company and user management routes (platform only)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from argus.api.deps import get_platform_db
from argus.core.passwords import hash_password
from argus.domain.enums import UserRole
from argus.domain.models import Company, CompanyUser
from argus.domain.schemas.admin import (
    AssignCompanyAdminRequest,
    CreateCompanyRequest,
    CreateCompanyUserRequest,
    CompanyResponse,
    CompanyUserResponse,
    UpdateCompanyRequest,
    UpdateCompanyUserRequest,
)

router = APIRouter(prefix="/admin", tags=["admin-companies"])


@router.post("/companies", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
async def create_company(
    body: CreateCompanyRequest,
    session: AsyncSession = Depends(get_platform_db),
) -> Company:
    company = Company(
        name=body.name,
        slug=body.slug,
        aggregation_window_secs=body.aggregation_window_secs,
    )
    session.add(company)
    await session.flush()
    return company


@router.get("/companies", response_model=list[CompanyResponse])
async def list_companies(
    session: AsyncSession = Depends(get_platform_db),
) -> list[Company]:
    return list((await session.scalars(select(Company).order_by(Company.name))).all())


@router.patch("/companies/{company_id}", response_model=CompanyResponse)
async def update_company(
    company_id: UUID,
    body: UpdateCompanyRequest,
    session: AsyncSession = Depends(get_platform_db),
) -> Company:
    company = await session.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    for field in ("name", "slug", "aggregation_window_secs"):
        value = getattr(body, field)
        if value is not None:
            setattr(company, field, value)
    await session.flush()
    return company


@router.delete("/companies/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_company(
    company_id: UUID,
    session: AsyncSession = Depends(get_platform_db),
) -> None:
    company = await session.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    await session.delete(company)


@router.get("/users", response_model=list[CompanyUserResponse])
async def list_users(
    session: AsyncSession = Depends(get_platform_db),
) -> list[CompanyUser]:
    return list((await session.scalars(select(CompanyUser).order_by(CompanyUser.email))).all())


@router.post("/users", response_model=CompanyUserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    body: CreateCompanyUserRequest,
    session: AsyncSession = Depends(get_platform_db),
) -> CompanyUser:
    try:
        role = UserRole(body.role)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid user role") from exc
    user = CompanyUser(
        company_id=body.company_id,
        email=body.email,
        idp_subject=body.idp_subject,
        password_hash=hash_password(body.password) if body.password else None,
        role=role,
    )
    session.add(user)
    await session.flush()
    return user


@router.patch("/users/{user_id}", response_model=CompanyUserResponse)
async def update_user(
    user_id: UUID,
    body: UpdateCompanyUserRequest,
    session: AsyncSession = Depends(get_platform_db),
) -> CompanyUser:
    user = await session.get(CompanyUser, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if body.email is not None:
        user.email = body.email
    if body.company_id is not None:
        user.company_id = body.company_id
    if body.role is not None:
        try:
            user.role = UserRole(body.role)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Invalid user role") from exc
    if body.password is not None:
        user.password_hash = hash_password(body.password)
    await session.flush()
    return user


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUID,
    session: AsyncSession = Depends(get_platform_db),
) -> None:
    user = await session.get(CompanyUser, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    await session.delete(user)


@router.post(
    "/companies/{company_id}/managers",
    response_model=CompanyUserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def assign_company_manager(
    company_id: UUID,
    body: AssignCompanyAdminRequest,
    session: AsyncSession = Depends(get_platform_db),
) -> CompanyUser:
    user = CompanyUser(
        company_id=company_id,
        idp_subject=body.idp_subject,
        email=body.email,
        password_hash=hash_password(body.password) if body.password else None,
        role=UserRole.MANAGER,
    )
    session.add(user)
    await session.flush()
    return user
