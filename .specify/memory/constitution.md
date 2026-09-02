<!--
Sync Impact Report
- Version change: none → 1.0.0
- Modified principles: n/a (initial ratification)
- Added sections:
  - Core Principles I–VIII (Multi-Tenant Isolation through Traceability)
  - Platform Scope
  - Engineering Workflow
  - Governance
- Removed sections: none
- Follow-up TODOs:
  - Spec Kit resolver unavailable: `.specify/scripts/bash/resolve-template.sh` missing.
    Run `specify init` (or equivalent bundle install) to materialize the full `.specify/`
    scaffold for `/speckit-specify`, `/speckit-plan`, and `/speckit-analyze`.
-->

# ARGUS Constitution

ARGUS is a multi-tenant SaaS surveillance platform for continuous vigilance and
simultaneous attention across distributed sites. These principles are binding on
all architecture, specifications, implementations, deployments, and operational
changes. Keywords MUST, MUST NOT, SHOULD, and MAY are interpreted per RFC 2119.

## Core Principles

### I. Multi-Tenant Isolation

The system MUST enforce strict logical separation of all configurations, rules,
events, and user data by tenant ID at every architectural layer — including edge
agents, ingestion pipelines, storage, APIs, background workers, and user
interfaces. Cross-tenant reads, writes, queries, caches, logs, and administrative
actions MUST NOT occur except through explicitly audited, tenant-scoped
super-admin tooling that itself enforces tenant boundaries. Tenant context MUST
be established at the trust boundary and propagated immutably through every
downstream operation. Rationale: surveillance data is sensitive; a single tenant
leak is a catastrophic breach of trust and regulatory compliance.

### II. Authentication & Identity

The system MUST delegate authentication and Role-Based Access Control (RBAC)
entirely to an external Identity Provider (IdP) or SSO. The system MUST NOT
process, transmit, or store local user passwords, password hashes, or
password-recovery secrets. Authorization decisions MUST be derived from IdP-
issued identity claims and centrally defined roles/permissions mapped to tenant
scope. Session or token validation MUST fail closed: unauthenticated or
unauthorized requests MUST NOT access tenant resources. Rationale: credential
management is a specialized security domain; centralizing it reduces attack
surface and simplifies audit.

### III. Interface Decoupling

The architecture MUST maintain absolute separation between the Admin Dashboard
(used for system and rule configuration) and the Triage SPA (used exclusively
for real-time monitoring and event resolution). These interfaces MUST NOT share
a single deployable frontend bundle, routing namespace, or authentication
session surface that blurs operational roles. Configuration mutations MUST NOT
be executable from the Triage SPA; triage actions MUST NOT be executable from
the Admin Dashboard unless exposed through a distinct, auditable API contract.
Rationale: operators under time pressure must not accidentally change rules;
administrators must not be conflated with frontline triage staff.

### IV. Edge-to-Cloud Cost Control

The edge environment MUST filter and immediately discard irrelevant video frames
locally. The edge MUST ONLY transmit frame sequences that exhibit suspicious
behavioral triggers defined by tenant rules. Bandwidth, storage, and cloud
inference costs MUST be bounded by this local gating; bulk upload of
unfiltered streams MUST NOT be the default or fallback path. Edge discard and
trigger decisions SHOULD be logged with sufficient metadata for later audit
without retaining discarded frame content. Rationale: continuous video at scale
is economically and operationally unsustainable without edge-first filtering.

### V. Privacy & LGPD Compliance

The system MUST NOT extract, process, or store facial recognition outputs,
facial embeddings, or any biometric data. System-based identification MUST rely
solely on correlating the timestamp of an AI-detected anomaly with physical
access control logs. Features that infer identity from appearance, gait, voice,
or other biometric signals MUST NOT be introduced without a constitution
amendment and explicit legal review. Personal data handling MUST align with
LGPD requirements: purpose limitation, data minimization, retention limits,
and subject rights MUST be enforceable per tenant. Rationale: biometric
surveillance carries elevated legal and ethical risk; timestamp correlation
preserves investigative value without biometric processing.

### VI. Asynchronous Communications

External notifications (e.g., SMS, WhatsApp, email, push) MUST be processed
asynchronously via a decoupled delivery pipeline. Failures, retries, or
latencies in notification delivery MUST NOT block, delay, or degrade the core
evidence evaluation and triage pipeline. Notification state MUST be tracked
independently from event lifecycle state; triage completion MUST NOT depend on
notification success. Rationale: third-party messaging providers are
unreliable; core safety workflows must remain real-time and resilient.

### VII. Continuous Improvement

The system MUST capture structured human feedback during triage — including
disposition (true positive, false positive, false negative, inconclusive) and
textual reasoning for false positives and false negatives. This feedback MUST
be stored in a structured, tenant-scoped form suitable for model and rule
refinement. Collected feedback MUST be utilized to continuously refine and
adapt AI contextual analysis; feedback pipelines MUST NOT be optional
afterthoughts bolted onto triage. Feedback MUST NOT include biometric data
(see Principle V). Rationale: surveillance AI without human-in-the-loop
learning stagnates and erodes operator trust.

### VIII. Traceability

Every aggregated decision MUST maintain a verifiable, immutable audit trail
linking the final disposition back to its raw frame evidences, the user who
reviewed it, and the specific context mode applied at the time of capture.
Audit records MUST be append-only; retroactive alteration or silent deletion of
decision provenance MUST NOT be permitted. The trail MUST be sufficient for an
independent reviewer to reconstruct what was seen, who acted, under which rule
set, and when — without relying on ephemeral application state. Rationale:
surveillance outcomes may be disputed legally and operationally; provenance is
non-negotiable.

## Platform Scope

ARGUS delivers tenant-isolated, edge-filtered video anomaly detection with
cloud-side contextual analysis, human triage, and asynchronous alerting.
The platform comprises: edge agents, cloud ingestion and inference services,
the Admin Dashboard, the Triage SPA, notification workers, and audit storage.
All features, specifications, and implementations MUST align with this scope
and with Core Principles I–VIII. Work outside this scope — including biometric
identification, unified admin/triage interfaces, or synchronous notification
dependencies — requires an explicit constitution amendment.

## Engineering Workflow

Specifications, plans, and tasks MUST cite the principles they implement or risk
violating. Pull requests and design reviews MUST verify: tenant isolation at new
data paths, IdP-only auth (no local credentials), Admin/Triage separation,
edge filtering before cloud upload, absence of biometric processing, async
notification boundaries, structured triage feedback capture, and immutable
audit trails for aggregated decisions. `/speckit-analyze` and the Constitution
Check section of implementation plans MUST treat any conflict with a MUST or
MUST NOT in this document as CRITICAL. Violations are resolved by changing the
spec, plan, or implementation — not by diluting a principle.

## Governance

This constitution supersedes conflicting informal practice, README aspirations,
and ad-hoc architectural decisions. Amendments MUST document the change, bump
`CONSTITUTION_VERSION` per semantic versioning (MAJOR for incompatible
principle removals or redefinitions, MINOR for new or materially expanded
principles or sections, PATCH for clarifications and non-semantic refinements),
and update `LAST_AMENDED_DATE`. Compliance reviews of specs, plans, pull
requests, and releases MUST verify alignment with Core Principles I–VIII.
Complexity and scope expansion MUST be justified against Principles III, IV,
and V.

**Version**: 1.0.0 | **Ratified**: 2026-09-01 | **Last Amended**: 2026-09-01
