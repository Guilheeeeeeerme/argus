# WebSocket Contract: Triage Real-Time Feed

**Feature**: `001-saas-mvp` | **Version**: 1.0.0

Dedicated WebSocket Gateway (`ws-gateway` service) for the Triage SPA. Separate
origin and deployable from Admin API per Constitution Principle III.

## Connection

```
wss://triage.argus.example.com/v1/ws?token=<JWT>
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `token` | Yes | Auth0 JWT (RS256); query param for browser WebSocket limitation |

Alternative: `Sec-WebSocket-Protocol: bearer,<JWT>` header if SPA supports it.

## Authentication & Authorization

1. Gateway validates JWT signature against Auth0 JWKS (`/.well-known/jwks.json`).
2. Required claims:

| Claim | Type | Description |
|-------|------|-------------|
| `sub` | string | IdP subject (Watcher identity) |
| `tenant_id` | uuid | Tenant scope |
| `role` | string | Must be `watcher` or `tenant_admin` |
| `exp` | int | Expiry |

3. On success, connection auto-joins room `triage:{tenant_id}`.
4. On failure, connection closed with code `4001` (unauthorized) or `4003` (forbidden).

Watchers with `tenant_admin` role MAY connect for monitoring but MUST NOT resolve
Decisions via WS (resolve via REST only if role permits).

## Server → Client Messages

All messages are JSON text frames with envelope:

```json
{
  "type": "<event_type>",
  "tenant_id": "<uuid>",
  "timestamp": "2026-09-01T15:30:00.000Z",
  "payload": { }
}
```

### `decision.state_changed`

Emitted when a Decision transitions state.

```json
{
  "type": "decision.state_changed",
  "tenant_id": "a1b2c3d4-...",
  "timestamp": "2026-09-01T15:30:00.000Z",
  "payload": {
    "decision_id": "d1e2f3a4-...",
    "camera_id": "c1a2b3d4-...",
    "region_id": "r1a2b3d4-...",
    "previous_state": "weird",
    "current_state": "warning",
    "cumulative_severity": 7,
    "evidence_count": 4,
    "market_name": "Downtown Market",
    "camera_name": "Entrance Cam 1"
  }
}
```

### `decision.evidence_added`

Emitted when a new Evidence links to an existing Decision.

```json
{
  "type": "decision.evidence_added",
  "tenant_id": "a1b2c3d4-...",
  "timestamp": "2026-09-01T15:30:00.000Z",
  "payload": {
    "decision_id": "d1e2f3a4-...",
    "evidence_id": "e1f2a3b4-...",
    "severity_score": 2,
    "captured_at": "2026-09-01T15:29:55.000Z",
    "vlm_summary": "Person loitering near restricted area"
  }
}
```

### `decision.resolved`

Emitted when a Watcher resolves a Decision (broadcast to all connected clients).

```json
{
  "type": "decision.resolved",
  "tenant_id": "a1b2c3d4-...",
  "timestamp": "2026-09-01T15:35:00.000Z",
  "payload": {
    "decision_id": "d1e2f3a4-...",
    "state": "resolved_false_positive",
    "resolved_by": "auth0|watcher123",
    "resolved_at": "2026-09-01T15:35:00.000Z"
  }
}
```

### `heartbeat`

Server ping every 30 seconds.

```json
{
  "type": "heartbeat",
  "tenant_id": "a1b2c3d4-...",
  "timestamp": "2026-09-01T15:30:00.000Z",
  "payload": {}
}
```

Client MUST respond with:

```json
{ "type": "pong" }
```

## Client → Server Messages

### `subscribe` (optional explicit)

Auto-subscribed on connect; use only for re-subscribe after error.

```json
{
  "type": "subscribe",
  "payload": {
    "tenant_id": "a1b2c3d4-..."
  }
}
```

Server validates `tenant_id` matches JWT claim; mismatch → close `4003`.

### `pong`

Response to `heartbeat`.

## Internal Pub/Sub Flow

```text
worker-aggregator / worker-vlm
        │
        ▼
  Redis PUBLISH ws:room:{tenant_id} <json envelope>
        │
        ▼
  ws-gateway (all instances subscribed)
        │
        ▼
  Connected WebSocket clients in room
```

Gateway maintains in-memory map: `tenant_id → Set[WebSocket]`.
Redis adapter enables horizontal scaling across gateway replicas.

## Connection Lifecycle

| Code | Meaning |
|------|---------|
| 1000 | Normal close |
| 4001 | Invalid/expired token |
| 4003 | Tenant mismatch or insufficient role |
| 4008 | Policy violation (e.g., rate limit) |

## Rate Limits

- Max 5 connections per `sub` per tenant (prevents tab flooding).
- Max 100 messages/sec inbound per connection (pong only expected).

## Latency Target

Decision state changes MUST reach connected Watchers within 5 seconds of Evidence
processing (SC-003). Measured: aggregator publish → WS client receive.
