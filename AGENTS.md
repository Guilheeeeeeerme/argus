<!-- headroom:rtk-instructions -->
# RTK (Rust Token Killer) - Token-Optimized Commands

When running shell commands, **always prefix with `rtk`**. This reduces context
usage by 60-90% with zero behavior change. If rtk has no filter for a command,
it passes through unchanged — so it is always safe to use.

## Key Commands
```bash
# Git (59-80% savings)
rtk git status          rtk git diff            rtk git log

# Files & Search (60-75% savings)
rtk ls <path>           rtk read <file>         rtk grep <pattern>
rtk find <pattern>      rtk diff <file>

# Test (90-99% savings) — shows failures only
rtk pytest tests/       rtk cargo test          rtk test <cmd>

# Build & Lint (80-90% savings) — shows errors only
rtk tsc                 rtk lint                rtk cargo build
rtk prettier --check    rtk mypy                rtk ruff check

# Analysis (70-90% savings)
rtk err <cmd>           rtk log <file>          rtk json <file>
rtk summary <cmd>       rtk deps                rtk env

# GitHub (26-87% savings)
rtk gh pr view <n>      rtk gh run list         rtk gh issue list

# Infrastructure (85% savings)
rtk docker ps           rtk kubectl get         rtk docker logs <c>

# Package managers (70-90% savings)
rtk pip list            rtk pnpm install        rtk npm run <script>
```

## Rules
- In command chains, prefix each segment: `rtk git add . && rtk git commit -m "msg"`
- For debugging, use raw command without rtk prefix
- `rtk proxy <cmd>` runs command without filtering but tracks usage
<!-- /headroom:rtk-instructions -->

# AGENTS.md — Argus

Coding-agent rules for this repository. Project map: [CLAUDE.md](./CLAUDE.md), [README.md](./README.md).

## Scope

- Work inside this monorepo (`apps/`, `packages/`, `services/`, `docs/`, `scripts/`).
- Production Compose/Jenkins lives in **infra** — do not invent a parallel prod deploy path in this repo.
- Prefer targeted reads and the smallest sufficient change. Do not run broad refactors or full test matrices unless asked.

## Hard rules

- **UI**: import from `@argus/design-system` only; follow [STYLE_GUIDE.md](./STYLE_GUIDE.md). No inline hex colors or ad-hoc CSS variables in apps.
- **Auth / tenancy**: opaque Redis sessions; MFE hash-token handoff; derive company/tenant from session server-side — never trust client claims alone.
- **LLM**: follow Promptdesk-aligned guardrails (`docs/ai-engineering.md`, `apps/api/docs/guardrails.md`). No API keys in prompts; fail closed on bad model output; log ids/statuses, not raw frame/prompt payloads.
- **Env**: copy `.env.example` → `.env`. Do not commit `.env`. Keep Redis DB index conventions (`/0` local, `/1` prod).
- **Auth0**: MVP uses mock (`AUTH0_USE_MOCK`); do not switch to production Auth0 without an explicit task.
- Local `docker-compose.yml` / `scripts/up.sh` are for development only — prod is infra-owned.

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
