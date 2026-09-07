# ARGUS — Product Specification (distilled)

Distilled from the original `001-saas-mvp` spec-kit artifacts (deleted during the
monorepo flatten). Product intent only; implementation details live in the code
and the root README.

## What ARGUS is

Multi-tenant SaaS surveillance platform. Cameras at physical locations stream
through a media gateway; the stream is broken down into **temporary frame
images**; an AI pipeline produces **Detections** (what + how sure); rules bound
to detection classes fire **alarms** when confidence clears their threshold;
operators triage the resulting Decisions and their feedback improves detection
quality.

Every concept is named generically — the MVP instantiates locations as
"markets", but the model extends to any monitored site.

## Roles

| Role | Scope | Interface | Can switch company/location? |
|------|-------|-----------|-------------------------------|
| `root` | Platform (us) | Admin (:8180) | Yes; creates companies + users |
| `admin` | Platform (customer + support team) | Admin (:8180) | Yes; creates companies + users |
| `manager` | One company | Admin (:8180) | No (manages their company) |
| `operator` | One company | Triage (:8181) | No (triage; can edit rules) |

Everyone can edit rules — authoring is part of every role's workflow.

## Conceptual flow

1. An **Agent** (edge device, N:N with Locations) captures activity.
2. Irrelevant content is discarded locally; suspicious sequences are ingested.
3. The stream is broken into **temporary frame images** (object storage, TTL).
4. The **Recipe** (AI analysis profile of a RuleSet) analyzes frames and emits
   **Detections**: `{ detection_class, confidence, description }`.
5. **Rules** bind to detections: a rule matches when
   `rule.detection_class == detection.class` (or rule class is null = any) **and**
   `detection.confidence >= rule.confidence_threshold` — plus its drawn regions
   and condition.
6. Matched rules raise the alarm: Evidence accumulates into a **Decision**;
   state transitions (weird/warning) notify and stream to triage live.
7. Operators review Decisions, resolve, and provide feedback (RAG for future
   analysis).

## Core entities

- **Company** — the client (RLS-enforced). Multiple Locations, Agents, Users.
- **Location** — physical place (MVP: a market). Has an `address`, a
  **sketch** (floor plan image/SVG) with camera placements `{x, y}`.
- **Agent** — edge device (`device_id` for M2M auth). **N:N** with Locations
  via `agent_locations`.
- **Camera** — belongs to a Location. Stores **industry-standard stream
  config** (RTSP URL + credentials, ONVIF later); media access is abstracted by
  the standalone **stream-gateway** microservice (go2rtc), which syncs camera
  configs from the API over an internal token-protected route.
- **RuleSet** — schedulable **group of rules** ("shifts"): `RuleSetSchedule`
  rows (day-of-week + time window, per location) + per-camera assignment.
- **Rule** — decision rule: `detection_class` + `confidence_threshold` binding,
  drawn regions (RegionOfInterest), condition, severity weight.
- **Recipe** — the AI analysis profile (system prompt + output schema, versioned)
  attached to a RuleSet.
- **Evidence / Decision / Feedback** — operational pipeline records. Evidence
  carries `detection_class` + `confidence` extracted from the VLM result.

## Auth model (dev)

- Users: opaque Redis sessions, Bearer tokens, `POST /v1/auth/login` →
  `/v1/auth/me` → `PATCH /v1/auth/context` (platform roles only; sets
  `activeCompanyId` + `activeLocationId`).
- SSO: admin app hosts login + `/sso/handoff`; MFEs receive `#token=` via
  origin-allowlisted return URLs (`SSO_RETURN_ORIGINS`).
- Agents (devices): M2M client-credentials JWTs (mock HS256 locally,
  `AUTH0_USE_MOCK=true`).
- Isolation: PostgreSQL RLS — `app.current_role IN ('root','admin')` bypasses;
  tenant roles are scoped to the Redis session's `activeCompanyId`.

## Non-goals (MVP)

- No production IdP integration (Auth0 scaffold exists behind the mock flag).
- No TLS/edge gateway - development only, plain HTTP with browser-facing test hostnames.
- No per-service deployables — single compose project, hot reload.
