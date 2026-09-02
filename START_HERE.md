# ARGUS — START HERE

This file is the durable handoff for the next development interaction. Read it
before changing code or documentation, then update it before ending the
interaction.

## Current flag

```text
NOTHING TO BE DONE: false
PROJECT_STATUS: foundation_on_main; mvp_implementation_not_on_main
ACTIVE_FEATURE: 001-saas-mvp
LAST_AUDIT: 2026-09-02
```

`NOTHING TO BE DONE: true` is allowed only when the completion gates below are
all verified on the current `main` commit and the evidence is recorded in the
feature validation log. Until then, this flag must remain `false`.

## What is currently true

- `main` contains the foundation work from PR #1: database migrations/models,
  Auth0/JWT security primitives, RLS setup, Docker infrastructure, seed and
  validation scripts, and the initial backend test.
- The feature specification and design artifacts are partly present under
  `specs/001-saas-mvp/`.
- Spec Kit CLI `1.0.3` is installed and the repository now has its core
  `.specify/` scripts, templates, workflows, and manifests.
- Codex-specific Spec Kit skills could not be written because `.agents/` is
  read-only in this workspace. The repository-local core installation remains
  usable; use the generated workflow files or install the Codex integration in
  a writable clone/workspace.
- Local refs `pr/02-ingest` through `pr/06-polish` contain later implementation
  work, but they are not merged into `main`. Treat them as review material, not
  as completed project state.

See [DOCUMENTATION_AUDIT.md](DOCUMENTATION_AUDIT.md) for the evidence-based
status and the comparison with those refs.

## Required next interaction

1. Start from a clean, verified `main` working tree and inspect the audit.
2. Review the unmerged PR refs in dependency order (`pr/02-ingest` through
   `pr/06-polish`) against the spec, plan, and constitution. Do not claim their
   tasks are complete on `main` until their changes are merged and re-tested.
3. Use the Spec Kit flow for the active feature:
   `speckit-clarify` (if needed) → `speckit-analyze` →
   `speckit-implement`/targeted fixes → `speckit-converge`.
4. Keep `specs/001-saas-mvp/tasks.md` and `validation-log.md` synchronized with
   actual repository state. Record failed, skipped, and environment-blocked
   checks explicitly.
5. Re-run the narrow tests after each slice, then the full quickstart and Docker
   smoke test when the environment is available.
6. Update this file's flag, `LAST_AUDIT`, status summary, and “Required next
   interaction” before handing off.

## Completion gates

- [ ] Spec Kit artifacts are complete and internally consistent.
- [ ] Foundation, ingestion, workers, admin/triage, WebSocket, and notification
      implementation is merged on `main`.
- [ ] Admin Dashboard and Triage SPA are either implemented as separate
      deployables or explicitly accepted as a documented MVP boundary.
- [ ] Automated tests pass on the supported runtime.
- [ ] Quickstart scenarios 1–8 pass, including a real Docker Compose smoke test.
- [ ] Security, tenant isolation, privacy, async notification, and immutable
      audit requirements are evidenced.
- [ ] `specs/001-saas-mvp/validation-log.md` records the final evidence and
      `speckit-converge` reports convergence.

When every box is checked, set `NOTHING TO BE DONE: true`, write the final
verification commit/date, and replace the next-step section with a short
maintenance instruction.
