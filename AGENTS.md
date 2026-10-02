<!-- headroom:rtk-instructions -->
# RTK (Rust Token Killer)

Always prefix shell commands with `rtk` (60-90% savings, pass-through when no filter).

Key: `rtk git status|diff|log` · `rtk ls/read/grep/find` · `rtk pytest|test|tsc|lint|mypy|ruff check|cargo build` · `rtk err/log/json/summary/deps` · `rtk gh pr view|run list|issue list` · `rtk docker ps|logs` · `rtk pip/pnpm/npm`.
In chains prefix each segment: `rtk git add . && rtk git commit -m "msg"`. For debugging use raw command; `rtk proxy <cmd>` runs unfiltered.
<!-- /headroom:rtk-instructions -->

# AGENTS.md — Argus

Coding-agent rules for this repository. Project map: [CLAUDE.md](./CLAUDE.md), [README.md](./README.md).

## Scope

- Work inside this monorepo (`apps/`, `packages/`, `services/`, `docs/`, `scripts/`).
- Production Compose and GitHub Actions workflows live in **infra** — GHA + GHCR is the sole supported production control plane (do not use Jenkins; VPS Jenkins removal is CONFIRM-gated in infra after GHA is proven). Do not invent a parallel prod deploy path in this repo.
- Prefer targeted reads and the smallest sufficient change. Do not run broad refactors or full test matrices unless asked.

## Hard rules

- **UI**: import from `@argus/design-system` only; follow [STYLE_GUIDE.md](./STYLE_GUIDE.md). No inline hex colors or ad-hoc CSS variables in apps.
- **Auth / tenancy**: opaque Redis sessions; MFE hash-token handoff; derive company/tenant from session server-side — never trust client claims alone.
- **LLM**: follow Promptdesk-aligned guardrails (`docs/ai-engineering.md`, `apps/api/docs/guardrails.md`). No API keys in prompts; fail closed on bad model output; log ids/statuses, not raw frame/prompt payloads.
- **Env**: copy `.env.example` → `.env`. Do not commit `.env`. Keep Redis DB index conventions (`/0` local, `/1` prod).
- **Auth0**: MVP uses mock (`AUTH0_USE_MOCK`); do not switch to production Auth0 without an explicit task.
- Local `docker-compose.yml` / `scripts/up.sh` are for development only — prod is infra-owned.
- Production database remains on existing Supabase Postgres, schema `argus`; do not rewrite its URLs to VPS Postgres. Run reviewed Alembic migrations via infra before rollout.

## Verification

```bash
npm run lint
npm run build
# API (apps/api; needs services up for full suite)
PYTHONPATH=src pytest tests/
```

For a narrow API change, prefer the relevant pytest paths over the entire suite.

## Communication

User-facing text in English.
