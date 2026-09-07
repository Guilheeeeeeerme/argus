"""Local authentication and company/location context routes (opaque Redis sessions)."""

from __future__ import annotations

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from argus.api.deps import get_platform_db
from argus.core.auth import AuthContext, get_auth_context
from argus.domain.enums import UserRole
from argus.domain.models import Location, Company, CompanyUser
from argus.services.database import get_db, set_session_context
from argus.services.sessions import (
    SessionData,
    create_session,
    delete_session,
    update_session,
)

router = APIRouter(prefix="/v1/auth", tags=["authentication"])


class LoginRequest(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    role: str
    companyId: str | None = None


class CompanyRef(BaseModel):
    id: str
    name: str
    slug: str


class LocationRef(BaseModel):
    id: str
    name: str
    address: str | None = None


class SessionResponse(BaseModel):
    token: str | None = None
    user: UserResponse
    activeCompany: CompanyRef | None = None
    activeLocation: LocationRef | None = None


class SwitchContextRequest(BaseModel):
    companyId: str | None = Field(default=None)
    locationId: str | None = Field(default=None)


def _user_response(user: CompanyUser) -> UserResponse:
    return UserResponse(
        id=str(user.id),
        email=user.email,
        role=user.role.value,
        companyId=str(user.company_id) if user.company_id else None,
    )


async def _session_payload(token: str, data: SessionData) -> SessionResponse:
    company = None
    location = None
    if data.company_id:
        async for session in get_db():
            await set_session_context(session, company_id=data.company_id, role=data.role)
            company = await session.scalar(select(Company).where(Company.id == data.company_id))
            if company is None:
                raise HTTPException(status_code=401, detail="Session company not found")
            if data.location_id:
                location = await session.scalar(
                    select(Location).where(Location.id == data.location_id, Location.deleted_at.is_(None))
                )
    elif data.location_id:
        raise HTTPException(status_code=401, detail="Session location without company")
    return SessionResponse(
        token=token,
        user=UserResponse(
            id=data.user_id,
            email=data.email,
            role=data.role,
            companyId=data.company_id,
        ),
        activeCompany=CompanyRef(id=str(company.id), name=company.name, slug=company.slug) if company else None,
        activeLocation=(
            LocationRef(id=str(location.id), name=location.name, address=location.address)
            if location
            else None
        ),
    )


@router.post("/login", response_model=SessionResponse)
async def login(body: LoginRequest) -> SessionResponse:
    async for session in get_db():
        # Login runs with platform context so seeded users are visible under RLS.
        await set_session_context(session, company_id=None, role=UserRole.ROOT.value)
        user = await session.scalar(select(CompanyUser).where(CompanyUser.email == body.email))
    if user is None or not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if not bcrypt.checkpw(body.password.encode(), user.password_hash.encode()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    data = SessionData(
        user_id=str(user.id),
        email=user.email,
        role=user.role.value,
        company_id=str(user.company_id) if user.company_id else None,
    )
    token = await create_session(data)
    return await _session_payload(token, data)


@router.post("/logout")
async def logout(auth: AuthContext = Depends(get_auth_context)) -> dict[str, bool]:
    await delete_session(auth.token)
    return {"ok": True}


@router.get("/me", response_model=SessionResponse)
async def me(auth: AuthContext = Depends(get_auth_context)) -> SessionResponse:
    data = SessionData(
        user_id=auth.sub,
        email=auth.email,
        role=auth.role.value,
        company_id=str(auth.company_id) if auth.company_id else None,
        location_id=str(auth.location_id) if auth.location_id else None,
    )
    return await _session_payload(auth.token, data)


@router.patch("/context", response_model=SessionResponse)
async def switch_context(
    body: SwitchContextRequest,
    session: AsyncSession = Depends(get_platform_db),
    auth: AuthContext = Depends(get_auth_context),
) -> SessionResponse:
    data = SessionData(
        user_id=auth.sub,
        email=auth.email,
        role=auth.role.value,
        company_id=str(auth.company_id) if auth.company_id else None,
        location_id=str(auth.location_id) if auth.location_id else None,
    )
    if body.companyId is not None:
        company = await session.scalar(select(Company).where(Company.id == body.companyId))
        if company is None:
            raise HTTPException(status_code=404, detail="Company not found")
        data.company_id = str(company.id)
        data.location_id = None
    if body.locationId is not None:
        if data.company_id is None:
            raise HTTPException(status_code=409, detail="Select a company first")
        location = await session.scalar(
            select(Location).where(
                Location.id == body.locationId,
                Location.company_id == data.company_id,
                Location.deleted_at.is_(None),
            )
        )
        if location is None:
            raise HTTPException(status_code=404, detail="Location not found")
        data.location_id = str(location.id)
    await update_session(auth.token, data)
    return await _session_payload(auth.token, data)
