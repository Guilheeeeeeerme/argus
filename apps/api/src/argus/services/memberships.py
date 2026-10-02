"""Server-side membership checks for HTTP sessions and live account events."""

from uuid import UUID

from sqlalchemy import select

from argus.domain.enums import UserRole
from argus.domain.models import AccountUserMembership
from argus.services.database import account_session
from argus.services.sessions import get_session


async def has_account_membership(user_id: str, account_id: str) -> bool:
    try:
        user_uuid, account_uuid = UUID(user_id), UUID(account_id)
    except ValueError:
        return False
    async with account_session(None, UserRole.ROOT.value) as db:
        return await db.scalar(select(AccountUserMembership.user_id).where(
            AccountUserMembership.user_id == user_uuid,
            AccountUserMembership.account_id == account_uuid,
        )) is not None


async def can_receive_account_events(token: str | None, account_id: str) -> bool:
    if not token:
        return False
    session = await get_session(token)
    return bool(
        session and session.account_id == account_id
        and session.role in {UserRole.MANAGER.value, UserRole.OPERATOR.value}
        and await has_account_membership(session.user_id, account_id)
    )
