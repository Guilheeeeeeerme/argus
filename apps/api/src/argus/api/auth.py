"""Local authentication and company/establishment context routes (opaque Redis sessions)."""

from __future__ import annotations

from uuid import UUID

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from argus.core.auth import AuthContext, get_auth_context
from argus.domain.enums import PLATFORM_ROLES, UserRole
from argus.domain.models import Company, CompanyUser, CompanyUserMembership, Establishment
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


class EstablishmentRef(BaseModel):
    id: str
    name: str
    address: str | None = None


class SessionResponse(BaseModel):
    token: str | None = None
    user: UserResponse
    activeCompany: CompanyRef | None = None
    activeEstablishment: EstablishmentRef | None = None
    # Backward-compatible alias for older clients.
    activeLocation: EstablishmentRef | None = None


class SwitchContextRequest(BaseModel):
    companyId: UUID | None = Field(default=None)
    establishmentId: UUID | None = Field(default=None)
    locationId: UUID | None = Field(default=None)  # alias


def _user_response(user: CompanyUser) -> UserResponse:
    return UserResponse(
        id=str(user.id),
        email=user.email,
        role=user.role.value,
        companyId=str(user.company_id) if user.company_id else None,
    )


async def _session_payload(token: str, data: SessionData) -> SessionResponse:
    company = None
    establishment = None
    establishment_id = data.establishment_id or data.location_id
    if data.company_id:
        async for session in get_db():
            await set_session_context(session, company_id=data.company_id, role=data.role)
            company = await session.scalar(select(Company).where(Company.id == data.company_id))
            if company is None:
                raise HTTPException(status_code=401, detail="Session company not found")
            if establishment_id:
                establishment = await session.scalar(
                    select(Establishment).where(
                        Establishment.id == establishment_id,
                        Establishment.company_id == data.company_id,
                        Establishment.active.is_(True),
                    )
                )
    elif establishment_id:
        raise HTTPException(status_code=401, detail="Session establishment without company")
    establishment_ref = (
        EstablishmentRef(
            id=str(establishment.id),
            name=establishment.name,
            address=establishment.address,
        )
        if establishment
        else None
    )
    return SessionResponse(
        token=token,
        user=UserResponse(
            id=data.user_id,
            email=data.email,
            role=data.role,
            companyId=data.company_id,
        ),
        activeCompany=CompanyRef(id=str(company.id), name=company.name, slug=company.slug)
        if company
        else None,
        activeEstablishment=establishment_ref,
        activeLocation=establishment_ref,
    )


@router.post("/login", response_model=SessionResponse)
async def login(body: LoginRequest) -> SessionResponse:
    email = body.email.lower()
    async for session in get_db():
        # Login runs with platform context so seeded users are visible under RLS.
        await set_session_context(session, company_id=None, role=UserRole.ROOT.value)
        user = await session.scalar(select(CompanyUser).where(CompanyUser.email == email))
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
    membership_ids = user.company_ids
    selected = (
        user.company_id if user.company_id in membership_ids
        else membership_ids[0] if len(membership_ids) == 1 else None
    )
    data = SessionData(
        user_id=str(user.id),
        email=user.email,
        role=user.role.value,
        company_id=str(selected) if selected else None,
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
        establishment_id=str(auth.establishment_id) if auth.establishment_id else None,
    )
    return await _session_payload(auth.token, data)


async def get_context_db(auth: AuthContext = Depends(get_auth_context)):
    """Trusted account lookup; every company result is explicitly membership-filtered."""
    async for session in get_db():
        await set_session_context(session, company_id=None, role=UserRole.ROOT.value)
        yield session


@router.get("/companies", response_model=list[CompanyRef])
async def available_companies(
    auth: AuthContext = Depends(get_auth_context),
    session: AsyncSession = Depends(get_context_db),
) -> list[CompanyRef]:
    query = select(Company).order_by(Company.name)
    if auth.role not in PLATFORM_ROLES:
        query = query.join(CompanyUserMembership).where(CompanyUserMembership.user_id == auth.sub)
    return [CompanyRef(id=str(c.id), name=c.name, slug=c.slug)
            for c in (await session.scalars(query)).all()]


@router.patch("/context", response_model=SessionResponse)
async def switch_context(
    body: SwitchContextRequest,
    session: AsyncSession = Depends(get_context_db),
    auth: AuthContext = Depends(get_auth_context),
) -> SessionResponse:
    data = SessionData(
        user_id=auth.sub,
        email=auth.email,
        role=auth.role.value,
        company_id=str(auth.company_id) if auth.company_id else None,
        establishment_id=str(auth.establishment_id) if auth.establishment_id else None,
    )
    if "companyId" in body.model_fields_set:
        if body.companyId is not None:
            if auth.role not in PLATFORM_ROLES:
                membership = await session.scalar(select(CompanyUserMembership.user_id).where(
                    CompanyUserMembership.user_id == auth.sub,
                    CompanyUserMembership.company_id == body.companyId,
                ))
                if membership is None:
                    raise HTTPException(status_code=403, detail="Company access denied")
            company = await session.scalar(select(Company).where(Company.id == body.companyId))
            if company is None:
                raise HTTPException(status_code=404, detail="Company not found")
            data.company_id = str(company.id)
        else:
            data.company_id = None
        data.establishment_id = None
        data.location_id = None
    if "establishmentId" in body.model_fields_set or "locationId" in body.model_fields_set:
        establishment_id = (
            body.establishmentId if "establishmentId" in body.model_fields_set else body.locationId
        )
        if establishment_id is not None:
            if data.company_id is None:
                raise HTTPException(status_code=409, detail="Select a company first")
            establishment = await session.scalar(select(Establishment).where(
                Establishment.id == establishment_id,
                Establishment.company_id == data.company_id,
                Establishment.active.is_(True),
            ))
            if establishment is None:
                raise HTTPException(status_code=404, detail="Establishment not found")
            data.establishment_id = str(establishment.id)
        else:
            data.establishment_id = None
        data.location_id = data.establishment_id
    await update_session(auth.token, data)
    return await _session_payload(auth.token, data)
