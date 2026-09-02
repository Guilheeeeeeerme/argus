# Quickstart: ARGUS SaaS MVP Validation

**Feature**: `001-saas-mvp` | **Date**: 2026-09-01

Runnable validation scenarios proving the MVP works end-to-end. Implementation
details belong in `tasks.md`; this guide defines acceptance validation only.

## Prerequisites

- Docker Compose (PostgreSQL 16, Redis 7, MinIO, all backend services)
- Auth0 tenant configured with custom claims (`tenant_id`, `role`)
- OpenAI API key (`OPENAI_API_KEY`)
- Twilio account with SMS/WhatsApp sandbox (`TWILIO_*` env vars)
- `specs/001-saas-mvp/contracts/` available for request/response shapes
- `specs/001-saas-mvp/data-model.md` for entity reference

### Environment Setup

```bash
cd backend
cp .env.example .env
# Fill: DATABASE_URL, REDIS_URL, S3_ENDPOINT, AUTH0_DOMAIN,
#       AUTH0_API_AUDIENCE, OPENAI_API_KEY, TWILIO_*

docker compose -f docker/docker-compose.yml up -d
alembic upgrade head
python scripts/seed_dev.py
```

### Seed Data Created

- Tenant: `acme-security` (UUID in seed output)
- Market: `Downtown Market`
- Camera: `Entrance Cam 1` with 1 region of interest
- Context Mode: `Night Shift` with Lens + 2 rules
- Notification config: test phone number
- Users: root_admin, tenant_admin, watcher (Auth0 subjects in seed output)

---

## Scenario 1: Multi-Tenant Isolation (US1, SC-002)

**Proves**: FR-001–004, Constitution Principle I

```bash
# As Tenant A admin — should succeed
curl -s -H "Authorization: Bearer $TOKEN_TENANT_A" \
  "$API/admin/tenants/$TENANT_A_ID/markets" | jq .

# As Tenant A admin — access Tenant B — should 403
curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer $TOKEN_TENANT_A" \
  "$API/admin/tenants/$TENANT_B_ID/markets"
# Expected: 403
```

**Pass criteria**: Tenant A token returns 200 for own tenant, 403 for Tenant B.
Zero cross-tenant data in response bodies.

---

## Scenario 2: Context Mode Scheduling (US2)

**Proves**: FR-005–009

```bash
# Create schedule: Night Shift active Mon-Fri 22:00-06:00
curl -s -X POST -H "Authorization: Bearer $TOKEN_TENANT_ADMIN" \
  -H "Content-Type: application/json" \
  "$API/tenants/$TENANT_ID/context-modes/$MODE_ID/schedules" \
  -d '{"day_of_week":"mon","start_time":"22:00:00","end_time":"06:00:00"}'

# Verify active mode (after scheduler tick or manual trigger)
redis-cli GET "camera:active_mode:$CAMERA_ID"
# Expected: Night Shift mode UUID
```

**Pass criteria**: Scheduled mode activates without manual intervention; audit log
records transition.

---

## Scenario 3: Edge Ingestion → Evidence (US3)

**Proves**: FR-011–012, FR-015, Constitution Principle IV

```bash
# Submit suspicious sequence (M2M token)
curl -s -X POST -H "Authorization: Bearer $TOKEN_EDGE_M2M" \
  -H "Content-Type: application/json" \
  "$INGEST/v1/ingest/sequences" \
  -d @tests/fixtures/sample_ingest_payload.json
# Expected: 202 {"status":"queued","ingestion_id":"..."}

# Wait for VLM worker (≤30s)
# Verify evidence created
psql $DATABASE_URL -c \
  "SELECT id, severity_score, context_mode_id FROM evidences \
   WHERE ingestion_id = '$INGESTION_ID';"
```

**Pass criteria**: 202 returned in < 100ms; Evidence row created with correct
`context_mode_id` and `captured_at`; frames stored in S3.

---

## Scenario 4: Evidence Aggregation → Decision States (US3, US4)

**Proves**: FR-014, FR-016–017, FR-019

```bash
# Submit 3 ingestions within 5-minute window (same camera/region)
for i in 1 2 3; do
  curl -s -X POST ... -d @tests/fixtures/sample_ingest_payload_$i.json
  sleep 2
done

# Check single Decision with 3 evidences
psql $DATABASE_URL -c \
  "SELECT d.id, d.state, d.evidence_count, d.cumulative_severity \
   FROM decisions d \
   JOIN decision_evidences de ON de.decision_id = d.id \
   WHERE d.camera_id = '$CAMERA_ID' \
   GROUP BY d.id;"
# Expected: 1 decision, state >= 'weird', evidence_count = 3
```

**Pass criteria**: Multiple evidences grouped into one Decision; state escalates
normal → weird → warning as thresholds crossed.

---

## Scenario 5: Real-Time Triage WebSocket (US4, SC-003)

**Proves**: FR-018–021, FR-020

```bash
# Terminal 1: Connect Watcher WebSocket
websocat "wss://localhost:8002/v1/ws?token=$TOKEN_WATCHER"

# Terminal 2: Trigger ingestion that crosses warning threshold
curl -s -X POST ... -d @tests/fixtures/high_severity_payload.json

# Terminal 1 should receive within 5 seconds:
# {"type":"decision.state_changed","payload":{"current_state":"warning",...}}
```

**Pass criteria**: WS message received < 5s; no manual page refresh needed;
10 concurrent websocat connections all receive same state change.

---

## Scenario 6: Watcher Resolution & Feedback (US5, SC-006)

**Proves**: FR-022–026, Constitution Principles VII & VIII

```bash
curl -s -X POST -H "Authorization: Bearer $TOKEN_WATCHER" \
  -H "Content-Type: application/json" \
  "$API/tenants/$TENANT_ID/decisions/$DECISION_ID/resolve" \
  -d '{"disposition":"false_positive","reasoning":"Reflection on glass, not a person"}'
# Expected: 200

# Verify immutable audit trail
psql $DATABASE_URL -c \
  "SELECT event_type, payload FROM audit_records \
   WHERE decision_id = '$DECISION_ID' ORDER BY created_at;"
# Expected: state_change events + resolved event with watcher sub

# Concurrent resolve should 409
curl -s -o /dev/null -w "%{http_code}" -X POST ... (same decision)
# Expected: 409
```

**Pass criteria**: Feedback permanently linked; audit trail complete; concurrent
resolve returns 409.

---

## Scenario 7: Async Notifications (US6, SC-007)

**Proves**: FR-027–030, Constitution Principle VI

```bash
# Trigger Warning Decision (Scenario 4 with high severity)
# Check notification delivery (async, may take seconds)
psql $DATABASE_URL -c \
  "SELECT status, channel, provider_message_id FROM notification_deliveries \
   WHERE decision_id = '$DECISION_ID';"
# Expected: status = 'sent' or 'delivered'

# Simulate Twilio failure (set invalid TWILIO_AUTH_TOKEN, restart worker-notify)
# Trigger another Warning — triage must still work
curl -s -X POST ... resolve endpoint
# Expected: 200 (triage unaffected)

psql $DATABASE_URL -c \
  "SELECT status, error_detail FROM notification_deliveries \
   WHERE decision_id = '$DECISION_ID_2';"
# Expected: status = 'failed', decision.state still = 'warning'
```

**Pass criteria**: Notification dispatched on Warning; failure does not block
triage resolve; delivery status independent from Decision state.

---

## Scenario 8: Out-of-Order Ingestion (US3 edge case)

**Proves**: FR-015, SC-005

```bash
# Submit evidence with captured_at T+3min, then T+1min (out of order)
curl -s -X POST ... -d '{"captured_at":"2026-09-01T10:03:00Z",...}'
curl -s -X POST ... -d '{"captured_at":"2026-09-01T10:01:00Z",...}'

psql $DATABASE_URL -c \
  "SELECT COUNT(*) FROM decision_evidences WHERE decision_id = '$DECISION_ID';"
# Expected: 2 (both linked, none dropped)
```

**Pass criteria**: 95%+ out-of-order evidences correctly grouped (SC-005).

---

## Full Pipeline Smoke Test

Run scenarios 1 → 7 sequentially. Total expected time: < 15 minutes.

| Step | Scenario | Key Metric |
|------|----------|------------|
| 1 | Tenant isolation | 403 on cross-tenant |
| 2 | Context scheduling | Active mode in Redis |
| 3 | Ingestion | 202 < 100ms |
| 4 | Aggregation | 1 Decision, N evidences |
| 5 | WebSocket | State change < 5s |
| 6 | Resolution | Audit trail complete |
| 7 | Notifications | Async, non-blocking |

All scenarios passing = MVP validation complete. Proceed to `/speckit-tasks`.
