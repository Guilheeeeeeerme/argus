<!-- headroom:rtk-instructions -->
# RTK (Rust Token Killer)

Always prefix shell commands with `rtk` (60-90% savings, pass-through when no filter).

Key: `rtk git status|diff|log` · `rtk ls/read/grep/find` · `rtk pytest|test|tsc|lint|mypy|ruff check|cargo build` · `rtk err/log/json/summary/deps` · `rtk gh pr view|run list|issue list` · `rtk docker ps|logs` · `rtk pip/pnpm/npm`.
In chains prefix each segment: `rtk git add . && rtk git commit -m "msg"`. For debugging use raw command; `rtk proxy <cmd>` runs unfiltered.
<!-- /headroom:rtk-instructions -->

# AGENTS.md — Argus

Coding-agent rules for this repository.

| Reference | Doc |
| --- | --- |
| Project map | [CLAUDE.md](./CLAUDE.md) · [README.md](./README.md) |
| AI engineering map | [docs/ai-engineering.md](./docs/ai-engineering.md) |
| Gemini+JEV routing | [docs/intelligence-routing.md](./docs/intelligence-routing.md) |
| Guardrails | [apps/api/docs/guardrails.md](./apps/api/docs/guardrails.md) |
| Style guide | [STYLE_GUIDE.md](./STYLE_GUIDE.md) |

## Scope

Work inside `apps/`, `packages/`, `services/`, `docs/`, `scripts/`. Production Compose and GHA workflows live in **infra** (sole prod control plane; do not invent parallel paths). Prefer targeted changes; no broad refactors or full test matrices unless asked.

## Hard rules

| Rule | Detail |
| --- | --- |
| **UI** | Import from `@argus/design-system` only ([STYLE_GUIDE.md](./STYLE_GUIDE.md)). No inline hex or ad-hoc CSS vars. |
| **Auth/tenancy** | Opaque Redis sessions; MFE hash-token handoff; derive account/tenant server-side. Never trust client claims alone. |
| **LLM** | Gemini VLM direct (`gemini-3.1-flash-lite`, public API); JEV post-VLM verify (`JEV_VERIFY_MODE`, `services/prompt-eval/.../jev_verify.py`, `jev_client.py`). No API keys in prompts; fail closed; log ids/statuses only. |
| **Env** | `.env.example` → `.env`. Never commit `.env`. Redis DB `/0` local, `/1` prod. |
| **Auth0** | MVP uses mock (`AUTH0_USE_MOCK`). Do not wire production Auth0 without an explicit task. |
| **Deploy** | `docker-compose.yml` / `scripts/up.sh` for dev only; prod is infra-owned. |
| **DB** | Production on Supabase Postgres, schema `argus`. Never rewrite URLs to VPS Postgres. Run Alembic migrations via infra before rollout. |

## Verification

```bash
npm run lint
npm run build
# API (apps/api; needs services up for full suite)
PYTHONPATH=src pytest tests/
```

For a narrow API change, prefer the relevant pytest paths over the entire suite.

User-facing text in English.
