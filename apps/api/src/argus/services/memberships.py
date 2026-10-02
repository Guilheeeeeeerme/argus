"""Server-side membership checks for HTTP sessions and live company events."""

from uuid import UUID

from sqlalchemy import select

from argus.domain.enums import UserRole
from argus.domain.models import CompanyUserMembership
from argus.services.database import company_session
from argus.services.sessions import get_session


async def has_company_membership(user_id: str, company_id: str) -> bool:
    try:
        user_uuid, company_uuid = UUID(user_id), UUID(company_id)
    except ValueError:
        return False
    async with company_session(None, UserRole.ROOT.value) as db:
        return await db.scalar(select(CompanyUserMembership.user_id).where(
            CompanyUserMembership.user_id == user_uuid,
            CompanyUserMembership.company_id == company_uuid,
        )) is not None


async def can_receive_company_events(token: str | None, company_id: str) -> bool:
    if not token:
        return False
    session = await get_session(token)
    return bool(
        session and session.company_id == company_id
        and session.role in {UserRole.MANAGER.value, UserRole.OPERATOR.value}
        and await has_company_membership(session.user_id, company_id)
    )
