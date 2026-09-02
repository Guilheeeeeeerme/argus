"""Append-only audit trail for decision lifecycle events."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from argus.domain.models import AuditRecord, Decision


async def write_audit_record(
    session: AsyncSession,
    *,
    decision: Decision,
    event_type: str,
    payload: dict[str, Any],
    actor: str | None = None,
) -> AuditRecord:
    record = AuditRecord(
        tenant_id=decision.tenant_id,
        decision_id=decision.id,
        event_type=event_type,
        payload=payload,
        actor=actor,
    )
    session.add(record)
    await session.flush()
    return record
