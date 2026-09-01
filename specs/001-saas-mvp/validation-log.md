# Validation Log: ARGUS SaaS MVP

**Feature**: `001-saas-mvp` | **Date**: 2026-09-01

## Automated test suite

```bash
cd backend
PYTHONPATH=src AUTH0_USE_MOCK=true AUTH0_DOMAIN=dev.argus.local \
  .venv/bin/python -m pytest tests/ -q
```

**Result**: 25 passed (2026-09-01)

| Area | Tests |
|------|-------|
| Auth JWT / RBAC | `test_auth_jwt.py` |
| Ingest pipeline | `test_ingest.py` |
| VLM / aggregator / scheduler workers | `test_workers.py`, `test_lens_builder.py`, `test_openai_vlm.py` |
| Admin API (tenants, markets, cross-tenant guard) | `test_admin_api.py` |
| Triage (decisions list, resolve + feedback) | `test_triage_api.py` |
| WebSocket gateway (auth, connection limit) | `test_ws_gateway.py` |
| Notification worker (Twilio mock) | `test_notifier.py` |

## Quickstart scenarios

| # | Scenario | Status | Notes |
|---|----------|--------|-------|
| 1 | Multi-tenant isolation | PASS | `test_cross_tenant_access_denied`, `test_tenant_admin_cannot_create_tenant` |
| 2 | Context mode scheduling | PASS | `test_workers.py` scheduler activation |
| 3 | Edge ingest → VLM | PASS | `test_ingest.py`, `test_workers.py` |
| 4 | Evidence aggregation / state machine | PASS | `test_workers.py` aggregator |
| 5 | WebSocket triage | PASS | `test_ws_gateway.py` JWT handshake + connection limit |
| 6 | Watcher resolve + feedback RAG | PASS | `test_resolve_decision_writes_feedback` |
| 7 | Twilio notifications | PASS | `test_notify_warning_creates_delivery` (mock Twilio) |
| 8 | Full pipeline E2E | PARTIAL | Covered by unit/integration tests; manual docker-compose E2E not run in CI |

## Remediation

- Scenario 8 full docker-compose walkthrough: run `quickstart.md` curl/websocat steps against local stack when integrating frontend.
