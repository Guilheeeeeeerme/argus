# Service sketch: notifications

> Status: **PARTIALLY IMPLEMENTED** inside `apps/api` (config CRUD +
> `notify` worker in log mode). Extraction + channel expansion are pending.
> This document is the handoff. Related: `decision-engine.md`.

## Purpose

Configure and deliver alarms raised by the decision engine: per-company
notification configs (channels + recipients), delivery attempts with status
tracking, and dedup so one decision alarms once.

## What exists today

| Piece | State | File |
|---|---|---|
| `notification_configs` CRUD (channel, recipient, is_active) | Implemented, routes `/v1/companies/{company_id}/notifications`, manager+ roles | `api/admin/notifications.py` |
| `notification_deliveries` (decision_id, channel, status, provider_message_id, error_detail) | Implemented (model + API read) | migration `005_operational` |
| Twilio client (SMS/WhatsApp) | Implemented, behind `NOTIFICATION_MODE=log` | `integrations/twilio_client.py` |
| `notify_warning` task | Implemented — reads decision + config, "sends" (log), writes a delivery row | `workers/notifier.py`, `workers/notify.py` |
| Delivery lifecycle pending→sent→delivered→failed | Modeled; only `sent` (log) is produced in dev | `domain/enums.py` |

## Responsibilities (to build / extract)

1. **Per-decision dedup** — one delivery per (decision, config). Today the
   aggregator calls `notify_warning` on every transition into WARNING; ensure
   idempotency via unique `(decision_id, config_id)` before re-enqueueing.
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
- Trigger: `notify_warning.delay(decision_id)` (from decision engine) — keep
  the Celery task name stable during extraction.
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
  `notification_deliveries` rows + worker logs.
- Replay a failed delivery: fix cause → `celery call notify.deliver` with the
  delivery id (or re-run `notify_warning`).
- Tests: `apps/api/tests/test_notifier.py`.

## Open decisions

- Fan-out policy: notify per config row vs per recipient group.
- Webhook signing format (HMAC-SHA256 over timestamp+body recommended).
- Do providers live inside this service, or does a bare "alerter" emit events
  and channels subscribe (event-transport reuse)?
