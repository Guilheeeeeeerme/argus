# Service sketch: notifications

> Status: **PARTIALLY IMPLEMENTED** inside `apps/api` (config CRUD +
> HITL-gated `notify` worker in log mode). Extraction + channel expansion
> are pending. This document is the handoff. Related: `decision-engine.md`.

## Purpose

Configure and deliver alarms raised by the decision engine: per-company
notification configs (channels + recipients), delivery attempts with status
tracking, and dedup so one decision alarms once.

## What exists today

| Piece | State | File |
|---|---|---|
| `notification_configs` CRUD (channel, recipient, is_active) | Implemented, routes `/v1/companies/{company_id}/notifications`, manager+ roles | `api/admin/notifications.py` |
| `notification_deliveries` (decision_id, channel, status, provider_message_id, error_detail) | Implemented (model + API read) | migration `005_operational` + `009_notify_hitl` |
| Twilio client (SMS/WhatsApp) | Implemented, behind `NOTIFICATION_MODE=log` | `integrations/twilio_client.py` |
| WARNING → queue deliveries | Implemented — creates `awaiting_approval` rows; **does not send** | `services/aggregation.py` → `queue_warning_deliveries` |
| HITL approve / dismiss | Implemented — manager+ `POST .../approve-notify` and `.../dismiss-notify` | `api/triage/decisions.py`, triage `DecisionDetail.tsx` |
| `notify_warning` task | Implemented — sends only `pending` deliveries (after approve) with a **deterministic** SMS body (no model prose) | `workers/notifier.py`, `workers/notify.py` |
| Delivery lifecycle | `awaiting_approval` → `pending` → `sent`/`failed`, or `dismissed` | `domain/enums.py` |

## HITL gate (Lethal Trifecta / Rule of Two)

External SMS/WhatsApp is a high-impact egress channel. Model-driven severity
must not auto-page humans:

1. Aggregator transitions a decision to WARNING and queues
   `notification_deliveries` with status `awaiting_approval` (one per active
   config; idempotent on `(decision_id, config_id)`).
2. A manager+ reviews the decision in triage and either:
   - **Approve notify** — sets deliveries to `pending` and enqueues
     `notify_warning`, which sends the deterministic body and marks `sent`.
   - **Dismiss notify** — sets deliveries to `dismissed`; no provider call.
3. SMS body is fixed template text + decision/camera ids + triage deep link —
   never VLM reasoning or free-form model output.

## Responsibilities (to build / extract)

1. **Per-decision dedup** — one delivery per (decision, config). Queue helper
   skips existing rows before insert.
2. **Channel adapters** behind one interface:
   - `log` (dev, current),
   - `twilio` SMS/WhatsApp (client exists — wire `NOTIFICATION_MODE=twilio`),
   - `webhook` (to build: POST decision payload to a company-configured URL,
     signed HMAC with a per-company secret),
   - `email` (optional later).
3. **Retry policy** — delivery failures → status `failed` + `error_detail`;
   exponential backoff via Celery retries (3), then surfaced in the Admin UI.
4. **Read receipts** — webhook/WhatsApp statuses update to
   `delivered` (provider callback route, token-protected internal endpoint).
5. **Quiet hours / shifts awareness** — respect the RuleSet schedules that
   produced the decision (do not page outside the shift unless severity is
   high); decision payload already carries the rule_set_id.
6. **Admin UI** — Notifications page in the admin app: list configs, add
   channel+recipient, toggle active, show recent deliveries with status.

## Suggested shape when extracted

```
services/notifications/
  app.py          # FastAPI or plain Celery worker — decision: notifications only
  channels/       # log.py, twilio.py, webhook.py, base.py
  tasks.py        # deliver(decision_id, config_id) with dedup + retries
  callbacks.py    # provider status callbacks (webhook + twilio)
```

Contracts it consumes:
- Trigger: WARNING → `queue_warning_deliveries`; send only after
  `approve-notify` → `notify_warning.delay(decision_id)`.
- Reads: `decisions`, `notification_configs` (company scoped, RLS role=manager).
- Writes: `notification_deliveries` + provider APIs.

## Configuration (env, already in `argus.config`)

| Var | Meaning |
|---|---|
| `NOTIFICATION_MODE` | `log` (default) \| `twilio` |
| `TWILIO_ACCOUNT_SID/AUTH_TOKEN` | provider creds |
| `TWILIO_SMS_FROM` / `TWILIO_WHATSAPP_FROM` | sender numbers |
| `DEV_NOTIFY_FAIL` | force failures (test retries/dlq path) |

## Runbook (start / resume)

- Current: `docker compose up -d worker` (task `notify.*` routed to the
  `notify` queue).
- Force a test alarm: seed an ingest message with scenario `warning`
  (MockVLM raises severity) → decision → WARNING → check
  `notification_deliveries` rows are `awaiting_approval` (nothing sent yet).
- Approve in triage UI (or `POST .../approve-notify`) → worker sends → status
  `sent`.
- Replay a failed delivery: fix cause → set status back to `pending` →
  `celery call notify.notify_warning` with the decision id.
- Tests: `apps/api/tests/test_notifier.py`, triage approve/dismiss coverage in
  `test_triage_api.py`.

## Open decisions

- Fan-out policy: notify per config row vs per recipient group.
- Webhook signing format (HMAC-SHA256 over timestamp+body recommended).
- Do providers live inside this service, or does a bare "alerter" emit events
  and channels subscribe (event-transport reuse)?
