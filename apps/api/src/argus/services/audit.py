"""Append-only audit trail for triage lifecycle events."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from argus.domain.models import AuditRecord


async def write_audit_record(
    session: AsyncSession,
    *,
    company_id: UUID,
    event_type: str,
    payload: dict[str, Any],
    actor: str | None = None,
    triage_case_id: UUID | None = None,
) -> AuditRecord:
    record = AuditRecord(
        company_id=company_id,
        triage_case_id=triage_case_id,
        event_type=event_type,
        payload=payload,
        actor=actor,
    )
    session.add(record)
    await session.flush()
    return record
