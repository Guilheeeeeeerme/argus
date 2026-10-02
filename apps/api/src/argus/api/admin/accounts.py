"""Account and user management routes (platform only)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from argus.api.deps import get_platform_db
from argus.core.passwords import hash_password
from argus.domain.enums import UserRole
from argus.domain.models import Account, AccountUser, AccountUserMembership
from argus.domain.schemas.admin import (
    AssignAccountAdminRequest,
    CreateAccountRequest,
    CreateAccountUserRequest,
    AccountResponse,
    AccountUserResponse,
    UpdateAccountRequest,
    UpdateAccountUserRequest,
)

router = APIRouter(prefix="/admin", tags=["admin-accounts"])


@router.post("/accounts", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
async def create_account(
    body: CreateAccountRequest,
    session: AsyncSession = Depends(get_platform_db),
) -> Account:
    account = Account(
        name=body.name,
        slug=body.slug,
        kind=body.kind,
        aggregation_window_secs=body.aggregation_window_secs,
    )
    session.add(account)
    await session.flush()
    return account


@router.get("/accounts", response_model=list[AccountResponse])
async def list_accounts(
    session: AsyncSession = Depends(get_platform_db),
) -> list[Account]:
    return list((await session.scalars(select(Account).order_by(Account.name))).all())


@router.patch("/accounts/{account_id}", response_model=AccountResponse)
async def update_account(
    account_id: UUID,
    body: UpdateAccountRequest,
    session: AsyncSession = Depends(get_platform_db),
) -> Account:
    account = await session.get(Account, account_id)
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    for field in ("name", "slug", "kind", "aggregation_window_secs"):
        value = getattr(body, field)
        if value is not None:
            setattr(account, field, value)
    await session.flush()
    return account


@router.delete("/accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    account_id: UUID,
    session: AsyncSession = Depends(get_platform_db),
) -> None:
    account = await session.get(Account, account_id)
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    await session.delete(account)


@router.get("/users", response_model=list[AccountUserResponse])
async def list_users(
    session: AsyncSession = Depends(get_platform_db),
) -> list[AccountUser]:
    return list((await session.scalars(select(AccountUser).order_by(AccountUser.email))).all())


async def _set_memberships(session: AsyncSession, user: AccountUser, account_ids: list[UUID]) -> None:
    ids = list(dict.fromkeys(account_ids))
    if ids:
        found = set((await session.scalars(select(Account.id).where(Account.id.in_(ids)))).all())
        if found != set(ids):
            raise HTTPException(status_code=404, detail="Account not found")
    existing = {membership.account_id: membership for membership in user.memberships}
    user.memberships = [existing.get(cid) or AccountUserMembership(account_id=cid) for cid in ids]
    user.account_id = ids[0] if ids else None


@router.post("/users", response_model=AccountUserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    body: CreateAccountUserRequest,
    session: AsyncSession = Depends(get_platform_db),
) -> AccountUser:
    try:
        role = UserRole(body.role)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid user role") from exc
    user = AccountUser(
        memberships=[],
        account_id=body.account_id,
        email=body.email,
        idp_subject=body.idp_subject,
        password_hash=hash_password(body.password) if body.password else None,
        role=role,
    )
    account_ids = (
        body.account_ids if body.account_ids is not None
        else [body.account_id] if body.account_id else []
    )
    await _set_memberships(session, user, account_ids)
    session.add(user)
    await session.flush()
    return user


@router.patch("/users/{user_id}", response_model=AccountUserResponse)
async def update_user(
    user_id: UUID,
    body: UpdateAccountUserRequest,
    session: AsyncSession = Depends(get_platform_db),
) -> AccountUser:
    user = await session.get(AccountUser, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if body.email is not None:
        user.email = body.email
    if body.account_ids is not None:
        await _set_memberships(session, user, body.account_ids)
    elif "account_id" in body.model_fields_set:
        await _set_memberships(session, user, [body.account_id] if body.account_id else [])
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
    user = await session.get(AccountUser, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    await session.delete(user)


@router.post(
    "/accounts/{account_id}/managers",
    response_model=AccountUserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def assign_account_manager(
    account_id: UUID,
    body: AssignAccountAdminRequest,
    session: AsyncSession = Depends(get_platform_db),
) -> AccountUser:
    user = AccountUser(
        memberships=[AccountUserMembership(account_id=account_id)],
        account_id=account_id,
        idp_subject=body.idp_subject,
        email=body.email,
        password_hash=hash_password(body.password) if body.password else None,
        role=UserRole.MANAGER,
    )
    session.add(user)
    await session.flush()
    return user
