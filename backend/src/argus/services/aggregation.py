"""Evidence aggregation and Decision state machine."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from argus.domain.enums import DecisionState, UserRole
from argus.domain.models import Decision, DecisionEvidence, Evidence, Tenant
from argus.services.audit import write_audit_record
from argus.services.database import tenant_session
from argus.services.redis import delete_key, get_key, set_key
from argus.services.ws_events import publish_ws_event
from argus.integrations.events import publish_event

OPEN_DECISION_KEY = "decision:open:{tenant_id}:{camera_id}:{region_key}"


class AggregationService:
    async def aggregate(self, evidence_id: UUID) -> Decision:
        async with tenant_session(None, UserRole.ROOT_ADMIN.value) as session:
            evidence = await session.get(Evidence, evidence_id)
            if evidence is None:
                raise ValueError(f"Evidence not found: {evidence_id}")

            await session.execute(
                text("SELECT set_config('app.current_tenant_id', :tid, true)"),
                {"tid": str(evidence.tenant_id)},
            )
            await session.execute(
                text("SELECT set_config('app.current_role', :role, true)"),
                {"role": UserRole.TENANT_ADMIN.value},
            )

            tenant = await session.get(Tenant, evidence.tenant_id)
            if tenant is None:
                raise ValueError(f"Tenant not found: {evidence.tenant_id}")

            decision = await self._merge_or_create_decision(session, evidence, tenant)
            old_state = decision.state
            await self._apply_state_transitions(session, decision, tenant, old_state)
            await session.commit()
            return decision

    async def _merge_or_create_decision(
        self,
        session: AsyncSession,
        evidence: Evidence,
        tenant: Tenant,
    ) -> Decision:
        region_key = str(evidence.region_id) if evidence.region_id else "none"
        open_key = OPEN_DECISION_KEY.format(
            tenant_id=evidence.tenant_id,
            camera_id=evidence.camera_id,
            region_key=region_key,
        )
        open_id_raw = await get_key(open_key)
        decision: Decision | None = None

        if open_id_raw:
            decision = await session.get(
                Decision,
                UUID(open_id_raw),
                options=(selectinload(Decision.evidences),),
            )

        if decision and evidence.captured_at <= decision.window_end:
            await self._link_evidence(session, decision, evidence)
        else:
            if decision:
                await delete_key(open_key)
            decision = await self._create_decision(session, evidence, tenant)
            await set_key(
                open_key,
                str(decision.id),
                ex=tenant.aggregation_window_secs + 300,
            )
            await self._link_evidence(session, decision, evidence)

        return decision

    async def _create_decision(
        self,
        session: AsyncSession,
        evidence: Evidence,
        tenant: Tenant,
    ) -> Decision:
        window_start = evidence.captured_at
        window_end = window_start + timedelta(seconds=tenant.aggregation_window_secs)
        decision = Decision(
            tenant_id=evidence.tenant_id,
            camera_id=evidence.camera_id,
            region_id=evidence.region_id,
            state=DecisionState.NORMAL,
            cumulative_severity=0,
            evidence_count=0,
            window_start=window_start,
            window_end=window_end,
            first_evidence_at=evidence.captured_at,
            last_evidence_at=evidence.captured_at,
        )
        session.add(decision)
        await session.flush()
        return decision

    async def _link_evidence(
        self,
        session: AsyncSession,
        decision: Decision,
        evidence: Evidence,
    ) -> None:
        existing = await session.scalar(
            select(DecisionEvidence.evidence_id).where(
                DecisionEvidence.decision_id == decision.id,
                DecisionEvidence.evidence_id == evidence.id,
            )
        )
        if existing:
            return

        session.add(
            DecisionEvidence(
                tenant_id=evidence.tenant_id,
                decision_id=decision.id,
                evidence_id=evidence.id,
            )
        )
        decision.evidence_count += 1
        decision.cumulative_severity += evidence.severity_score
        decision.last_evidence_at = evidence.captured_at
        if decision.first_evidence_at is None:
            decision.first_evidence_at = evidence.captured_at

    async def _apply_state_transitions(
        self,
        session: AsyncSession,
        decision: Decision,
        tenant: Tenant,
        prior_state: DecisionState,
    ) -> None:
        new_state = self._compute_state(decision, tenant)
        if new_state == decision.state:
            return

        old_state = decision.state
        decision.state = new_state
        await write_audit_record(
            session,
            decision=decision,
            event_type="state_change",
            payload={
                "from_state": old_state.value,
                "to_state": new_state.value,
                "evidence_count": decision.evidence_count,
                "cumulative_severity": decision.cumulative_severity,
            },
            actor="worker-aggregator",
        )
        await self._emit_state_change(decision, old_state, new_state)

    def _compute_state(self, decision: Decision, tenant: Tenant) -> DecisionState:
        if decision.cumulative_severity >= tenant.warning_threshold:
            return DecisionState.WARNING
        if decision.evidence_count >= tenant.weird_threshold:
            return DecisionState.WEIRD
        return DecisionState.NORMAL

    async def _emit_state_change(
        self,
        decision: Decision,
        old_state: DecisionState,
        new_state: DecisionState,
    ) -> None:
        await publish_ws_event(
            tenant_id=decision.tenant_id,
            event_type="decision.state_changed",
            payload={
                "decision_id": str(decision.id),
                "camera_id": str(decision.camera_id),
                "region_id": str(decision.region_id) if decision.region_id else None,
                "previous_state": old_state.value,
                "current_state": new_state.value,
                "cumulative_severity": decision.cumulative_severity,
                "evidence_count": decision.evidence_count,
            },
        )
        await publish_event(
            event_type="decision.state_changed",
            tenant_id=str(decision.tenant_id),
            payload={
                "decision_id": str(decision.id),
                "current_state": new_state.value,
                "previous_state": old_state.value,
            },
        )

        if new_state == DecisionState.WARNING:
            from argus.workers.notify import notify_warning

            notify_warning.delay(str(decision.id))
