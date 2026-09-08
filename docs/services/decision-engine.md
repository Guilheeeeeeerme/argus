# Service sketch: decision-engine

> Status: **IMPLEMENTED inside `apps/api`** (`services/aggregation.py` +
> `workers/aggregator.py`), to be extracted later. This document is the
> handoff. Related: `image-analysis.md`, `notifications.md`, `realtime-page.md`.

## Purpose

Group matched detections (Evidence) into **Decisions**, run the state machine,
raise **alarms** (notifications on warning), and stream state changes to the
triage UI over WebSocket.

## Pipeline (current, working)

```
Evidence created (image-analysis) → aggregate_evidence.delay(evidence_id)
  → AggregationService.aggregate(evidence_id)
      1. platform-context session (RLS role=root bypass) to read the evidence
      2. switch context to the evidence company (role=manager)
      3. merge-or-create Decision:
           - open-decision key in Redis:
             decision:open:{company_id}:{camera_id}:{region_key}
             TTL = company.aggregation_window_secs + 300
           - same window + same camera + same region → link evidence
             (cumulative_severity += evidence.severity_score)
           - else: close old, create new Decision (window = captured_at +
             aggregation_window_secs)
      4. state machine (_compute_state):
           WARNING when cumulative_severity >= company.warning_threshold
           WEIRD    when evidence_count      >= company.weird_threshold
           NORMAL   otherwise
      5. on transition: audit record + WS event + event transport
           - WARNING also queues notification_deliveries as
             awaiting_approval (HITL; no Twilio send until approve-notify)
```

## Contracts

- **Redis keys**: `decision:open:{company_id}:{camera_id}:{region_key}`.
- **WS event** (`decision.state_changed` envelope):
  `{type, company_id, timestamp, payload: {decision_id, camera_id, region_id,
  previous_state, current_state, cumulative_severity, evidence_count}}`.
  Delivered via Redis pub/sub (`chat`-style channel `argus:ws` — see
  `services/ws_events.py` + `ws/pubsub.py`) to the WS router mounted on the
  admin API (`/v1/ws?token=<session>`; company-scoped rooms).
- **Audit**: every transition writes `audit_records` (actor `worker-aggregator`).
- **States** (enum `decision_state`): `normal, weird, warning,
  resolved_true_positive, resolved_false_positive, resolved_false_negative`.
  Resolves are terminal → view-only.

## Where the code lives

| Concern | File |
|---|---|
| Aggregation + state machine | `apps/api/src/argus/services/aggregation.py` |
| Celery entry | `apps/api/src/argus/workers/aggregator.py` |
| Audit | `services/audit.py` |
| WS publish | `services/ws_events.py` + `ws/pubsub.py` + `ws/gateway.py` |
| Event transport (log/SNS/EventBridge) | `integrations/events.py` (log mode in dev) |

## Extraction checklist (when to split)

1. Move `aggregation.py` + `aggregator.py` into `services/decision-engine/`
   (its own Celery app, same broker).
2. It needs: `REDIS_URL`, `DATABASE_URL`, WS publish (Redis pub/sub — unchanged
   contract), event transport config.
3. Compose: register as `decisions` on `argus_dmz`; drop task from the api
   worker's include list.
4. Acceptance: seeded ingest scenario still walks normal→weird→warning;
   WARNING triggers one notification (idempotent per decision).

## Runbook (start / resume)

- Runs inside the `worker` compose service: `docker compose up -d worker`.
- Re-aggregate an evidence manually:
  ```bash
  docker compose exec worker celery -A argus.workers.celery_app call \
    aggregate.aggregate_evidence --args '["<evidence_uuid>"]'
  ```
- Stale open-decision keys (Redis restart mid-window) are harmless: the
  aggregator re-opens a fresh window on the next evidence.
- Tests: `test_workers.py::test_aggregator_groups_evidences_into_decision`,
  `test_out_of_order_evidence_merges_into_same_decision`, `test_notifier.py`.

## Open decisions

- Alarm dedup/window tuning per location (today: company-level thresholds).
- Whether resolves should be bound to the Decision or to the underlying rule
  (rule-level feedback for RAG).
- Escalation chain (warning → critical) — not modeled yet.
