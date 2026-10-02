"""Local authentication and account/unit context routes (opaque Redis sessions)."""

from __future__ import annotations

from uuid import UUID

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from argus.core.auth import AuthContext, get_auth_context
from argus.domain.enums import PLATFORM_ROLES, UserRole
from argus.domain.models import Account, AccountUser, AccountUserMembership, Unit
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
    accountId: str | None = None


class AccountRef(BaseModel):
    id: str
    name: str
    slug: str


class UnitRef(BaseModel):
    id: str
    name: str
    address: str | None = None


class SessionResponse(BaseModel):
    token: str | None = None
    user: UserResponse
    activeAccount: AccountRef | None = None
    activeUnit: UnitRef | None = None


class SwitchContextRequest(BaseModel):
    accountId: UUID | None = Field(default=None)
    unitId: UUID | None = Field(default=None)


def _user_response(user: AccountUser) -> UserResponse:
    return UserResponse(
        id=str(user.id),
        email=user.email,
        role=user.role.value,
        accountId=str(user.account_id) if user.account_id else None,
    )


async def _session_payload(token: str, data: SessionData) -> SessionResponse:
    account = None
    unit = None
    unit_id = data.unit_id
    if data.account_id:
        async for session in get_db():
            await set_session_context(session, account_id=data.account_id, role=data.role)
            account = await session.scalar(select(Account).where(Account.id == data.account_id))
            if account is None:
                raise HTTPException(status_code=401, detail="Session account not found")
            if unit_id:
                unit = await session.scalar(
                    select(Unit).where(
                        Unit.id == unit_id,
                        Unit.account_id == data.account_id,
                        Unit.active.is_(True),
                    )
                )
    elif unit_id:
        raise HTTPException(status_code=401, detail="Session unit without account")
    unit_ref = (
        UnitRef(
            id=str(unit.id),
            name=unit.name,
            address=unit.address,
        )
        if unit
        else None
    )
    return SessionResponse(
        token=token,
        user=UserResponse(
            id=data.user_id,
            email=data.email,
            role=data.role,
            accountId=data.account_id,
        ),
        activeAccount=AccountRef(id=str(account.id), name=account.name, slug=account.slug)
        if account
        else None,
        activeUnit=unit_ref,
    )


@router.post("/login", response_model=SessionResponse)
async def login(body: LoginRequest) -> SessionResponse:
    email = body.email.lower()
    async for session in get_db():
        # Login runs with platform context so seeded users are visible under RLS.
        await set_session_context(session, account_id=None, role=UserRole.ROOT.value)
        user = await session.scalar(select(AccountUser).where(AccountUser.email == email))
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
    membership_ids = user.account_ids
    selected = (
        user.account_id if user.account_id in membership_ids
        else membership_ids[0] if len(membership_ids) == 1 else None
    )
    data = SessionData(
        user_id=str(user.id),
        email=user.email,
        role=user.role.value,
        account_id=str(selected) if selected else None,
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
        account_id=str(auth.account_id) if auth.account_id else None,
        unit_id=str(auth.unit_id) if auth.unit_id else None,
    )
    return await _session_payload(auth.token, data)


async def get_context_db(auth: AuthContext = Depends(get_auth_context)):
    """Trusted account lookup; every account result is explicitly membership-filtered."""
    async for session in get_db():
        await set_session_context(session, account_id=None, role=UserRole.ROOT.value)
        yield session


@router.get("/accounts", response_model=list[AccountRef])
async def available_accounts(
    auth: AuthContext = Depends(get_auth_context),
    session: AsyncSession = Depends(get_context_db),
) -> list[AccountRef]:
    query = select(Account).order_by(Account.name)
    if auth.role not in PLATFORM_ROLES:
        query = query.join(AccountUserMembership).where(AccountUserMembership.user_id == auth.sub)
    return [AccountRef(id=str(c.id), name=c.name, slug=c.slug)
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
        account_id=str(auth.account_id) if auth.account_id else None,
        unit_id=str(auth.unit_id) if auth.unit_id else None,
    )
    if "accountId" in body.model_fields_set:
        if body.accountId is not None:
            if auth.role not in PLATFORM_ROLES:
                membership = await session.scalar(select(AccountUserMembership.user_id).where(
                    AccountUserMembership.user_id == auth.sub,
                    AccountUserMembership.account_id == body.accountId,
                ))
                if membership is None:
                    raise HTTPException(status_code=403, detail="Account access denied")
            account = await session.scalar(select(Account).where(Account.id == body.accountId))
            if account is None:
                raise HTTPException(status_code=404, detail="Account not found")
            data.account_id = str(account.id)
        else:
            data.account_id = None
        data.unit_id = None
    if "unitId" in body.model_fields_set:
        unit_id = body.unitId
        if unit_id is not None:
            if data.account_id is None:
                raise HTTPException(status_code=409, detail="Select a account first")
            unit = await session.scalar(select(Unit).where(
                Unit.id == unit_id,
                Unit.account_id == data.account_id,
                Unit.active.is_(True),
            ))
            if unit is None:
                raise HTTPException(status_code=404, detail="Unit not found")
            data.unit_id = str(unit.id)
        else:
            data.unit_id = None
    await update_session(auth.token, data)
    return await _session_payload(auth.token, data)
