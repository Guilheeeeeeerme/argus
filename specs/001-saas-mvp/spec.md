# Feature Specification: ARGUS SaaS MVP

**Feature Branch**: `001-saas-mvp`

**Created**: 2026-09-01

**Status**: Draft

**Input**: User description: "Generate the product specification for the ARGUS SaaS MVP. Detail what the system does and why, without dictating technical implementations, database schemas, or communication protocols."

## Overview

ARGUS is a multi-tenant SaaS surveillance platform that transforms distributed camera
activity into actionable security Decisions. Edge environments discard irrelevant
footage locally; the cloud applies contextual behavioral analysis; human Watchers
triage outcomes in real time; structured feedback continuously improves detection
quality.

This specification defines the minimum viable product (MVP) required to deliver
that end-to-end loop for multiple isolated organizations.

### Personas

| Persona | Role | Primary Interface |
|---------|------|-------------------|
| **Root Admin** | Manages overarching tenant accounts and assigns Tenant Admins | Admin Dashboard |
| **Tenant Admin** | Configures markets, cameras, context modes, and notification routing for one organization | Admin Dashboard |
| **Watcher** | Monitors real-time triage, reviews Decisions, provides feedback | Triage SPA |

### Conceptual Flow

1. Activity is captured at the edge.
2. Irrelevant content is discarded locally.
3. Suspicious sequences undergo contextual analysis based on active Context Modes
   (e.g., Night Shift, Public Market).
4. Triggers are aggregated into distinct Evidences.
5. Related Evidences within a time window are grouped into a single Decision.
6. Decisions are transmitted to the Triage interface.
7. Human Watchers review each Decision, take action, and provide feedback.

### Decision Lifecycle States

| State | Meaning |
|-------|---------|
| **Normal** | Baseline monitoring; no triggers active for this scope |
| **Weird** | Evidences are accumulating but have not breached the alert threshold |
| **Warning** | Threshold breached; requires immediate Watcher action |
| **Resolved (True Positive)** | Watcher confirmed a genuine threat or anomaly |
| **Resolved (False Positive)** | Watcher determined the alert was not a genuine threat |

### Scope Boundaries

**In scope for MVP**: Multi-tenant hierarchy mapping, SSO integration, context mode
configuration, edge event ingestion, AI contextual analysis, evidence aggregation,
real-time triage monitoring, human feedback loop, and external notifications.

**Out of scope for MVP**: Billing/invoicing, hardware provisioning, biometric
identification, custom model training, and custom reporting dashboards.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Multi-Tenant Setup (Priority: P1)

As a **Root Admin**, I want to create tenants and assign Tenant Admins so that
multiple organizations can use the system securely and in isolation.

**Why this priority**: Without tenant isolation and role assignment, no other
capability can be offered safely to multiple customers. This is the trust
foundation of the platform.

**Independent Test**: Create two tenants with distinct Tenant Admins; verify each
admin sees only their organization's data after SSO login. Delivers provable
multi-tenant security before any surveillance workflow is enabled.

**Acceptance Scenarios**:

1. **Given** a Root Admin with platform-level access, **When** they create a new
   tenant and assign a Tenant Admin, **Then** the Tenant Admin can authenticate
   via SSO and access only that tenant's configuration and operational data.
2. **Given** a Tenant Admin authenticated for Tenant A, **When** they attempt to
   view or modify any resource belonging to Tenant B, **Then** access is denied
   and no cross-tenant data is exposed.
3. **Given** a Watcher assigned to a tenant, **When** they authenticate via SSO,
   **Then** they can access the Triage interface for that tenant only and cannot
   reach Admin Dashboard configuration functions beyond their role.

---

### User Story 2 - Context & Rule Configuration (Priority: P2)

As a **Tenant Admin**, I want to define Markets, Cameras, and Context Modes so
that the system applies the correct behavioral rules based on time or location.

**Why this priority**: Context-aware rules are what differentiate meaningful
detection from generic motion alerts. Configuration must exist before edge events
can be evaluated meaningfully.

**Independent Test**: Configure a Market with cameras, regions of interest, and a
scheduled Context Mode; verify the active mode switches at the scheduled time.
Delivers tenant-specific behavioral policy without requiring live edge events.

**Acceptance Scenarios**:

1. **Given** a Tenant Admin and an existing Market, **When** they register a
   Camera and define one or more regions of interest on that camera's view,
   **Then** behavioral rules can be explicitly mapped to those regions.
2. **Given** a Context Mode with an associated schedule, **When** the scheduled
   activation time arrives, **Then** that mode becomes the active evaluation
   context for the cameras and regions it covers without manual intervention.
3. **Given** multiple Context Modes with non-overlapping schedules for the same
   camera, **When** schedules transition, **Then** exactly one mode is active per
   camera at any point in time and the transition is recorded for audit.

---

### User Story 3 - Ingestion & Aggregation (Priority: P2)

As the **System**, I need to receive filtered edge sequences, evaluate them
against active context rules, and aggregate multiple triggers into a single
Decision to prevent operator alert fatigue.

**Why this priority**: The core value proposition — turning raw edge triggers
into a manageable stream of Decisions — depends on reliable ingestion and
intelligent grouping.

**Independent Test**: Submit a series of edge triggers within a configured time
window for the same scope; verify they produce one Decision with multiple linked
Evidences. Delivers the aggregation behavior that makes triage operable.

**Acceptance Scenarios**:

1. **Given** multiple Evidences from the same camera or correlated scope within
   a tenant-configured aggregation time window, **When** the system processes
   them, **Then** they are grouped into a single Decision entity rather than
   generating separate alerts for each trigger.
2. **Given** edge events arriving out of chronological order, **When** the
   system ingests them, **Then** all valid Evidences are retained and correctly
   associated with the appropriate Decision without data loss.
3. **Given** Evidences evaluated under an active Context Mode, **When** a
   Decision is created or updated, **Then** the Decision records which Context
   Mode was active at the time of each Evidence capture.
4. **Given** only locally filtered suspicious sequences are transmitted from
   edge, **When** irrelevant activity occurs, **Then** no Evidence or Decision
   is created for that activity.

---

### User Story 4 - Real-Time Triage Interface (Priority: P1)

As a **Watcher**, I want a dedicated monitoring interface to see Decisions
transition through states in real time so I can react to threats immediately.

**Why this priority**: Real-time human triage is the operational heart of ARGUS.
Without it, aggregated Decisions have no path to resolution.

**Independent Test**: Simulate escalating Evidences for a tenant; verify a
Watcher sees the Decision move from Normal through Weird to Warning without
manual page refresh. Delivers the primary operator workflow.

**Acceptance Scenarios**:

1. **Given** a Watcher viewing the Triage interface for their tenant, **When**
   Evidences accumulate below the alert threshold, **Then** the affected
   Decision visually escalates from Normal to Weird.
2. **Given** a Decision whose Evidences breach the alert threshold, **When**
   the threshold is crossed, **Then** the Decision transitions to Warning and is
   prominently surfaced for immediate Watcher attention.
3. **Given** an active Triage session, **When** new Decision state changes
   occur, **Then** the interface updates automatically without requiring manual
   refresh.
4. **Given** the Admin Dashboard and Triage SPA, **When** a Watcher performs
   triage, **Then** they use the Triage SPA exclusively — configuration changes
   are not available in that interface.

---

### User Story 5 - Feedback & Continuous Learning (Priority: P2)

As a **Watcher**, I want to resolve a Decision (True Positive, False Positive,
or False Negative) and provide written reasoning so the system learns from its
mistakes.

**Why this priority**: Structured human feedback closes the improvement loop
required by platform governance and ensures detection quality improves over time.

**Independent Test**: Resolve a Warning Decision with a disposition and written
reasoning; verify the resolution is permanently linked and stored in a structured
form. Delivers accountable triage outcomes and learning-ready data.

**Acceptance Scenarios**:

1. **Given** a Decision in Warning state, **When** a Watcher resolves it as True
   Positive or False Positive and submits written reasoning, **Then** the
   resolution state and reasoning are permanently and immutably linked to that
   Decision.
2. **Given** a Watcher identifies a missed threat (False Negative), **When**
   they record that disposition with written reasoning, **Then** the feedback is
   stored in a structured format suitable for informing future contextual
   analysis.
3. **Given** a resolved Decision, **When** an auditor reviews its history,
   **Then** they can trace the final disposition back to the contributing
   Evidences, the reviewing Watcher, and the Context Mode active at capture
   time.

---

### User Story 6 - External Notifications (Priority: P3)

As a **Tenant Admin**, I want to configure the system to send high-severity
Decisions to external SMS/WhatsApp numbers so off-site security personnel are
alerted.

**Why this priority**: Off-site alerting extends reach beyond active Watchers but
is secondary to the core triage workflow; delivery must never compromise it.

**Independent Test**: Configure notification recipients; trigger a Warning
Decision; verify notification dispatch while confirming the Triage interface
remains responsive even if delivery fails. Delivers async alerting without
pipeline coupling.

**Acceptance Scenarios**:

1. **Given** a Tenant Admin has configured SMS and/or WhatsApp recipients for
   high-severity alerts, **When** a Decision transitions to Warning, **Then**
   notifications are dispatched asynchronously to the configured recipients.
2. **Given** an external notification delivery failure or delay, **When** the
   failure occurs, **Then** the Triage interface continues to operate normally
   and the Decision remains available for Watcher action without stall or crash.
3. **Given** a resolved Decision, **When** notification delivery status is
   reviewed, **Then** delivery outcome is tracked independently from the
   Decision lifecycle state.

---

### Edge Cases

- What happens when two Watchers attempt to resolve the same Warning Decision
  concurrently? The system must prevent conflicting resolutions and inform the
  second Watcher that the Decision has already been resolved.
- What happens when a Context Mode schedule changes while Evidences are
  accumulating? Each Evidence must retain the mode that was active at its capture
  time; the Decision must not retroactively change historical context attribution.
- What happens when edge connectivity is intermittent? Valid Evidences received
  after a delay must still aggregate into the correct Decision window where
  timestamps fall within the configured aggregation period.
- What happens when no Watcher is actively viewing the Triage interface? Decisions
  must still progress through states and remain available when a Watcher connects;
  Warning Decisions must still trigger configured external notifications.
- What happens when a Tenant Admin is removed or reassigned mid-session? Active
  SSO sessions must be re-evaluated on the next authorization check; removed admins
  must lose configuration access immediately upon token refresh or session end.
- What happens when notification recipients are misconfigured or unreachable?
  Failures must be logged and visible to Tenant Admins without affecting triage
  throughput or Decision state progression.
- What happens when a camera has no active Context Mode assigned? The system must
  reject or quarantine edge events from that camera with a clear administrative
  indicator rather than applying default rules silently.

## Requirements *(mandatory)*

### Functional Requirements

**Tenant & Identity**

- **FR-001**: System MUST support a multi-tenant hierarchy with at minimum Root
  Admin, Tenant Admin, and Watcher roles scoped to individual tenants.
- **FR-002**: System MUST authenticate all users exclusively through an external
  SSO/IdP; local password storage and processing MUST NOT occur.
- **FR-003**: System MUST enforce that Tenant Admins and Watchers can only view
  and mutate data belonging to their assigned organization, as determined by
  SSO-issued identity claims.
- **FR-004**: Root Admin MUST be able to create tenants and assign Tenant Admins
  to those tenants.

**Configuration (Admin Dashboard)**

- **FR-005**: Tenant Admin MUST be able to define Markets as organizational
  groupings of surveillance scope.
- **FR-006**: Tenant Admin MUST be able to register Cameras within Markets.
- **FR-007**: Tenant Admin MUST be able to define regions of interest on a
  Camera and map behavioral rules explicitly to those regions.
- **FR-008**: Tenant Admin MUST be able to create Context Modes (e.g., Night
  Shift, Public Market) with associated behavioral rules.
- **FR-009**: Context Modes MUST support scheduled automatic activation and
  deactivation.
- **FR-010**: Admin Dashboard MUST be logically separate from the Triage SPA;
  configuration mutations MUST NOT be executable from the Triage interface.

**Ingestion, Analysis & Aggregation**

- **FR-011**: System MUST accept only pre-filtered suspicious sequences from edge
  environments; irrelevant content discarded at edge MUST NOT be ingested.
- **FR-012**: System MUST evaluate ingested sequences against the active Context
  Mode and applicable region rules for the originating Camera.
- **FR-013**: System MUST NOT perform facial recognition, store facial
  embeddings, or process any biometric data.
- **FR-014**: System MUST aggregate related Evidences occurring within a
  tenant-configurable time window into a single Decision entity.
- **FR-015**: System MUST handle out-of-order edge ingestion without dropping
  valid Evidences.
- **FR-016**: Each Decision MUST progress through lifecycle states: Normal,
  Weird, Warning, and Resolved (True Positive or False Positive).
- **FR-017**: Each Evidence and Decision MUST record the Context Mode active at
  time of capture.

**Triage (Triage SPA)**

- **FR-018**: Watcher MUST have a dedicated Triage interface showing Decisions
  and their current lifecycle state for their assigned tenant.
- **FR-019**: Triage interface MUST visually escalate Decisions from Normal to
  Weird to Warning as Evidence severity increases.
- **FR-020**: Triage interface MUST update Decision states in real time without
  manual refresh.
- **FR-021**: Multiple concurrent Watchers viewing the same tenant's triage feed
  MUST NOT cause state conflicts or inconsistent views of unresolved Decisions.
- **FR-022**: Watcher MUST be able to resolve a Warning Decision as True
  Positive, False Positive, or False Negative.

**Feedback & Traceability**

- **FR-023**: Watcher MUST provide written reasoning when resolving False
  Positive or False Negative dispositions.
- **FR-024**: Resolution state and human reasoning MUST be permanently and
  immutably linked to the originating Decision.
- **FR-025**: Feedback data MUST be stored in a structured, tenant-scoped form
  suitable for informing future contextual analysis.
- **FR-026**: Every Decision MUST maintain an audit trail linking final state
  to contributing Evidences, the reviewing Watcher, and Context Mode at capture.

**Notifications**

- **FR-027**: Tenant Admin MUST be able to configure external notification
  recipients (SMS and/or WhatsApp) for high-severity Decisions.
- **FR-028**: System MUST dispatch notifications asynchronously when a Decision
  enters Warning state.
- **FR-029**: Notification delivery failure or latency MUST NOT block, delay, or
  degrade the evidence evaluation or triage pipeline.
- **FR-030**: Notification delivery status MUST be tracked independently from
  Decision lifecycle state.

### Key Entities

- **Tenant**: An isolated organization using ARGUS; owns all configuration,
  events, and user assignments beneath it.
- **Market**: A tenant-scoped grouping representing a physical or logical
  surveillance area (e.g., a retail location, warehouse zone).
- **Camera**: A registered video source within a Market; associated with edge
  filtering and cloud ingestion.
- **Region of Interest**: A defined area within a Camera's field of view to
  which specific behavioral rules apply.
- **Context Mode**: A named set of behavioral rules and thresholds (e.g., Night
  Shift, Public Market) activatable manually or on schedule.
- **Evidence**: A single AI-evaluated suspicious trigger derived from an edge
  sequence, linked to a Camera, region, Context Mode, and timestamp.
- **Decision**: An aggregated unit comprising one or more related Evidences
  within a time window; carries a lifecycle state and resolution outcome.
- **Watcher Feedback**: Structured disposition (True Positive, False Positive,
  False Negative) and optional written reasoning permanently linked to a
  Decision.
- **Notification Configuration**: Tenant-scoped recipient list and severity
  rules for external alerting channels.
- **Audit Record**: Immutable append-only record linking Decision outcomes to
  Evidences, reviewers, and active Context Modes.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Root Admin can onboard a new tenant with an assigned Tenant Admin
  in under 10 minutes end-to-end (tenant creation through first successful SSO
  login).
- **SC-002**: 100% of authorization test cases confirm zero cross-tenant data
  exposure across Root Admin, Tenant Admin, and Watcher roles.
- **SC-003**: Watchers observe Decision state changes (Normal → Weird → Warning)
  in the Triage interface within 5 seconds of the triggering Evidence being
  processed, under normal operating conditions.
- **SC-004**: At least 10 concurrent Watchers viewing the same tenant's triage
  feed receive consistent Decision states with no resolution conflicts.
- **SC-005**: 95% of Evidences arriving out of order within the aggregation
  window are correctly grouped into the intended Decision without loss.
- **SC-006**: 100% of resolved Decisions retain a permanent, retrievable link
  to their contributing Evidences, reviewing Watcher, and capture-time Context
  Mode.
- **SC-007**: When external notification delivery fails, 100% of Triage
  interface operations (view, escalate, resolve) remain available without
  measurable degradation to Watcher task completion time.
- **SC-008**: Tenant Admins can configure a Market, Camera, region of interest,
  and scheduled Context Mode without assistance in under 30 minutes on first use.
- **SC-009**: Watchers resolve 90% of Warning Decisions with disposition and
  required reasoning on the first attempt without workflow errors.

## Assumptions

- Organizations using ARGUS MVP already operate compatible edge devices capable
  of local frame filtering; hardware provisioning is out of scope.
- A single external SSO/IdP is available at MVP launch; multi-IdP federation is
  not required for the initial release.
- Default evidence aggregation time window is 5 minutes per Decision scope,
  tenant-configurable within reasonable bounds (1–30 minutes).
- "Minimal observable latency" for triage updates is defined as within 5 seconds
  under normal load; formal SLA tiers are out of scope for MVP.
- AI contextual analysis uses platform-managed models; custom model training is
  out of scope but feedback data is captured for future refinement cycles.
- Identification of individuals relies on timestamp correlation with external
  access control logs; biometric identification is explicitly excluded.
- LGPD-aligned data minimization and retention defaults apply per tenant; detailed
  retention policy configuration UI is deferred beyond MVP.
- SMS and WhatsApp delivery depend on third-party messaging providers; ARGUS
  tracks delivery status but does not guarantee provider uptime.
- Billing, invoicing, and usage metering are not required for MVP operation.
- English is the primary language for MVP interfaces; localization is out of
  scope.

## Constitution Alignment

This feature specification implements the following constitutional principles:

| Principle | MVP Coverage |
|-----------|--------------|
| I. Multi-Tenant Isolation | FR-001–004, US1, SC-002 |
| II. Authentication & Identity | FR-002–003, SSO-only access |
| III. Interface Decoupling | FR-010, FR-018–020, US4 |
| IV. Edge-to-Cloud Cost Control | FR-011, conceptual flow step 2 |
| V. Privacy & LGPD Compliance | FR-013, assumptions on biometrics |
| VI. Asynchronous Communications | FR-028–030, US6 |
| VII. Continuous Improvement | FR-023–025, US5 |
| VIII. Traceability | FR-026, FR-017, US5 AC3 |
