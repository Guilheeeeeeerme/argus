"""Evidence aggregator Celery worker."""

from __future__ import annotations

import logging
from uuid import UUID

from argus.services.aggregation import AggregationService
from argus.workers.celery_app import celery_app
from argus.workers.utils import run_async

logger = logging.getLogger(__name__)
_service = AggregationService()


@celery_app.task(name="aggregate.aggregate_evidence")
def aggregate_evidence(evidence_id: str) -> str:
    decision = run_async(_service.aggregate(UUID(evidence_id)))
    logger.info(
        "Aggregated evidence %s into decision %s state=%s",
        evidence_id,
        decision.id,
        decision.state.value,
    )
    return str(decision.id)
